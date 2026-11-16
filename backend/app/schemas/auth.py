from typing import Optional, List
import re
from pydantic import BaseModel, Field, field_validator

class UserSignUp(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    email: str = Field(..., description="User email or username")
    password: str = Field(..., min_length=4)
    phone: Optional[str] = None
    role: str = Field(default="RENTER", description="RENTER, VEHICLE_OWNER, DELIVERY_PERSON, ADMIN")
    kyc_tier: str = Field(default="T2", description="T0, T1, T2, T3")
    driving_licence_classes: str = Field(default="LMV", description="Comma separated classes e.g. LMV,HMV,TRACTOR")
    face_image: Optional[str] = Field(None, description="Base64 encoded face photo or data URL")

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean:
            # If user enters simple username (e.g. 'guest', 'himanshu'), auto-qualify it
            clean = f"{clean}@agrilink.in"
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean):
            raise ValueError("Invalid email format. Enter e.g. name@example.com")
        return clean

class UserLogin(BaseModel):
    email: str = Field(..., description="User email or username")
    password: str

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        clean = v.strip().lower()
        if "@" not in clean:
            clean = f"{clean}@agrilink.in"
        return clean

class FaceLoginRequest(BaseModel):
    email: Optional[str] = Field(None, description="Optional email for 1:1 face verification")
    face_image: str = Field(..., description="Base64 encoded live camera capture of face")

    @field_validator("email")
    @classmethod
    def normalize_optional_email(cls, v: Optional[str]) -> Optional[str]:
        if not v:
            return None
        clean = v.strip().lower()
        if "@" not in clean:
            clean = f"{clean}@agrilink.in"
        return clean

class FaceEnrollRequest(BaseModel):
    face_image: str = Field(..., description="Base64 encoded live camera capture of face")

class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    kyc_tier: str
    personas: List[str]
    driving_licence_classes: List[str]
    has_face_enrolled: bool = False
    face_thumbnail: Optional[str] = None
    wallet_balance: float = 0.0

class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "Bearer"
    user: UserProfile
