from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field

class BookingCreateRequest(BaseModel):
    vehicle_id: str
    start_time: datetime = Field(..., example="2026-11-20T09:00:00")
    end_time: datetime = Field(..., example="2026-11-20T17:00:00")
    idempotency_key: str = Field(..., example="idemp-bk-uuid-001")

class HandoverCreateRequest(BaseModel):
    odometer_reading: float = Field(..., ge=0, example=45230.5)
    fuel_level_percent: float = Field(..., ge=0, le=100, example=95.0)
    condition_notes: Optional[str] = Field(None, example="Clean condition, minor scratch on left fender noted")
    photos: Optional[List[str]] = Field(default=[], description="List of encrypted photo store references")

class ReturnCreateRequest(BaseModel):
    odometer_reading: float = Field(..., ge=0, example=45380.0)
    fuel_level_percent: float = Field(..., ge=0, le=100, example=90.0)
    condition_notes: Optional[str] = Field(None, example="Returned in good shape")
    damage_detected: bool = Field(default=False)
    damage_amount: float = Field(default=0.0, ge=0)
    photos: Optional[List[str]] = Field(default=[])

class CancellationRequest(BaseModel):
    reason: str = Field(..., example="Agri harvest dispatch rescheduled by cooperative")

class AgriLinkVehicleRequest(BaseModel):
    agrilink_job_ref: str = Field(..., example="AGL-DEL-2026-9042")
    delivery_person_citizen_id: str = Field(..., example="CIT-DEL-5544")
    delivery_person_name: str = Field(..., example="Suresh Gowda")
    delivery_person_kyc_tier: str = Field(default="T2")
    delivery_person_licence_classes: str = Field(default="LMV,HMV")
    vehicle_class: Optional[str] = Field(None, example="LIGHT_COMMERCIAL")
    min_capacity_kg: Optional[float] = Field(None, example=600.0)
    start_time: datetime = Field(..., example="2026-11-21T06:00:00")
    end_time: datetime = Field(..., example="2026-11-21T18:00:00")
    destination: Optional[str] = Field(None, example="Kolar Vegetable Market")
    idempotency_key: str = Field(..., example="idemp-agl-job-9042")

class HandoverRecordResponse(BaseModel):
    id: str
    booking_id: str
    handover_type: str
    recorded_by_citizen_id: str
    odometer_reading: float
    fuel_level_percent: float
    condition_notes: Optional[str]
    damage_detected: bool
    damage_amount: float
    photos: Optional[str]
    timestamp: datetime

    class Config:
        from_attributes = True

class BookingResponse(BaseModel):
    id: str
    booking_ref: str
    vehicle_id: str
    renter_citizen_id: str
    renter_name: str
    renter_kyc_tier: str
    renter_licence_classes: str
    start_time: datetime
    end_time: datetime
    status: str
    agrilink_job_ref: Optional[str]
    estimated_duration_hours: float
    base_rent_amount: float
    deposit_amount: float
    total_hold_amount: float
    wallet_hold_id: Optional[str]
    wallet_hold_status: str
    idempotency_key: str
    cancellation_reason: Optional[str]
    cancellation_fee: float
    refund_amount: float
    cancelled_by: Optional[str]
    cancelled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    handover_records: List[HandoverRecordResponse] = []

    class Config:
        from_attributes = True

class PriceEstimateResponse(BaseModel):
    duration_hours: float
    duration_days: float
    base_rent_amount: float
    deposit_amount: float
    total_hold_amount: float
    breakdown_notes: str

