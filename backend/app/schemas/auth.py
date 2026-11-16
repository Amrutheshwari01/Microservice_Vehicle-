from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field

class UserSignUp(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=4)
    phone: Optional[str] = None
    role: str = Field(default="RENTER", description="RENTER, VEHICLE_OWNER, DELIVERY_PERSON, ADMIN")
    kyc_tier: str = Field(default="T2", description="T0, T1, T2, T3")
    driving_licence_classes: str = Field(default="LMV", description="Comma separated classes e.g. LMV,HMV,TRACTOR")

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    kyc_tier: str
    personas: List[str]
    driving_licence_classes: List[str]
    wallet_balance: float = 0.0

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: UserProfile

