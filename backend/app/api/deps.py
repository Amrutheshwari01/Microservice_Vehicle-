import json
from typing import Optional
from fastapi import Header, HTTPException, status, Depends, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.inter_service.identity_client import decode_token_claims, MOCK_CITIZENS
from app.models.audit import AuditEvent

def get_current_actor(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_citizen_id: Optional[str] = Header(None)
) -> dict:
    """
    Extracts authenticated citizen claims from JWT token or fallback citizen header (CIS-M4).
    """
    token = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
    elif x_citizen_id:
        token = x_citizen_id

    if not token:
        # Default guest/visitor persona
        return {
            "citizen_id": "GUEST_VISITOR",
            "name": "Anonymous Visitor",
            "kyc_tier": "T0",
            "personas": ["VISITOR"],
            "driving_licence_classes": []
        }

    claims = decode_token_claims(token)
    if not claims:
        # Check if direct mock ID was passed
        if token in MOCK_CITIZENS:
            claims = MOCK_CITIZENS[token]
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired identity token from Citizen Identity Service (CIS-M4)"
            )
            
    return claims

def require_vehicle_owner(actor: dict = Depends(get_current_actor)) -> dict:
    personas = actor.get("personas", [])
    if "VEHICLE_OWNER" not in personas and "ADMIN" not in personas:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Requires Vehicle Owner persona in Citizen Identity token"
        )
    return actor

def require_renter(actor: dict = Depends(get_current_actor)) -> dict:
    # RTO-FR-08: Renter registered, KYC tier T1 or higher, valid licence
    kyc_tier = actor.get("kyc_tier", "T0")
    if kyc_tier not in ["T1", "T2", "T3"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Ineligible for booking: KYC tier '{kyc_tier}' is below minimum required Tier 1 (T1) verification."
        )
    return actor

def require_admin(actor: dict = Depends(get_current_actor)) -> dict:
    personas = actor.get("personas", [])
    if "ADMIN" not in personas and "RTO_OFFICIAL" not in personas:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Requires Administrator or RTO Official credentials"
        )
    return actor

def log_audit_trail(
    db: Session,
    actor_id: str,
    actor_role: str,
    action: str,
    entity_type: str,
    entity_id: str,
    details: Optional[dict] = None,
    correlation_id: Optional[str] = None
):
    audit = AuditEvent(
        actor_id=actor_id,
        actor_role=actor_role,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id),
        details=json.dumps(details or {}, default=str),
        correlation_id=correlation_id
    )
    db.add(audit)
    db.flush()

