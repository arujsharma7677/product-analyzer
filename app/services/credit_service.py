"""
Credit service — SQLAlchemy ORM over the prepaid credit schema.

All credit state is keyed on users.number (integer business key), NOT the
auth uuid. All balance math now lives HERE, in application code (the DB
triggers that used to do it were removed in 002_deduction_in_code.sql):
  - Analysis usage  -> log_usage_batch() locks the credit row, checks the
    balance, deducts a flat 6500 per platform, and writes the audit rows.
  - Admin top-ups    -> recharge() locks the credit row, grows the balance,
    and writes the audit row.
Each runs in one transaction with the credit row locked (SELECT ... FOR UPDATE)
so it stays atomic and race-safe.
"""
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app.database import SessionLocal
from app.models.db import (
    AdminRechargeLog,
    CreditTransaction,
    User,
    UserCredits,
    UserUsage,
)

# Flat credits charged per platform analysed. One user_usage row == one
# platform == one CREDITS_PER_PLATFORM charge, deducted in code below.
CREDITS_PER_PLATFORM = 6500


async def get_user_number(auth_id: str) -> int:
    """Resolve the auth uuid (JWT sub) to the canonical users.number."""
    async with SessionLocal() as session:
        number = await session.scalar(select(User.number).where(User.auth_id == auth_id))
    if number is None:
        raise HTTPException(status_code=404, detail="User not found")
    return number


async def get_credits(user_number: int) -> dict:
    """Return the live credit row for a user (auto-creates an empty one)."""
    async with SessionLocal() as session:
        row = await session.scalar(
            select(UserCredits).where(UserCredits.user_number == user_number)
        )
        if row is None:
            # Auto-provision an empty credits row (race-safe).
            session.add(UserCredits(user_number=user_number))
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
            return {
                "credits_balance": 0,
                "credits_used": 0,
                "total_credits_purchased": 0,
                "last_recharged_at": None,
            }
        return {
            "credits_balance": row.credits_balance,
            "credits_used": row.credits_used,
            "total_credits_purchased": row.total_credits_purchased,
            "last_recharged_at": row.last_recharged_at,
        }


async def require_positive_balance(user_number: int, minimum: float = 0) -> float:
    """
    Hard-stop guard used by every billable API.
    Raises 402 if the user's balance is below `minimum` (default: any balance
    at or below zero). Returns the current balance when OK.
    """
    credits = await get_credits(user_number)
    balance = float(credits["credits_balance"] or 0)
    if balance <= 0 or balance < minimum:
        detail = (
            f"Insufficient credits. A minimum of {int(minimum):,} credits is "
            f"required to run this analysis; your balance is {int(balance):,}. "
            "Please recharge to continue."
            if minimum > 0
            else "Insufficient credits. Your balance is 0. Please recharge to continue."
        )
        raise HTTPException(status_code=402, detail=detail)
    return balance


async def log_usage_batch(
    user_number: int,
    platforms: list[str],
    input_tokens: int,
    output_tokens: int,
    *,
    usage_type: str = "catalog_analyse",
    catalog_id: str | None = None,
    catalog_name: str | None = None,
    model_used: str = "claude-sonnet-4-6",
    status: str = "success",
) -> tuple[float, list[dict]]:
    """
    Charge a flat CREDITS_PER_PLATFORM per selected platform, entirely in code.

    All of it runs in ONE transaction with the user's credit row locked
    (SELECT ... FOR UPDATE), so it is atomic and race-safe: two concurrent
    requests can't both pass the balance check and overdraw. The whole batch is
    all-or-nothing — if the balance can't cover every platform, nothing is
    charged. For each platform we insert a user_usage row (with credits_deducted
    set explicitly) and a matching credit_transactions audit row, then write the
    new balance back to user_credits.

    The Claude call happens once for the whole request, so its real token counts
    are recorded on the first row only; the remaining rows carry 0 tokens (the
    charge is flat and independent of tokens) to avoid double-counting usage.

    Returns (total_credits_deducted, [{"platform", "credits_deducted"}, ...]).
    Raises HTTP 402 if the balance can't cover every platform.
    """
    total_charge = CREDITS_PER_PLATFORM * len(platforms)
    breakdown: list[dict] = []

    async with SessionLocal() as session:
        async with session.begin():
            # Lock the credit row for the duration of the transaction.
            credits = await session.scalar(
                select(UserCredits)
                .where(UserCredits.user_number == user_number)
                .with_for_update()
            )
            balance = float(credits.credits_balance) if credits is not None else 0.0
            if credits is None or balance < total_charge:
                raise HTTPException(
                    status_code=402,
                    detail="Insufficient credits to complete this analysis. Please recharge.",
                )

            for i, platform in enumerate(platforms):
                before = balance
                after = before - CREDITS_PER_PLATFORM
                label = f"{catalog_name} [{platform}]" if catalog_name else platform

                usage = UserUsage(
                    user_number=user_number,
                    type=usage_type,
                    input_tokens=input_tokens if i == 0 else 0,
                    output_tokens=output_tokens if i == 0 else 0,
                    credits_deducted=CREDITS_PER_PLATFORM,
                    catalog_id=catalog_id,
                    catalog_name=label,
                    model_used=model_used,
                    status=status,
                )
                session.add(usage)
                await session.flush()  # populate usage.id for the audit row

                session.add(
                    CreditTransaction(
                        user_number=user_number,
                        transaction_type="deduction",
                        amount=-CREDITS_PER_PLATFORM,
                        balance_before=before,
                        balance_after=after,
                        reference_id=usage.id,
                        reference_type="catalog_analyse",
                        description=label,
                    )
                )
                balance = after
                breakdown.append(
                    {"platform": platform, "credits_deducted": float(CREDITS_PER_PLATFORM)}
                )

            credits.credits_balance = balance
            credits.credits_used = float(credits.credits_used) + total_charge
            credits.updated_at = func.now()

    return float(total_charge), breakdown


async def recharge(
    user_number: int,
    recharge_amount: float,
    credits_granted: float,
    *,
    payment_reference: str | None = None,
    note: str | None = None,
    recharged_by: str = "admin",
) -> dict:
    """
    Admin top-up, done entirely in code (mirror of log_usage_batch, but adding).

    In ONE transaction with the credit row locked (SELECT ... FOR UPDATE):
    auto-provision the credits row if missing, log the admin_recharge_log row,
    grow credits_balance / total_credits_purchased by credits_granted, and write
    the credit_transactions audit row. Returns the refreshed credit row.
    """
    async with SessionLocal() as session:
        async with session.begin():
            # Lock the credit row (auto-provision an empty one if absent).
            credits = await session.scalar(
                select(UserCredits)
                .where(UserCredits.user_number == user_number)
                .with_for_update()
            )
            if credits is None:
                credits = UserCredits(
                    user_number=user_number,
                    credits_balance=0,
                    credits_used=0,
                    total_credits_purchased=0,
                )
                session.add(credits)
                await session.flush()

            before = float(credits.credits_balance or 0)
            after = before + credits_granted

            log = AdminRechargeLog(
                user_number=user_number,
                recharge_amount=recharge_amount,
                credits_granted=credits_granted,
                payment_reference=payment_reference,
                note=note,
                recharged_by=recharged_by,
            )
            session.add(log)
            await session.flush()  # populate log.id for the audit row

            credits.credits_balance = after
            credits.total_credits_purchased = (
                float(credits.total_credits_purchased or 0) + credits_granted
            )
            credits.last_recharged_at = func.now()
            credits.updated_at = func.now()

            session.add(
                CreditTransaction(
                    user_number=user_number,
                    transaction_type="recharge",
                    amount=credits_granted,
                    balance_before=before,
                    balance_after=after,
                    reference_id=log.id,
                    reference_type="admin_recharge",
                    description=note or "Admin recharge",
                )
            )
    return await get_credits(user_number)
