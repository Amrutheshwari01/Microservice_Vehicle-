from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.vehicle import DocumentCreate, DocumentResponse
from app.schemas.compliance import ComplianceStatusResponse, ExpiryCheckSummary
from app.modules.m5_compliance.service import ComplianceService
from app.api.deps import get_current_actor, require_admin

router = APIRouter(tags=["Compliance Tracking & Expiry (RTO-M5)"])

@router.post("/vehicles/{vehicle_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def upload_compliance_document(
    vehicle_id: str,
    doc_in: DocumentCreate,
    request: Request,
    db: Session = Depends(get_db),
    actor: dict = Depends(get_current_actor)
):
    """
    RTO-FR-13: Upload compliance documents (Insurance, Fitness, Permit, PUC).
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    return ComplianceService.add_document(
        db=db,
        vehicle_id=vehicle_id,
        doc_in=doc_in,
        actor=actor,
        correlation_id=correlation_id
    )

@router.get("/vehicles/{vehicle_id}/compliance", response_model=ComplianceStatusResponse)
def get_vehicle_compliance(
    vehicle_id: str,
    db: Session = Depends(get_db)
):
    """
    RTO-FR-13: Read compliance documents and validity status.
    """
    return ComplianceService.get_vehicle_compliance(db=db, vehicle_id=vehicle_id)

@router.post("/compliance/sweep", response_model=ExpiryCheckSummary)
def run_compliance_sweep(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """
    RTO-FR-13: Scheduled/on-demand compliance sweep.
    Alerts before expiry and auto-blocks rental listing/booking for expired vehicles.
    """
    return ComplianceService.run_compliance_sweep(db=db)

