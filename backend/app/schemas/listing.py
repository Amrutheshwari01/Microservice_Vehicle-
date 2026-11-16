from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from app.schemas.vehicle import VehicleResponse

class RentalListingCreate(BaseModel):
    vehicle_id: str
    rate_per_hour: float = Field(..., gt=0, examples=[150.0])
    rate_per_day: float = Field(..., gt=0, examples=[1200.0])
    rate_per_km: float = Field(..., gt=0, examples=[12.0])
    security_deposit: float = Field(..., ge=0, examples=[2000.0])
    pickup_location: str = Field(..., examples=["Hebbal APMC Yard, Bengaluru"])
    pickup_coordinates: Optional[str] = Field(None, examples=["13.0358,77.5970"])
    rental_rules: Optional[str] = Field(None, examples=["Return with same fuel level. Carry valid commercial driving licence."])

class RentalListingUpdate(BaseModel):
    rate_per_hour: Optional[float] = None
    rate_per_day: Optional[float] = None
    rate_per_km: Optional[float] = None
    security_deposit: Optional[float] = None
    pickup_location: Optional[str] = None
    pickup_coordinates: Optional[str] = None
    rental_rules: Optional[str] = None
    status: Optional[str] = Field(None, description="ACTIVE, PAUSED, WITHDRAWN")

class AvailabilityWindowCreate(BaseModel):
    start_time: datetime
    end_time: datetime
    is_available: bool = True
    notes: Optional[str] = None

class AvailabilityWindowResponse(BaseModel):
    id: str
    listing_id: str
    start_time: datetime
    end_time: datetime
    is_available: bool
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class RentalListingResponse(BaseModel):
    id: str
    vehicle_id: str
    owner_citizen_id: str
    rate_per_hour: float
    rate_per_day: float
    rate_per_km: float
    security_deposit: float
    pickup_location: str
    pickup_coordinates: Optional[str]
    rental_rules: Optional[str]
    status: str
    created_at: datetime
    updated_at: datetime
    vehicle: Optional[VehicleResponse] = None
    availability_windows: List[AvailabilityWindowResponse] = []

    class Config:
        from_attributes = True

class FleetSearchResult(BaseModel):
    listing_id: str
    vehicle_id: str
    registration_number: str
    vehicle_class: str
    make_model: str
    capacity_kg: float
    fuel_type: str
    rate_per_hour: float
    rate_per_day: float
    rate_per_km: float
    security_deposit: float
    pickup_location: str
    status: str
    availability_status: str = "AVAILABLE"
