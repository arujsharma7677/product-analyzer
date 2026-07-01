from fastapi import APIRouter, Depends
from sqlalchemy import desc, select

from app.services import credit_service
from app.middleware.auth_middleware import get_current_user
from app.models.credits import AddCredits
from app.database import SessionLocal
from app.models.db import CreditTransaction, UserUsage

router = APIRouter()


@router.get("/credits")
async def my_credits(user=Depends(get_current_user)):
    user_number = await credit_service.get_user_number(user["id"])
    credits = await credit_service.get_credits(user_number)
    return {
        "user_number": user_number,
        "credits_balance": float(credits["credits_balance"] or 0),
        "credits_used": float(credits["credits_used"] or 0),
        "total_credits_purchased": float(credits["total_credits_purchased"] or 0),
        "last_recharged_at": credits["last_recharged_at"],
    }


@router.get("/credits/check")
async def check_balance(user=Depends(get_current_user)):
    """Lightweight guard the frontend can call before starting an analysis.
    Returns 402 if balance is zero."""
    user_number = await credit_service.get_user_number(user["id"])
    balance = await credit_service.require_positive_balance(user_number)
    return {"ok": True, "credits_balance": balance}


@router.post("/credits/recharge")
async def recharge_user(body: AddCredits, user=Depends(get_current_user)):
    """Admin recharge. Logs admin_recharge_log and updates the balance in code."""
    target = body.user_number
    credits = await credit_service.recharge(
        target,
        recharge_amount=body.recharge_amount,
        credits_granted=body.credits_granted,
        payment_reference=body.payment_reference,
        note=body.note,
    )
    return {
        "message": f"{body.credits_granted} credits granted to user {target}",
        "credits_balance": float(credits["credits_balance"] or 0),
    }


@router.get("/credits/history")
async def usage_history(user=Depends(get_current_user)):
    user_number = await credit_service.get_user_number(user["id"])
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(
                    UserUsage.type,
                    UserUsage.input_tokens,
                    UserUsage.output_tokens,
                    UserUsage.total_tokens,
                    UserUsage.credits_deducted,
                    UserUsage.catalog_name,
                    UserUsage.model_used,
                    UserUsage.status,
                    UserUsage.created_at,
                )
                .where(UserUsage.user_number == user_number)
                .order_by(desc(UserUsage.created_at))
                .limit(50)
            )
        ).mappings().all()
    return {"history": [dict(r) for r in rows]}


@router.get("/credits/transactions")
async def transactions(user=Depends(get_current_user)):
    user_number = await credit_service.get_user_number(user["id"])
    async with SessionLocal() as session:
        rows = (
            await session.execute(
                select(
                    CreditTransaction.transaction_type,
                    CreditTransaction.amount,
                    CreditTransaction.balance_before,
                    CreditTransaction.balance_after,
                    CreditTransaction.reference_type,
                    CreditTransaction.description,
                    CreditTransaction.created_at,
                )
                .where(CreditTransaction.user_number == user_number)
                .order_by(desc(CreditTransaction.created_at))
                .limit(100)
            )
        ).mappings().all()
    return {"transactions": [dict(r) for r in rows]}
