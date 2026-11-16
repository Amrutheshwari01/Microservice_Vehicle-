from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field

# Wallet CIS-M6 contracts
class WalletHoldRequest(BaseModel):
    citizen_id: str
    amount: float
    currency: str = "INR"
    purpose: str = "VEHICLE_RENTAL_HOLD"
    reference_id: str
    idempotency_key: str

class WalletHoldResponse(BaseModel):
    hold_id: str
    citizen_id: str
    amount: float
    status: str # "HELD", "REJECTED", "EXPIRED"
    created_at: datetime
    message: Optional[str] = None

class WalletReleaseRequest(BaseModel):
    hold_id: str
    amount_to_release: float # Amount paid to owner
    reference_id: str
    beneficiary_citizen_id: str # Owner's wallet

class WalletRefundRequest(BaseModel):
    hold_id: str
    amount_to_refund: float # Amount returned to renter
    reference_id: str

class WalletWebhookPayload(BaseModel):
    event: str # "FundsHeld", "FundsReleased", "FundsRefunded", "HoldExpired"
    hold_id: str
    booking_id: str
    amount: float
    timestamp: datetime
    status: str

# Identity CIS-M4 contracts
class CitizenIdentityToken(BaseModel):
    citizen_id: str
    name: str
    kyc_tier: str # "T0", "T1", "T2", "T3"
    personas: List[str] # ["CITIZEN", "VEHICLE_OWNER", "RENTER", "ADMIN", "RTO_OFFICIAL"]
    driving_licence_classes: List[str] # ["LMV", "HMV", "MCWG"]
    licence_valid_till: Optional[datetime] = None

# Transactional Outbox & Events
class OutboxEventResponse(BaseModel):
    id: str
    event_type: str
    aggregate_type: str
    aggregate_id: str
    payload: str
    published: bool
    published_at: Optional[datetime]
    retry_count: int
    correlation_id: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True

# Audit & Records
class AuditEventResponse(BaseModel):
    id: str
    timestamp: datetime
    actor_id: str
    actor_role: str
    action: str
    entity_type: str
    entity_id: str
    details: Optional[str]
    correlation_id: Optional[str]

    class Config:
        from_attributes = True

