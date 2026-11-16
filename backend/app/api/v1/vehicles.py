from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.vehicle import Vehicle, VehicleStatus
from app.schemas.vehicle import (
    VehicleCreate,
    VehicleResponse,
    VehicleDetailResponse,
    VerificationReviewRequest,
)
from app.modules.m1_registration.service import RegistrationService
from app.modules.m2_fleet.service import FleetService
from app.inter_service.mock_external_services import SharedOcrService
from app.api.deps import get_current_actor, require_vehicle_owner, require_admin

router = APIRouter(prefix="/vehicles", tags=["Vehicles & Registration (RTO-M1, M2)"])

@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def register_vehicle(
    vehicle_in: VehicleCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(require_vehicle_owner)
):
    """
    RTO-FR-01: Vehicle registration with RC document upload.
    RTO-FR-03: Ownership validation against KYC identity.
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    return RegistrationService.register_vehicle(
        db=db,
        vehicle_in=vehicle_in,
        owner_actor=actor,
        correlation_id=correlation_id
    )

@router.post("/ocr-extract")
def extract_rc_with_ocr(
    raw_text_or_filename: str = Body(..., embed=True, example="KA-04-MK-4421 Tata Ace Gold RC Copy")
):
    """
    Optional OCR service helper to prefill vehicle registration fields from RC (RTO-FR-01).
    """
    return SharedOcrService.extract_rc_data(raw_text_or_filename)

@router.get("", response_model=List[VehicleResponse])
def list_vehicles(
    owner_citizen_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_actor)
):
    """
    List vehicles. If owner persona, default filter to own vehicles unless admin.
    """
    query = db.query(Vehicle)
    if owner_citizen_id:
        query = query.filter(Vehicle.owner_citizen_id == owner_citizen_id)
    elif "ADMIN" not in actor.get("personas", []) and "RTO_OFFICIAL" not in actor.get("personas", []) and actor.get("citizen_id") != "GUEST_VISITOR":
        # Default to caller's vehicles
        query = query.filter(Vehicle.owner_citizen_id == actor["citizen_id"])

    if status_filter:
        query = query.filter(Vehicle.status == status_filter.upper())

    return query.order_by(Vehicle.created_at.desc()).all()

@router.get("/search")
def search_fleet(
    vehicle_class: Optional[str] = Query(None, description="e.g. LIGHT_COMMERCIAL, TRACTOR, MINI_TRUCK"),
    min_capacity_kg: Optional[float] = Query(None, description="Minimum payload capacity in kg"),
    max_rate_per_day: Optional[float] = Query(None, description="Maximum daily rental rate"),
    location: Optional[str] = Query(None, description="Pickup location substring"),
    db: Session = Depends(get_db)
):
    """
    RTO-FR-05: Fleet search with filters (Public / Renter / Guest read-only).
    Returns only bookable vehicles (not blocked by expired compliance).
    """
    return FleetService.search_fleet(
        db=db,
        vehicle_class=vehicle_class,
        min_capacity_kg=min_capacity_kg,
        max_rate_per_day=max_rate_per_day,
        location=location
    )

@router.get("/{vehicle_id}", response_model=VehicleDetailResponse)
def get_vehicle(
    vehicle_id: str,
    db: Session = Depends(get_db)
):
    """
    RTO-FR-02, RTO-FR-04: Retrieve vehicle details, status, and verification result.
    """
    vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
    if not vehicle:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")
    return vehicle

@router.get("/{vehicle_id}/availability")
def get_availability_calendar(
    vehicle_id: str,
    db: Session = Depends(get_db)
):
    """
    RTO-FR-05: Availability calendar showing existing bookings and available slots.
    """
    return FleetService.get_vehicle_availability_calendar(db=db, vehicle_id=vehicle_id)

@router.patch("/{vehicle_id}/status", response_model=VehicleResponse)
def transition_vehicle_lifecycle(
    vehicle_id: str,
    target_status: str = Body(..., embed=True, example="UNDER_MAINTENANCE"),
    reason: Optional[str] = Body(None, embed=True),
    request: Request = None,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_actor)
):
    """
    RTO-FR-04: Vehicle lifecycle state transition (enforces state machine).
    """
    correlation_id = getattr(request.state, "correlation_id", None) if request else None
    return FleetService.transition_vehicle_status(
        db=db,
        vehicle_id=vehicle_id,
        target_status=target_status.upper(),
        actor=actor,
        reason=reason,
        correlation_id=correlation_id
    )

@router.post("/{vehicle_id}/verification-review", response_model=VehicleResponse)
def review_verification(
    vehicle_id: str,
    review_in: VerificationReviewRequest,
    request: Request,
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """
    RTO-FR-02: Administrator verification review fallback.
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    return RegistrationService.review_verification(
        db=db,
        vehicle_id=vehicle_id,
        review_in=review_in,
        admin_actor=admin,
        correlation_id=correlation_id
    )

