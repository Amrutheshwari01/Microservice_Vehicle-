from typing import List, Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.modules.m5_compliance.export_service import ExportService
from app.schemas.inter_service import AuditEventResponse
from app.api.deps import require_admin

router = APIRouter(prefix="/records", tags=["Records & Audit Exports (RTO-M5)"])

@router.get("", response_model=List[AuditEventResponse])
def get_audit_records(
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """
    RTO-FR-14: Authorised read APIs for audit, registration, rental, and compliance history.
    """
    return ExportService.get_full_audit_records(db=db, limit=limit)

@router.get("/export")
def export_records(
    format: str = Query("csv", description="csv or json"),
    entity_type: str = Query("ALL", description="ALL, VEHICLE, LISTING, BOOKING, DOCUMENT"),
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """
    RTO-FR-14: Export history records in CSV or JSON format.
    """
    if format.lower() == "csv":
        csv_data = ExportService.export_records_csv(db=db, entity_type=entity_type)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=rto_records_export_{entity_type.lower()}.csv"}
        )
    else:
        records = ExportService.get_full_audit_records(db=db, limit=1000)
        return records

@router.get("/export/vehicles")
def export_vehicles_csv(
    db: Session = Depends(get_db),
    admin: dict = Depends(require_admin)
):
    """
    RTO-FR-14: Export official vehicle registry to CSV.
    """
    csv_data = ExportService.export_vehicle_registry_csv(db=db)
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=rto_vehicle_registry.csv"}
    )

