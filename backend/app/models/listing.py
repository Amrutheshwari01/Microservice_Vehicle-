import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base

class ListingStatus:
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    WITHDRAWN = "WITHDRAWN"

class RentalListing(Base):
    __tablename__ = "rental_listings"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), unique=True, nullable=False, index=True)
    owner_citizen_id = Column(String(64), nullable=False, index=True)
    
    # Rate Card (RTO-FR-06)
    rate_per_hour = Column(Float, nullable=False, default=150.0)
    rate_per_day = Column(Float, nullable=False, default=1200.0)
    rate_per_km = Column(Float, nullable=False, default=12.0)
    security_deposit = Column(Float, nullable=False, default=2000.0)
    
    # Location & Rules
    pickup_location = Column(String(255), nullable=False)
    pickup_coordinates = Column(String(64), nullable=True) # e.g. "13.0358,77.5970"
    rental_rules = Column(Text, nullable=True)
    
    status = Column(String(32), nullable=False, default=ListingStatus.ACTIVE, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    vehicle = relationship("Vehicle", back_populates="listings")
    availability_windows = relationship("AvailabilityWindow", back_populates="listing", cascade="all, delete-orphan")

class AvailabilityWindow(Base):
    __tablename__ = "availability_windows"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    listing_id = Column(String(36), ForeignKey("rental_listings.id"), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False, index=True)
    is_available = Column(Boolean, default=True)
    notes = Column(String(255), nullable=True)

    listing = relationship("RentalListing", back_populates="availability_windows")

