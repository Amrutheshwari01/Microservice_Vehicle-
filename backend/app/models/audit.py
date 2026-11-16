import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text

from app.database import Base

class AuditEvent(Base):
    __tablename__ = "audit_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    actor_id = Column(String(64), nullable=False, index=True)
    actor_role = Column(String(32), nullable=False, index=True)
    action = Column(String(64), nullable=False, index=True)
    entity_type = Column(String(32), nullable=False, index=True)
    entity_id = Column(String(64), nullable=False, index=True)
    details = Column(Text, nullable=True) # JSON details
    correlation_id = Column(String(64), nullable=True, index=True)

