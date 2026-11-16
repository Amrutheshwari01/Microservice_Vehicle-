from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query, Body
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.booking import Booking
from app.models.listing import RentalListing
from app.schemas.booking import (
    BookingCreateRequest,
    BookingResponse,
    HandoverCreateRequest,
    ReturnCreateRequest,
    CancellationRequest,
    PriceEstimateResponse,
)
from app.modules.m4_booking.service import BookingService
from app.modules.m4_booking.pricing import PricingEngine
from app.api.deps import require_renter, get_current_actor

router = APIRouter(prefix="/bookings", tags=["Bookings & Payments (RTO-M4)"])

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def create_booking(
    booking_in: BookingCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    renter: dict = Depends(require_renter)
):
    """
    RTO-FR-08: Booking request with eligibility and overlap prevention.
    RTO-FR-09: Pricing and wallet fund hold before confirmation.
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    return BookingService.create_booking(
        db=db,
        booking_in=booking_in,
        renter_actor=renter,
        correlation_id=correlation_id
    )

@router.post("/estimate-price", response_model=PriceEstimateResponse)
def estimate_price(
    vehicle_id: str = Body(..., embed=True),
    start_time: datetime = Body(..., embed=True),
    end_time: datetime = Body(..., embed=True),
    db: Session = Depends(get_db)
):
    """
    RTO-FR-09: Pre-confirmation price breakdown (rent, deposit, charges).
    """
    listing = db.query(RentalListing).filter(RentalListing.vehicle_id == vehicle_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental listing for this vehicle not found")

    dur_hours, base_rent, deposit, total_hold = PricingEngine.calculate_price(listing, start_time, end_time)
    
    return PriceEstimateResponse(
        duration_hours=dur_hours,
        duration_days=round(dur_hours / 24.0, 2),
        base_rent_amount=base_rent,
        deposit_amount=deposit,
        total_hold_amount=total_hold,
        breakdown_notes=f"Base Rent: ₹{base_rent} ({dur_hours}h) + Security Deposit: ₹{deposit} (Fully refundable on safe return)"
    )

@router.get("", response_model=List[BookingResponse])
def list_bookings(
    renter_citizen_id: Optional[str] = None,
    vehicle_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_actor)
):
    query = db.query(Booking)
    if renter_citizen_id:
        query = query.filter(Booking.renter_citizen_id == renter_citizen_id)
    elif "ADMIN" not in actor.get("personas", []) and actor.get("citizen_id") != "GUEST_VISITOR":
        # Default to caller bookings
        query = query.filter(Booking.renter_citizen_id == actor["citizen_id"])

    if vehicle_id:
        query = query.filter(Booking.vehicle_id == vehicle_id)
    if status_filter:
        query = query.filter(Booking.status == status_filter.upper())

    return query.order_by(Booking.created_at.desc()).all()

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: str,
    db: Session = Depends(get_db)
):
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")
    return booking

@router.post("/{booking_id}/handover", response_model=BookingResponse)
def record_handover(
    booking_id: str,
    handover_in: HandoverCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_actor)
):
    """
    RTO-FR-10: Handover record. Transitions vehicle to RENTED.
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    return BookingService.record_handover(
        db=db,
        booking_id=booking_id,
        handover_in=handover_in,
        actor=actor,
        correlation_id=correlation_id
    )

@router.post("/{booking_id}/return", response_model=BookingResponse)
def record_return(
    booking_id: str,
    return_in: ReturnCreateRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_actor)
):
    """
    RTO-FR-10: Return record and wallet settlement.
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    return BookingService.record_return(
        db=db,
        booking_id=booking_id,
        return_in=return_in,
        actor=actor,
        correlation_id=correlation_id
    )

@router.post("/{booking_id}/cancel", response_model=BookingResponse)
def cancel_booking(
    booking_id: str,
    cancel_in: CancellationRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_actor)
):
    """
    RTO-FR-11: Cancellation policy and refund calculation.
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    return BookingService.cancel_booking(
        db=db,
        booking_id=booking_id,
        cancel_in=cancel_in,
        actor=actor,
        correlation_id=correlation_id
    )

