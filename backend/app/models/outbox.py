import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Text, Integer

from app.database import Base

class OutboxEvent(Base):
    __tablename__ = "outbox_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(64), nullable=False, index=True)
    aggregate_type = Column(String(32), nullable=False, index=True)
    aggregate_id = Column(String(64), nullable=False, index=True)
    payload = Column(Text, nullable=False) # JSON serialized data
    
    published = Column(Boolean, default=False, index=True)
    published_at = Column(DateTime, nullable=True)
    retry_count = Column(Integer, default=0)
    correlation_id = Column(String(64), nullable=True, index=True)
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)

