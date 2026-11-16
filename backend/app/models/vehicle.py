import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Boolean, ForeignKey, Text, Enum as SQLEnum
from sqlalchemy.orm import relationship

from app.database import Base

class VehicleStatus:
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    AVAILABLE = "AVAILABLE"
    RESERVED = "RESERVED"
    RENTED = "RENTED"
    IN_TRANSIT = "IN_TRANSIT"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"
    SUSPENDED = "SUSPENDED"

class VerificationStatus:
    PENDING = "PENDING"
    VERIFIED = "VERIFIED"
    REJECTED = "REJECTED"
    REQUIRES_ADMIN_REVIEW = "REQUIRES_ADMIN_REVIEW"

class VehicleClass:
    LIGHT_COMMERCIAL = "LIGHT_COMMERCIAL"      # Tata Ace, Mahindra Bolero Maxi
    HEAVY_COMMERCIAL = "HEAVY_COMMERCIAL"      # Trucks, 10-wheelers
    TRACTOR = "TRACTOR"                        # Agricultural tractors
    MINI_TRUCK = "MINI_TRUCK"                  # Small goods carriers
    AUTO_RICKSHAW = "AUTO_RICKSHAW"            # 3-wheeler goods/transport
    CAR = "CAR"
    TWO_WHEELER = "TWO_WHEELER"

class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    registration_number = Column(String(32), unique=True, nullable=False, index=True)
    vehicle_class = Column(String(32), nullable=False, index=True)
    make_model = Column(String(100), nullable=False)
    capacity_kg = Column(Float, nullable=False, default=500.0)
    seating_capacity = Column(Integer, nullable=False, default=2)
    fuel_type = Column(String(20), nullable=False, default="DIESEL")
    
    # Ownership (RTO-FR-03: plain citizen_id value, no foreign key into Identity microservice)
    owner_citizen_id = Column(String(64), nullable=False, index=True)
    owner_name = Column(String(100), nullable=False)
    
    # Lifecycle & Verification States (RTO-FR-02, RTO-FR-04)
    status = Column(String(32), nullable=False, default=VehicleStatus.PENDING, index=True)
    verification_status = Column(String(32), nullable=False, default=VerificationStatus.PENDING)
    verification_reason = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    documents = relationship("VehicleDocument", back_populates="vehicle", cascade="all, delete-orphan")
    verification_requests = relationship("VerificationRequest", back_populates="vehicle", cascade="all, delete-orphan")
    listings = relationship("RentalListing", back_populates="vehicle", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="vehicle", cascade="all, delete-orphan")

class DocumentType:
    RC = "RC"
    INSURANCE = "INSURANCE"
    FITNESS = "FITNESS"
    PERMIT = "PERMIT"
    PUC = "PUC"

class VehicleDocument(Base):
    __tablename__ = "vehicle_documents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    document_type = Column(String(32), nullable=False, index=True)
    document_number = Column(String(64), nullable=False)
    file_reference = Column(String(255), nullable=False) # Encrypted file store reference
    issue_date = Column(DateTime, nullable=True)
    expiry_date = Column(DateTime, nullable=True, index=True) # Critical for RTO-FR-13 compliance check
    is_valid = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="documents")

class VerificationRequest(Base):
    __tablename__ = "verification_requests"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="PENDING_RETRY")
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=5)
    next_retry_at = Column(DateTime, nullable=True)
    adapter_response = Column(Text, nullable=True)
    admin_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="verification_requests")

