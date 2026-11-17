from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, Body, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.outbox import OutboxEvent
from app.schemas.inter_service import OutboxEventResponse, WalletWebhookPayload
from app.inter_service.outbox import dispatch_pending_events
from app.inter_service.identity_client import MOCK_CITIZENS, generate_mock_token
from app.inter_service.wallet_client import WalletClient

router = APIRouter(prefix="/inter-service", tags=["Microservice Connectivity & Data Exchange (S06)"])

@router.get("/catalog")
def get_microservice_catalog():
    """
    Service catalog metadata for AgriLink ecosystem service discovery.
    Provides data contracts, event topics, and API versions.
    """
    return {
        "service_name": "rto-vehicle-registry-rental-service",
        "service_version": "1.0.0",
        "ecosystem": "AgriLink",
        "microservice_id": "MS-03",
        "published_events": [
            {
                "topic": "agrilink.rto.vehicle.registered",
                "event_type": "VehicleRegistered",
                "description": "Emitted when a citizen registers a vehicle"
            },
            {
                "topic": "agrilink.rto.vehicle.assigned",
                "event_type": "VehicleAssigned",
                "description": "Emitted when a vehicle is assigned to an AgriLink delivery job (RTO-FR-12)"
            },
            {
                "topic": "agrilink.rto.booking.confirmed",
                "event_type": "BookingConfirmed",
                "description": "Emitted when a rental booking is confirmed with wallet fund hold"
            },
            {
                "topic": "agrilink.rto.settlement.completed",
                "event_type": "RentalSettlementCompleted",
                "description": "Emitted when a return is recorded and funds are released to owner"
            },
            {
                "topic": "agrilink.rto.compliance.expired",
                "event_type": "ComplianceBlockingTriggered",
                "description": "Emitted when expired compliance blocks vehicle listing or booking"
            }
        ],
        "consumed_services": [
            {
                "service": "Citizen Identity Service (CIS-M4)",
                "contract": "JWT tokens, KYC tier claims, driving licence classes"
            },
            {
                "service": "Citizen Wallet Service (CIS-M6)",
                "contract": "POST /v1/holds, /release, /refund (Hold rent and deposit before booking)"
            },
            {
                "service": "AgriLink Delivery System (AGL-M5)",
                "contract": "POST /v1/vehicle-requests (Request vehicle for delivery job)"
            },
            {
                "service": "External State RTO National Registry",
                "contract": "RC verification adapter with 24h backoff retry queue"
            }
        ]
    }

@router.get("/outbox", response_model=List[OutboxEventResponse])
def get_outbox_events(
    published_filter: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """
    Inspect the Transactional Outbox event queue for cross-microservice data exchange.
    """
    query = db.query(OutboxEvent)
    if published_filter is not None:
        query = query.filter(OutboxEvent.published == published_filter)
    return query.order_by(OutboxEvent.created_at.desc()).limit(limit).all()

@router.post("/outbox/dispatch")
def trigger_outbox_dispatch(
    db: Session = Depends(get_db)
):
    """
    Simulates the background Outbox Publisher worker polling and publishing events to the AgriLink message broker.
    """
    dispatched = dispatch_pending_events(db)
    return {
        "status": "SUCCESS",
        "dispatched_count": len(dispatched),
        "dispatched_events": [e.event_type for e in dispatched]
    }

@router.get("/mock-identity/citizens")
def list_mock_citizens():
    """
    List mock ecosystem citizens with ready-to-use Bearer JWT tokens for testing personas.
    """
    result = []
    for cid, data in MOCK_CITIZENS.items():
        token = generate_mock_token(cid)
        result.append({
            **data,
            "jwt_token": token
        })
    return result

@router.get("/mock-wallet/state")
def get_mock_wallet_state(citizen_id: Optional[str] = None):
    """
    Inspect mock Citizen Wallet balances and active rental fund holds.
    """
    return WalletClient.get_wallet_state(citizen_id)

@router.post("/mock-wallet/webhook")
def handle_wallet_webhook(payload: WalletWebhookPayload):
    """
    Inbound webhook for Wallet CIS-M6 asynchronous event callbacks.
    """
    return {
        "status": "RECEIVED",
        "event": payload.event,
        "hold_id": payload.hold_id,
        "processed_at": datetime.utcnow().isoformat()
    }

@router.get("/connectivity")
def check_inter_service_connectivity():
    """
    Live diagnostics verifying connection between Microservice_Vehicle (RTO)
    and Microservice_Citizen (CIS Identity & Wallet).
    """
    import httpx
    from app.config import settings

    target_url = getattr(settings, "CITIZEN_SERVICE_URL", "http://localhost:8001/api/v1")
    service_secret = getattr(settings, "INTERNAL_SERVICE_SECRET", "agrilink-internal-microservice-shared-secret-2026")
    
    citizen_ms_status = "OFFLINE"
    status_detail = ""
    sample_citizen = None

    try:
        with httpx.Client(timeout=3.0) as client:
            headers = {"X-Service-Key": service_secret}
            # Query the first active citizen in the database
            from app.database import engine
            from sqlalchemy import text
            citizen_uuid = None
            try:
                with engine.connect() as conn:
                    citizen_uuid = conn.execute(text("SELECT id FROM public.citizens WHERE status = 'ACTIVE' LIMIT 1")).scalar()
            except Exception:
                pass
            
            if citizen_uuid:
                probe_url = f"{target_url}/internal/citizens/{citizen_uuid}/status"
                resp = client.get(probe_url, headers=headers)
                if resp.status_code == 200:
                    citizen_ms_status = "CONNECTED"
                    sample_citizen = resp.json()
                else:
                    citizen_ms_status = f"HTTP_{resp.status_code}"
                    status_detail = resp.text
            else:
                # Fallback probe to openapi docs
                docs_resp = client.get("http://localhost:8001/docs")
                if docs_resp.status_code == 200:
                    citizen_ms_status = "CONNECTED"
    except Exception as e:
        status_detail = str(e)

    return {
        "status": "HEALTHY",
        "source_microservice": {
            "name": "Microservice_Vehicle- (RTO Commercial Fleet & Registry)",
            "port": 8000
        },
        "target_microservice": {
            "name": "Microservice_Citizen (Identity & Wallet Service)",
            "url": target_url,
            "port": 8001,
            "status": citizen_ms_status,
            "detail": status_detail,
            "live_citizen_verified": sample_citizen
        },
        "shared_infrastructure": {
            "database": "Supabase PostgreSQL (Project ID: mgilglfzakfqmssxadrx)",
            "shared_jwt_algorithm": settings.JWT_ALGORITHM,
            "inter_service_auth": "X-Service-Key Pre-shared Secret"
        }
    }

