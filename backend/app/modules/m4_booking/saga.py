import uuid
import logging
from datetime import datetime, timedelta
from typing import Tuple
from sqlalchemy.orm import Session

from app.models.booking import Booking, BookingSaga, BookingStatus, SagaState, WalletHoldStatus
from app.models.vehicle import Vehicle, VehicleStatus
from app.inter_service.wallet_client import WalletClient
from app.inter_service.outbox import record_event
from app.config import settings

logger = logging.getLogger("rto_booking_saga")

class BookingSagaCoordinator:
    """
    RTO-FR-09 & RTO-N02:
    Booking Saga Coordinator enforcing:
    1. Wallet fund hold before confirmation.
    2. Zero booking confirmed without a wallet hold.
    3. Auto-cancellation within 60s if the hold fails or times out.
    """

    @classmethod
    def execute_booking_saga(
        cls,
        db: Session,
        booking: Booking,
        vehicle: Vehicle,
        correlation_id: str = None
    ) -> Tuple[bool, str]:
        # 1. Initialize Saga
        deadline = datetime.utcnow() + timedelta(seconds=settings.BOOKING_HOLD_TIMEOUT_SECONDS)
        saga = BookingSaga(
            booking_id=booking.id,
            saga_state=SagaState.STARTED,
            deadline=deadline
        )
        db.add(saga)
        db.flush()

        logger.info(f"[SAGA_STARTED] Booking: {booking.booking_ref} | Total Hold: ₹{booking.total_hold_amount}")

        # 2. Call Wallet Service (CIS-M6) to hold funds
        saga.saga_state = SagaState.HOLD_REQUESTED
        booking.wallet_hold_status = WalletHoldStatus.HOLD_REQUESTED
        
        success, hold_id, message = WalletClient.create_hold(
            citizen_id=booking.renter_citizen_id,
            amount=booking.total_hold_amount,
            reference_id=booking.booking_ref,
            idempotency_key=booking.idempotency_key
        )

        if not success:
            # Compensate / Abort: Auto-cancel booking within 60s per RTO-N02
            logger.warning(f"[SAGA_COMPENSATING] Wallet hold failed for {booking.booking_ref}: {message}")
            saga.saga_state = SagaState.EXPIRED_CANCELLED
            saga.compensation_reason = f"Wallet hold rejected: {message}"
            
            booking.status = BookingStatus.FAILED
            booking.wallet_hold_status = WalletHoldStatus.FAILED
            
            # Vehicle returns to AVAILABLE
            vehicle.status = VehicleStatus.AVAILABLE
            
            record_event(
                db=db,
                event_type="BookingFailed",
                aggregate_type="BOOKING",
                aggregate_id=booking.id,
                payload={"booking_ref": booking.booking_ref, "reason": message},
                correlation_id=correlation_id
            )
            return False, message

        # 3. Hold Succeeded (FundsHeld received) -> Confirm Booking
        booking.wallet_hold_id = hold_id
        booking.wallet_hold_status = WalletHoldStatus.FUNDS_HELD
        booking.status = BookingStatus.CONFIRMED
        
        saga.saga_state = SagaState.CONFIRMED
        vehicle.status = VehicleStatus.RESERVED
        vehicle.updated_at = datetime.utcnow()

        record_event(
            db=db,
            event_type="BookingConfirmed",
            aggregate_type="BOOKING",
            aggregate_id=booking.id,
            payload={
                "booking_id": booking.id,
                "booking_ref": booking.booking_ref,
                "vehicle_id": vehicle.id,
                "renter_citizen_id": booking.renter_citizen_id,
                "hold_id": hold_id,
                "total_hold_amount": booking.total_hold_amount
            },
            correlation_id=correlation_id
        )

        logger.info(f"[SAGA_COMPLETED] Booking {booking.booking_ref} CONFIRMED with hold {hold_id}")
        return True, "Booking confirmed with wallet fund hold"

