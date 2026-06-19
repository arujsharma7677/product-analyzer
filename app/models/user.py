from pydantic import BaseModel, EmailStr
from typing import Optional

class UserSignup(BaseModel):
    email: EmailStr
    password: str
    first_name: str
    last_name: str
    seller_name: str
    country: str
    address: str
    pincode: str
    state: str
    gst: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: str
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    seller_name: Optional[str]
    country: Optional[str]
    address: Optional[str]
    pincode: Optional[str]
    state: Optional[str]
    gst: Optional[str]
    credits_remaining: int = 0
    credits_used: int = 0
