import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base

class BookingStatus:
    PENDING_HOLD = "PENDING_HOLD"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"

class WalletHoldStatus:
    NONE = "NONE"
    HOLD_REQUESTED = "HOLD_REQUESTED"
    FUNDS_HELD = "FUNDS_HELD"
    RELEASED = "RELEASED"
    REFUNDED = "REFUNDED"
    FAILED = "FAILED"

class Booking(Base):
    __tablename__ = "bookings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_ref = Column(String(32), unique=True, nullable=False, index=True)
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    
    # Renter details (RTO-FR-08: KYC tier T1 or higher, valid licence from token claims)
    renter_citizen_id = Column(String(64), nullable=False, index=True)
    renter_name = Column(String(100), nullable=False)
    renter_kyc_tier = Column(String(16), nullable=False)
    renter_licence_classes = Column(String(255), nullable=False) # e.g. "LMV,HMV"
    
    # Booking timeslot
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    
    status = Column(String(32), nullable=False, default=BookingStatus.PENDING_HOLD, index=True)
    
    # AgriLink delivery job reference (RTO-FR-12: AgriLink assignment)
    agrilink_job_ref = Column(String(64), nullable=True, index=True)
    
    # Financial breakdown (RTO-FR-09)
    estimated_duration_hours = Column(Float, nullable=False, default=1.0)
    base_rent_amount = Column(Float, nullable=False, default=0.0)
    deposit_amount = Column(Float, nullable=False, default=0.0)
    total_hold_amount = Column(Float, nullable=False, default=0.0)
    
    # Wallet Hold & Idempotency (CIS-M6)
    wallet_hold_id = Column(String(64), nullable=True, index=True)
    wallet_hold_status = Column(String(32), default=WalletHoldStatus.NONE)
    idempotency_key = Column(String(128), unique=True, nullable=False, index=True)
    
    # Cancellation & Refund (RTO-FR-11)
    cancellation_reason = Column(String(255), nullable=True)
    cancellation_fee = Column(Float, default=0.0)
    refund_amount = Column(Float, default=0.0)
    cancelled_by = Column(String(64), nullable=True)
    cancelled_at = Column(DateTime, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="bookings")
    saga = relationship("BookingSaga", back_populates="booking", uselist=False, cascade="all, delete-orphan")
    handover_records = relationship("HandoverRecord", back_populates="booking", cascade="all, delete-orphan")

class SagaState:
    STARTED = "STARTED"
    HOLD_REQUESTED = "HOLD_REQUESTED"
    CONFIRMED = "CONFIRMED"
    EXPIRED_CANCELLED = "EXPIRED_CANCELLED"
    COMPLETED = "COMPLETED"

class BookingSaga(Base):
    __tablename__ = "booking_sagas"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = Column(String(36), ForeignKey("bookings.id"), unique=True, nullable=False)
    saga_state = Column(String(32), nullable=False, default=SagaState.STARTED)
    deadline = Column(DateTime, nullable=False) # 60 seconds from creation (RTO-N02)
    compensation_reason = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    booking = relationship("Booking", back_populates="saga")

class HandoverRecord(Base):
    __tablename__ = "handover_records"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    booking_id = Column(String(36), ForeignKey("bookings.id"), nullable=False, index=True)
    handover_type = Column(String(16), nullable=False) # "HANDOVER" or "RETURN"
    recorded_by_citizen_id = Column(String(64), nullable=False)
    
    # Vehicle metrics (RTO-FR-10)
    odometer_reading = Column(Float, nullable=False)
    fuel_level_percent = Column(Float, nullable=False)
    condition_notes = Column(Text, nullable=True)
    damage_detected = Column(Boolean, default=False)
    damage_amount = Column(Float, default=0.0)
    photos = Column(Text, nullable=True) # JSON array of photo file references
    timestamp = Column(DateTime, default=datetime.utcnow)

    booking = relationship("Booking", back_populates="handover_records")

