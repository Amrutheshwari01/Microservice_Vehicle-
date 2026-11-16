from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status

from app.models.vehicle import Vehicle, VehicleStatus, VehicleDocument
from app.models.listing import RentalListing, ListingStatus, AvailabilityWindow
from app.models.booking import Booking, BookingStatus
from app.schemas.listing import FleetSearchResult
from app.modules.m2_fleet.state_machine import VehicleStateMachine
from app.inter_service.outbox import record_event
from app.api.deps import log_audit_trail

class FleetService:

    @classmethod
    def transition_vehicle_status(
        cls,
        db: Session,
        vehicle_id: str,
        target_status: str,
        actor: dict,
        reason: Optional[str] = None,
        correlation_id: Optional[str] = None
    ) -> Vehicle:
        """
        RTO-FR-04: Vehicle lifecycle state transition
        """
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        # Security check: Only vehicle owner or admin can trigger manual state changes
        is_owner = (vehicle.owner_citizen_id == actor.get("citizen_id"))
        is_admin = ("ADMIN" in actor.get("personas", []) or "RTO_OFFICIAL" in actor.get("personas", []))
        if not (is_owner or is_admin):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to change vehicle state")

        # Admin only can suspend
        if target_status == VehicleStatus.SUSPENDED and not is_admin:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only Administrator can suspend a vehicle")

        # Validate state machine
        VehicleStateMachine.validate_transition(vehicle.status, target_status)

        old_status = vehicle.status
        vehicle.status = target_status
        vehicle.updated_at = datetime.utcnow()

        log_audit_trail(
            db=db,
            actor_id=actor.get("citizen_id", "SYSTEM"),
            actor_role="ADMIN" if is_admin else "OWNER",
            action="VEHICLE_STATUS_CHANGED",
            entity_type="VEHICLE",
            entity_id=vehicle.id,
            details={"old_status": old_status, "new_status": target_status, "reason": reason},
            correlation_id=correlation_id
        )

        record_event(
            db=db,
            event_type="VehicleStatusChanged",
            aggregate_type="VEHICLE",
            aggregate_id=vehicle.id,
            payload={"vehicle_id": vehicle.id, "old_status": old_status, "new_status": target_status},
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(vehicle)
        return vehicle

    @classmethod
    def search_fleet(
        cls,
        db: Session,
        vehicle_class: Optional[str] = None,
        min_capacity_kg: Optional[float] = None,
        max_rate_per_day: Optional[float] = None,
        location: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[FleetSearchResult]:
        """
        RTO-FR-05: Fleet search API returning only bookable vehicles (not blocked by expired compliance).
        """
        now = datetime.utcnow()
        query = (
            db.query(RentalListing, Vehicle)
            .join(Vehicle, RentalListing.vehicle_id == Vehicle.id)
            .filter(RentalListing.status == ListingStatus.ACTIVE)
            .filter(Vehicle.status.in_([VehicleStatus.AVAILABLE, VehicleStatus.VERIFIED]))
        )

        if vehicle_class:
            query = query.filter(Vehicle.vehicle_class == vehicle_class.upper())
        if min_capacity_kg:
            query = query.filter(Vehicle.capacity_kg >= min_capacity_kg)
        if max_rate_per_day:
            query = query.filter(RentalListing.rate_per_day <= max_rate_per_day)
        if location:
            query = query.filter(RentalListing.pickup_location.ilike(f"%{location}%"))

        results = query.all()
        fleet_results: List[FleetSearchResult] = []

        for listing, vehicle in results:
            # Check compliance documents: RTO-FR-13 (must not have expired insurance, fitness, permit, or puc)
            expired_docs = (
                db.query(VehicleDocument)
                .filter(VehicleDocument.vehicle_id == vehicle.id)
                .filter(VehicleDocument.expiry_date != None)
                .filter(VehicleDocument.expiry_date < now)
                .all()
            )
            if expired_docs:
                continue # Blocked due to expired compliance

            # Check overlap if dates provided
            if start_time and end_time:
                overlap = (
                    db.query(Booking)
                    .filter(Booking.vehicle_id == vehicle.id)
                    .filter(Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ACTIVE]))
                    .filter(and_(Booking.start_time < end_time, Booking.end_time > start_time))
                    .first()
                )
                if overlap:
                    continue # Not available for this specific window

            fleet_results.append(
                FleetSearchResult(
                    listing_id=listing.id,
                    vehicle_id=vehicle.id,
                    registration_number=vehicle.registration_number,
                    vehicle_class=vehicle.vehicle_class,
                    make_model=vehicle.make_model,
                    capacity_kg=vehicle.capacity_kg,
                    fuel_type=vehicle.fuel_type,
                    rate_per_hour=listing.rate_per_hour,
                    rate_per_day=listing.rate_per_day,
                    rate_per_km=listing.rate_per_km,
                    security_deposit=listing.security_deposit,
                    pickup_location=listing.pickup_location,
                    status=vehicle.status,
                    availability_status="AVAILABLE"
                )
            )

        return fleet_results

    @classmethod
    def get_vehicle_availability_calendar(
        cls,
        db: Session,
        vehicle_id: str
    ) -> Dict[str, Any]:
        """
        RTO-FR-05: Availability calendar showing existing bookings and available slots.
        """
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        listing = db.query(RentalListing).filter(RentalListing.vehicle_id == vehicle_id).first()
        
        # Get all confirmed or active bookings
        bookings = (
            db.query(Booking)
            .filter(Booking.vehicle_id == vehicle_id)
            .filter(Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ACTIVE]))
            .order_by(Booking.start_time.asc())
            .all()
        )

        busy_slots = [
            {
                "booking_id": b.id,
                "booking_ref": b.booking_ref,
                "start_time": b.start_time.isoformat(),
                "end_time": b.end_time.isoformat(),
                "status": b.status
            }
            for b in bookings
        ]

        return {
            "vehicle_id": vehicle.id,
            "registration_number": vehicle.registration_number,
            "vehicle_status": vehicle.status,
            "listing_status": listing.status if listing else "UNLISTED",
            "busy_slots": busy_slots,
            "can_book_now": (vehicle.status in [VehicleStatus.AVAILABLE, VehicleStatus.VERIFIED]) and (listing is not None and listing.status == ListingStatus.ACTIVE)
        }

