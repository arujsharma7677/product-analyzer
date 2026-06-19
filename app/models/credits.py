from pydantic import BaseModel
from typing import Optional

class CreditsOut(BaseModel):
    user_number: int
    credits_balance: float
    credits_used: float
    total_credits_purchased: float

class AddCredits(BaseModel):
    """Admin recharge payload. Keyed on users.number."""
    user_number: int
    recharge_amount: float
    credits_granted: float
    payment_reference: Optional[str] = None
    note: Optional[str] = None

class UsageLogOut(BaseModel):
    type: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    credits_deducted: float
    status: str
    created_at: str
