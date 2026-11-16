import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(String(64), primary_key=True, default=lambda: f"CIT-{uuid.uuid4().hex[:8].upper()}")
    name = Column(String(120), nullable=False)
    email = Column(String(120), unique=True, nullable=False, index=True)
    phone = Column(String(20), nullable=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="RENTER") # "RENTER", "VEHICLE_OWNER", "DELIVERY_PERSON", "ADMIN"
    kyc_tier = Column(String(16), nullable=False, default="T1") # "T0", "T1", "T2", "T3"
    driving_licence_classes = Column(String(100), nullable=False, default="LMV") # "LMV,HMV,TRACTOR,MCWG"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

