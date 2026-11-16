from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class VehicleBase(BaseModel):
    registration_number: str = Field(..., examples=["KA-01-AB-1234"])
    vehicle_class: str = Field(..., examples=["LIGHT_COMMERCIAL"])
    make_model: str = Field(..., examples=["Tata Ace Gold"])
    capacity_kg: float = Field(..., examples=[750.0])
    seating_capacity: int = Field(default=2, examples=[2])
    fuel_type: str = Field(default="DIESEL", examples=["DIESEL"])

class VehicleCreate(VehicleBase):
    rc_document_number: str = Field(..., examples=["RC-99887766"])
    rc_file_data: Optional[str] = Field(None, description="Base64 or mock file reference of RC")
    rc_expiry_date: Optional[datetime] = None

class DocumentCreate(BaseModel):
    document_type: str = Field(..., examples=["INSURANCE"])
    document_number: str = Field(..., examples=["POL-2026-987654"])
    file_reference: str = Field(..., examples=["enc://docs/insurance_ka01ab1234.pdf"])
    issue_date: Optional[datetime] = None
    expiry_date: datetime = Field(..., examples=["2027-12-31T23:59:59"])

class DocumentResponse(BaseModel):
    id: str
    vehicle_id: str
    document_type: str
    document_number: str
    file_reference: str
    issue_date: Optional[datetime]
    expiry_date: Optional[datetime]
    is_valid: bool
    created_at: datetime

    class Config:
        from_attributes = True

class VerificationReviewRequest(BaseModel):
    decision: str = Field(..., examples=["VERIFIED"], description="VERIFIED or REJECTED")
    reason: Optional[str] = Field(None, examples=["RC physically verified against state portal records"])
    admin_notes: Optional[str] = None

class VehicleResponse(VehicleBase):
    id: str
    owner_citizen_id: str
    owner_name: str
    status: str
    verification_status: str
    verification_reason: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class VehicleDetailResponse(VehicleResponse):
    documents: List[DocumentResponse] = []
