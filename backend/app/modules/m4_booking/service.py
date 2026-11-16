import uuid
import json
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from fastapi import HTTPException, status

from app.models.vehicle import Vehicle, VehicleStatus, VehicleClass
from app.models.listing import RentalListing, ListingStatus
from app.models.booking import Booking, BookingStatus, HandoverRecord, WalletHoldStatus
from app.schemas.booking import BookingCreateRequest, HandoverCreateRequest, ReturnCreateRequest, CancellationRequest
from app.modules.m4_booking.pricing import PricingEngine
from app.modules.m4_booking.saga import BookingSagaCoordinator
from app.inter_service.wallet_client import WalletClient
from app.inter_service.outbox import record_event
from app.api.deps import log_audit_trail

class BookingService:

    @classmethod
    def create_booking(
        cls,
        db: Session,
        booking_in: BookingCreateRequest,
        renter_actor: dict,
        correlation_id: Optional[str] = None
    ) -> Booking:
        """
        RTO-FR-08: Booking request with eligibility and overlap prevention (RTO-N01).
        RTO-FR-09: Pricing and wallet fund hold before confirmation (RTO-N02).
        """
        renter_id = renter_actor["citizen_id"]
        renter_name = renter_actor["name"]
        kyc_tier = renter_actor.get("kyc_tier", "T0")
        licence_classes = renter_actor.get("driving_licence_classes", [])

        # 1. Eligibility Check (RTO-FR-08: KYC tier T1 or higher)
        if kyc_tier not in ["T1", "T2", "T3"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"KYC Verification failed: Your current tier '{kyc_tier}' is below the required Tier 1 (T1) verification for vehicle rentals."
            )

        # 2. Fetch Vehicle & Listing
        vehicle = db.query(Vehicle).filter(Vehicle.id == booking_in.vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        listing = db.query(RentalListing).filter(RentalListing.vehicle_id == vehicle.id).first()
        if not listing or listing.status != ListingStatus.ACTIVE:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This vehicle is currently not active for rent.")

        # 3. Driving Licence Class Check (RTO-FR-08)
        required_class = "LMV"
        if vehicle.vehicle_class == VehicleClass.HEAVY_COMMERCIAL:
            required_class = "HMV"
        elif vehicle.vehicle_class == VehicleClass.TRACTOR:
            required_class = "TRACTOR"
        elif vehicle.vehicle_class == VehicleClass.TWO_WHEELER:
            required_class = "MCWG"

        if required_class not in licence_classes and "HMV" not in licence_classes and "ADMIN" not in renter_actor.get("personas", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Ineligible licence: Driving licence class '{required_class}' is required for {vehicle.vehicle_class} ({vehicle.make_model}). You hold: {licence_classes}"
            )

        # 4. Check Start and End Times
        start = booking_in.start_time
        end = booking_in.end_time
        if end <= start:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Booking end time must be after start time.")

        # 5. RTO-N01: Strict Overlap Prevention (Zero overlapping confirmed bookings)
        overlapping = (
            db.query(Booking)
            .filter(Booking.vehicle_id == vehicle.id)
            .filter(Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ACTIVE]))
            .filter(and_(Booking.start_time < end, Booking.end_time > start))
            .first()
        )
        if overlapping:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Overlap conflict: Vehicle is already booked from {overlapping.start_time.strftime('%Y-%m-%d %H:%M')} to {overlapping.end_time.strftime('%Y-%m-%d %H:%M')} (Ref: {overlapping.booking_ref})"
            )

        # 6. Calculate Price Breakdown (RTO-FR-09)
        dur_hours, base_rent, deposit, total_hold = PricingEngine.calculate_price(listing, start, end)

        # Generate human-readable reference
        booking_ref = f"BK-{datetime.utcnow().strftime('%y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        # 7. Create booking record
        booking = Booking(
            booking_ref=booking_ref,
            vehicle_id=vehicle.id,
            renter_citizen_id=renter_id,
            renter_name=renter_name,
            renter_kyc_tier=kyc_tier,
            renter_licence_classes=",".join(licence_classes),
            start_time=start,
            end_time=end,
            status=BookingStatus.PENDING_HOLD,
            estimated_duration_hours=dur_hours,
            base_rent_amount=base_rent,
            deposit_amount=deposit,
            total_hold_amount=total_hold,
            wallet_hold_status=WalletHoldStatus.NONE,
            idempotency_key=booking_in.idempotency_key
        )
        db.add(booking)
        db.flush()

        # 8. Execute Booking Saga with Wallet CIS-M6 Hold (RTO-FR-09, RTO-N02)
        saga_ok, saga_msg = BookingSagaCoordinator.execute_booking_saga(
            db=db,
            booking=booking,
            vehicle=vehicle,
            correlation_id=correlation_id
        )

        if not saga_ok:
            db.commit()
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail=f"Booking reservation failed: {saga_msg}"
            )

        log_audit_trail(
            db=db,
            actor_id=renter_id,
            actor_role="RENTER",
            action="BOOKING_CONFIRMED",
            entity_type="BOOKING",
            entity_id=booking.id,
            details={"booking_ref": booking_ref, "total_hold": total_hold},
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(booking)
        return booking

    @classmethod
    def record_handover(
        cls,
        db: Session,
        booking_id: str,
        handover_in: HandoverCreateRequest,
        actor: dict,
        correlation_id: Optional[str] = None
    ) -> Booking:
        """
        RTO-FR-10: Vehicle Handover record.
        Transitions vehicle to RENTED and booking to ACTIVE.
        """
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        if booking.status != BookingStatus.CONFIRMED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot record handover for booking in '{booking.status}' status. Must be CONFIRMED."
            )

        # Record handover metrics
        handover = HandoverRecord(
            booking_id=booking.id,
            handover_type="HANDOVER",
            recorded_by_citizen_id=actor["citizen_id"],
            odometer_reading=handover_in.odometer_reading,
            fuel_level_percent=handover_in.fuel_level_percent,
            condition_notes=handover_in.condition_notes,
            photos=json.dumps(handover_in.photos or [])
        )
        db.add(handover)

        # Update Booking and Vehicle states
        booking.status = BookingStatus.ACTIVE
        vehicle = db.query(Vehicle).filter(Vehicle.id == booking.vehicle_id).first()
        if vehicle:
            vehicle.status = VehicleStatus.RENTED
            vehicle.updated_at = datetime.utcnow()

        log_audit_trail(
            db=db,
            actor_id=actor["citizen_id"],
            actor_role="OPERATOR",
            action="HANDOVER_COMPLETED",
            entity_type="BOOKING",
            entity_id=booking.id,
            details={"odometer": handover_in.odometer_reading, "fuel": handover_in.fuel_level_percent},
            correlation_id=correlation_id
        )

        record_event(
            db=db,
            event_type="VehicleHandoverCompleted",
            aggregate_type="BOOKING",
            aggregate_id=booking.id,
            payload={
                "booking_id": booking.id,
                "booking_ref": booking.booking_ref,
                "vehicle_id": vehicle.id if vehicle else None,
                "odometer": handover_in.odometer_reading
            },
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(booking)
        return booking

    @classmethod
    def record_return(
        cls,
        db: Session,
        booking_id: str,
        return_in: ReturnCreateRequest,
        actor: dict,
        correlation_id: Optional[str] = None
    ) -> Booking:
        """
        RTO-FR-10: Vehicle Return record and wallet settlement.
        Releases rent to owner, refunds remaining deposit or deducts damage.
        """
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        if booking.status != BookingStatus.ACTIVE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot record return for booking in '{booking.status}' status. Must be ACTIVE."
            )

        vehicle = db.query(Vehicle).filter(Vehicle.id == booking.vehicle_id).first()

        # Record return metrics
        ret_record = HandoverRecord(
            booking_id=booking.id,
            handover_type="RETURN",
            recorded_by_citizen_id=actor["citizen_id"],
            odometer_reading=return_in.odometer_reading,
            fuel_level_percent=return_in.fuel_level_percent,
            condition_notes=return_in.condition_notes,
            damage_detected=return_in.damage_detected,
            damage_amount=return_in.damage_amount,
            photos=json.dumps(return_in.photos or [])
        )
        db.add(ret_record)

        # 1. Instruct Wallet CIS-M6: Release base rent to Vehicle Owner
        if booking.wallet_hold_id:
            WalletClient.release_hold(
                hold_id=booking.wallet_hold_id,
                amount_to_owner=booking.base_rent_amount,
                owner_citizen_id=vehicle.owner_citizen_id if vehicle else "SYSTEM_OWNER",
                reference_id=booking.booking_ref
            )

            # 2. Instruct Wallet CIS-M6: Refund deposit minus damage to Renter
            deposit_refund = max(0.0, booking.deposit_amount - return_in.damage_amount)
            if deposit_refund > 0:
                WalletClient.refund_hold(
                    hold_id=booking.wallet_hold_id,
                    refund_amount=deposit_refund,
                    reference_id=booking.booking_ref
                )

        # Update lifecycle state
        booking.status = BookingStatus.COMPLETED
        booking.refund_amount = max(0.0, booking.deposit_amount - return_in.damage_amount)

        if vehicle:
            # If damage was noted, move to UNDER_MAINTENANCE; otherwise AVAILABLE
            if return_in.damage_detected and return_in.damage_amount > 0:
                vehicle.status = VehicleStatus.UNDER_MAINTENANCE
            else:
                vehicle.status = VehicleStatus.AVAILABLE
            vehicle.updated_at = datetime.utcnow()

        log_audit_trail(
            db=db,
            actor_id=actor["citizen_id"],
            actor_role="OPERATOR",
            action="RETURN_AND_SETTLED",
            entity_type="BOOKING",
            entity_id=booking.id,
            details={
                "odometer": return_in.odometer_reading,
                "damage_detected": return_in.damage_detected,
                "damage_amount": return_in.damage_amount
            },
            correlation_id=correlation_id
        )

        record_event(
            db=db,
            event_type="RentalSettlementCompleted",
            aggregate_type="BOOKING",
            aggregate_id=booking.id,
            payload={
                "booking_id": booking.id,
                "booking_ref": booking.booking_ref,
                "released_to_owner": booking.base_rent_amount,
                "refunded_to_renter": booking.refund_amount,
                "damage_deducted": return_in.damage_amount
            },
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(booking)
        return booking

    @classmethod
    def cancel_booking(
        cls,
        db: Session,
        booking_id: str,
        cancel_in: CancellationRequest,
        actor: dict,
        correlation_id: Optional[str] = None
    ) -> Booking:
        """
        RTO-FR-11: Cancellation policy and refund.
        """
        booking = db.query(Booking).filter(Booking.id == booking_id).first()
        if not booking:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

        if booking.status not in [BookingStatus.CONFIRMED, BookingStatus.PENDING_HOLD]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel booking in '{booking.status}' status."
            )

        now = datetime.utcnow()
        vehicle = db.query(Vehicle).filter(Vehicle.id == booking.vehicle_id).first()

        # Calculate cancellation fee and refund based on policy
        cancellation_fee, refund_amount = PricingEngine.calculate_cancellation_refund(
            start_time=booking.start_time,
            cancelled_at=now,
            total_hold_amount=booking.total_hold_amount,
            deposit_amount=booking.deposit_amount,
            base_rent_amount=booking.base_rent_amount
        )

        # Process wallet refund
        if booking.wallet_hold_id:
            if cancellation_fee > 0 and vehicle:
                # Release cancellation fee penalty to owner
                WalletClient.release_hold(
                    hold_id=booking.wallet_hold_id,
                    amount_to_owner=cancellation_fee,
                    owner_citizen_id=vehicle.owner_citizen_id,
                    reference_id=f"CANCEL-FEE-{booking.booking_ref}"
                )
            # Refund remaining amount to renter
            WalletClient.refund_hold(
                hold_id=booking.wallet_hold_id,
                refund_amount=refund_amount,
                reference_id=f"CANCEL-REFUND-{booking.booking_ref}"
            )

        booking.status = BookingStatus.CANCELLED
        booking.cancellation_reason = cancel_in.reason
        booking.cancellation_fee = cancellation_fee
        booking.refund_amount = refund_amount
        booking.cancelled_by = actor["citizen_id"]
        booking.cancelled_at = now

        # Vehicle returns to AVAILABLE
        if vehicle:
            vehicle.status = VehicleStatus.AVAILABLE
            vehicle.updated_at = now

        log_audit_trail(
            db=db,
            actor_id=actor["citizen_id"],
            actor_role="RENTER",
            action="BOOKING_CANCELLED",
            entity_type="BOOKING",
            entity_id=booking.id,
            details={"fee": cancellation_fee, "refund": refund_amount, "reason": cancel_in.reason},
            correlation_id=correlation_id
        )

        record_event(
            db=db,
            event_type="BookingCancelled",
            aggregate_type="BOOKING",
            aggregate_id=booking.id,
            payload={
                "booking_id": booking.id,
                "booking_ref": booking.booking_ref,
                "cancellation_fee": cancellation_fee,
                "refund_amount": refund_amount
            },
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(booking)
        return booking

