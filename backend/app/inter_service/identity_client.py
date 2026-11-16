import jwt
from typing import Optional, List, Dict
from datetime import datetime, timedelta
from app.config import settings

# Pre-configured mock citizens representing ecosystem personas
MOCK_CITIZENS: Dict[str, dict] = {
    "CIT-OWNER-001": {
        "citizen_id": "CIT-OWNER-001",
        "name": "Ramesh Patil",
        "kyc_tier": "T2",
        "personas": ["CITIZEN", "VEHICLE_OWNER"],
        "driving_licence_classes": ["LMV", "HMV", "TRACTOR"],
        "licence_valid_till": "2030-05-15T00:00:00"
    },
    "CIT-RENTER-002": {
        "citizen_id": "CIT-RENTER-002",
        "name": "Priya Sharma",
        "kyc_tier": "T2",
        "personas": ["CITIZEN", "RENTER"],
        "driving_licence_classes": ["LMV", "MCWG"],
        "licence_valid_till": "2029-08-20T00:00:00"
    },
    "CIT-RENTER-LOWKYC": {
        "citizen_id": "CIT-RENTER-LOWKYC",
        "name": "Anil Kumar (T0 Unverified)",
        "kyc_tier": "T0", # Fails RTO-FR-08 (requires T1 or higher)
        "personas": ["CITIZEN", "RENTER"],
        "driving_licence_classes": ["LMV"],
        "licence_valid_till": "2028-01-01T00:00:00"
    },
    "CIT-DELIVERY-003": {
        "citizen_id": "CIT-DELIVERY-003",
        "name": "Suresh Gowda (AgriLink Delivery)",
        "kyc_tier": "T3",
        "personas": ["CITIZEN", "DELIVERY_PERSON"],
        "driving_licence_classes": ["LMV", "HMV"],
        "licence_valid_till": "2032-11-10T00:00:00"
    },
    "CIT-ADMIN-001": {
        "citizen_id": "CIT-ADMIN-001",
        "name": "Officer V. K. Rao",
        "kyc_tier": "T3",
        "personas": ["CITIZEN", "ADMIN", "RTO_OFFICIAL"],
        "driving_licence_classes": ["LMV"],
        "licence_valid_till": "2035-01-01T00:00:00"
    }
}

def generate_mock_token(citizen_id: str, custom_claims: Optional[dict] = None) -> str:
    """Helper to generate JWT tokens for testing or demo sessions."""
    citizen = MOCK_CITIZENS.get(citizen_id, {
        "citizen_id": citizen_id,
        "name": "Citizen User",
        "kyc_tier": "T1",
        "personas": ["CITIZEN", "RENTER"],
        "driving_licence_classes": ["LMV"],
        "licence_valid_till": "2030-01-01T00:00:00"
    })
    claims = {
        "sub": citizen["citizen_id"],
        "citizen_id": citizen["citizen_id"],
        "name": citizen["name"],
        "kyc_tier": citizen["kyc_tier"],
        "personas": citizen["personas"],
        "driving_licence_classes": citizen["driving_licence_classes"],
        "exp": datetime.utcnow() + timedelta(days=7),
        "iss": "agrilink-cis-identity"
    }
    if custom_claims:
        claims.update(custom_claims)
    return jwt.encode(claims, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def decode_token_claims(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except Exception:
        # Fallback: check if the token is a mock citizen ID directly
        if token in MOCK_CITIZENS:
            return MOCK_CITIZENS[token]
        return None

