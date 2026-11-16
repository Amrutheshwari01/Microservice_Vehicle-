import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_
from fastapi import HTTPException, status

from app.models.vehicle import Vehicle, VehicleStatus, VehicleDocument
from app.models.listing import RentalListing, ListingStatus
from app.models.booking import Booking, BookingStatus, WalletHoldStatus
from app.schemas.booking import AgriLinkVehicleRequest
from app.modules.m4_booking.pricing import PricingEngine
from app.modules.m4_booking.saga import BookingSagaCoordinator
from app.inter_service.outbox import record_event
from app.api.deps import log_audit_trail

class AgriLinkAssignmentService:
    """
    RTO-FR-12: AgriLink delivery vehicle assignment (Microservice integration with AGL-M5).
    """

    @classmethod
    def assign_vehicle_for_job(
        cls,
        db: Session,
        req: AgriLinkVehicleRequest,
        correlation_id: Optional[str] = None
    ) -> Booking:
        # Check if already processed (Idempotency)
        existing = db.query(Booking).filter(Booking.idempotency_key == req.idempotency_key).first()
        if existing:
            return existing

        now = datetime.utcnow()
        # Find candidate vehicles: Verified/Available, matching capacity/class, compliant docs
        query = (
            db.query(Vehicle, RentalListing)
            .join(RentalListing, Vehicle.id == RentalListing.vehicle_id)
            .filter(Vehicle.status.in_([VehicleStatus.AVAILABLE, VehicleStatus.VERIFIED]))
            .filter(RentalListing.status == ListingStatus.ACTIVE)
        )

        if req.vehicle_class:
            query = query.filter(Vehicle.vehicle_class == req.vehicle_class.upper())
        if req.min_capacity_kg:
            query = query.filter(Vehicle.capacity_kg >= req.min_capacity_kg)

        candidates = query.all()
        selected_vehicle = None
        selected_listing = None

        for v, l in candidates:
            # Check compliance documents
            expired = (
                db.query(VehicleDocument)
                .filter(VehicleDocument.vehicle_id == v.id)
                .filter(VehicleDocument.expiry_date != None)
                .filter(VehicleDocument.expiry_date < now)
                .first()
            )
            if expired:
                continue

            # Check overlap
            overlap = (
                db.query(Booking)
                .filter(Booking.vehicle_id == v.id)
                .filter(Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ACTIVE]))
                .filter(and_(Booking.start_time < req.end_time, Booking.end_time > req.start_time))
                .first()
            )
            if not overlap:
                selected_vehicle = v
                selected_listing = l
                break

        if not selected_vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No suitable vehicle available for AgriLink job {req.agrilink_job_ref} with requirements (Class: {req.vehicle_class}, Min Capacity: {req.min_capacity_kg}kg)."
            )

        # Pricing
        dur_hours, base_rent, deposit, total_hold = PricingEngine.calculate_price(
            listing=selected_listing,
            start_time=req.start_time,
            end_time=req.end_time
        )

        booking_ref = f"AGL-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # Create booking linked to AgriLink job
        booking = Booking(
            booking_ref=booking_ref,
            vehicle_id=selected_vehicle.id,
            renter_citizen_id=req.delivery_person_citizen_id,
            renter_name=req.delivery_person_name,
            renter_kyc_tier=req.delivery_person_kyc_tier,
            renter_licence_classes=req.delivery_person_licence_classes,
            start_time=req.start_time,
            end_time=req.end_time,
            status=BookingStatus.PENDING_HOLD,
            agrilink_job_ref=req.agrilink_job_ref,
            estimated_duration_hours=dur_hours,
            base_rent_amount=base_rent,
            deposit_amount=deposit,
            total_hold_amount=total_hold,
            wallet_hold_status=WalletHoldStatus.NONE,
            idempotency_key=req.idempotency_key
        )
        db.add(booking)
        db.flush()

        # Execute Booking Saga with Wallet CIS-M6 hold
        saga_ok, saga_msg = BookingSagaCoordinator.execute_booking_saga(
            db=db,
            booking=booking,
            vehicle=selected_vehicle,
            correlation_id=correlation_id
        )

        if not saga_ok:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"AgriLink assignment hold failed on delivery wallet: {saga_msg}"
            )

        # Transition vehicle to IN_TRANSIT (RTO-FR-12 & RTO-FR-04)
        selected_vehicle.status = VehicleStatus.IN_TRANSIT
        selected_vehicle.updated_at = datetime.utcnow()

        # Publish VehicleAssigned event for AgriLink (AGL-M5)
        record_event(
            db=db,
            event_type="VehicleAssigned",
            aggregate_type="BOOKING",
            aggregate_id=booking.id,
            payload={
                "agrilink_job_ref": req.agrilink_job_ref,
                "booking_ref": booking.booking_ref,
                "vehicle_id": selected_vehicle.id,
                "registration_number": selected_vehicle.registration_number,
                "vehicle_class": selected_vehicle.vehicle_class,
                "make_model": selected_vehicle.make_model,
                "capacity_kg": selected_vehicle.capacity_kg,
                "delivery_person_citizen_id": req.delivery_person_citizen_id,
                "pickup_location": selected_listing.pickup_location,
                "status": "IN_TRANSIT"
            },
            correlation_id=correlation_id
        )

        log_audit_trail(
            db=db,
            actor_id="AGRILINK_SERVICE",
            actor_role="SYSTEM_SERVICE",
            action="AGRILINK_VEHICLE_ASSIGNED",
            entity_type="BOOKING",
            entity_id=booking.id,
            details={"job_ref": req.agrilink_job_ref, "vehicle_reg": selected_vehicle.registration_number},
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(booking)
        return booking

