import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import Session

from app.models.outbox import OutboxEvent

logger = logging.getLogger("rto_outbox")

def record_event(
    db: Session,
    event_type: str,
    aggregate_type: str,
    aggregate_id: str,
    payload: Dict[str, Any],
    correlation_id: Optional[str] = None
) -> OutboxEvent:
    """
    Transactional Outbox Pattern (S06: REST plus broker events).
    Writes an event within the exact same database transaction as the entity mutation.
    """
    event = OutboxEvent(
        event_type=event_type,
        aggregate_type=aggregate_type,
        aggregate_id=str(aggregate_id),
        payload=json.dumps(payload, default=str),
        correlation_id=correlation_id,
        published=False,
        retry_count=0,
        created_at=datetime.utcnow()
    )
    db.add(event)
    db.flush()
    logger.info(f"[OUTBOX_RECORDED] Event: {event_type} | Aggregate: {aggregate_type}:{aggregate_id}")
    return event

def dispatch_pending_events(db: Session, max_batch: int = 50) -> List[OutboxEvent]:
    """
    Polls and marks outbox events as published, simulating event bus publish (Kafka / RabbitMQ / Cloud PubSub).
    """
    events = (
        db.query(OutboxEvent)
        .filter(OutboxEvent.published == False)
        .order_by(OutboxEvent.created_at.asc())
        .limit(max_batch)
        .all()
    )
    for event in events:
        event.published = True
        event.published_at = datetime.utcnow()
        logger.info(f"[OUTBOX_DISPATCHED] Published {event.event_type} id={event.id}")
    db.commit()
    return events

