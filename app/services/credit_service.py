"""
Credit service — talks to the new prepaid credit schema.

All credit state is keyed on users.number (integer business key), NOT the
auth uuid. The DB triggers do the actual balance math:
  - INSERT into user_usage        -> trigger deducts from user_credits
  - INSERT into admin_recharge_log -> trigger tops up user_credits
This module only reads balances, resolves user_number, and inserts the
usage row. It NEVER updates user_credits directly.
"""
from fastapi import HTTPException
from app.database import db

# Minimum credits charged per analysis. The actual charge mirrors the
# generated column user_usage.credits_deducted = max(MIN_CREDITS, input + output).
MIN_CREDITS = 6500


async def get_user_number(auth_id: str) -> int:
    """Resolve the auth uuid (JWT sub) to the canonical users.number."""
    row = await db.fetch_one(
        "SELECT number FROM users WHERE auth_id = :aid",
        {"aid": auth_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="User not found")
    return row["number"]


async def get_credits(user_number: int) -> dict:
    """Return the live credit row for a user (auto-creates an empty one)."""
    row = await db.fetch_one(
        """SELECT credits_balance, credits_used, total_credits_purchased,
                  last_recharged_at
           FROM user_credits WHERE user_number = :n""",
        {"n": user_number},
    )
    if not row:
        await db.execute(
            "INSERT INTO user_credits (user_number) VALUES (:n) "
            "ON CONFLICT (user_number) DO NOTHING",
            {"n": user_number},
        )
        return {
            "credits_balance": 0,
            "credits_used": 0,
            "total_credits_purchased": 0,
            "last_recharged_at": None,
        }
    return dict(row)


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


async def log_usage(
    user_number: int,
    input_tokens: int,
    output_tokens: int,
    *,
    usage_type: str = "catalog_analyse",
    catalog_id: str | None = None,
    catalog_name: str | None = None,
    model_used: str = "claude-sonnet-4-6",
    status: str = "success",
) -> float:
    """
    Insert a user_usage row. The DB trigger deducts the credits and writes
    the credit_transactions audit row. credits_deducted is computed in the DB
    (generated column), so we don't pass it. Returns credits deducted.

    If the trigger raises 'Insufficient credits', surface it as HTTP 402.
    """
    try:
        await db.execute(
            """INSERT INTO user_usage
                 (user_number, type, input_tokens, output_tokens,
                  catalog_id, catalog_name, model_used, status)
               VALUES
                 (:n, :type, :inp, :out, :cid, :cname, :model, :status)""",
            {
                "n": user_number,
                "type": usage_type,
                "inp": input_tokens,
                "out": output_tokens,
                "cid": catalog_id,
                "cname": catalog_name,
                "model": model_used,
                "status": status,
            },
        )
    except Exception as e:
        msg = str(e)
        if "Insufficient credits" in msg or "check_violation" in msg:
            raise HTTPException(
                status_code=402,
                detail="Insufficient credits to complete this analysis. Please recharge.",
            )
        raise
    return max(MIN_CREDITS, input_tokens + output_tokens)


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
    Admin top-up. Inserts into admin_recharge_log; the DB trigger grows the
    balance and writes the audit row. Returns the refreshed credit row.
    """
    await db.execute(
        """INSERT INTO admin_recharge_log
             (user_number, recharge_amount, credits_granted,
              payment_reference, note, recharged_by)
           VALUES (:n, :amt, :granted, :ref, :note, :by)""",
        {
            "n": user_number,
            "amt": recharge_amount,
            "granted": credits_granted,
            "ref": payment_reference,
            "note": note,
            "by": recharged_by,
        },
    )
    return await get_credits(user_number)
