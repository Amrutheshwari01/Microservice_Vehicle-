from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.vehicle import Vehicle, VehicleDocument, VehicleStatus, DocumentType
from app.models.listing import RentalListing, ListingStatus
from app.schemas.vehicle import DocumentCreate
from app.schemas.compliance import ComplianceStatusResponse, ExpiryCheckSummary
from app.inter_service.outbox import record_event
from app.api.deps import log_audit_trail

REQUIRED_COMPLIANCE_TYPES = [
    DocumentType.RC,
    DocumentType.INSURANCE,
    DocumentType.FITNESS,
    DocumentType.PUC
]

class ComplianceService:

    @classmethod
    def add_document(
        cls,
        db: Session,
        vehicle_id: str,
        doc_in: DocumentCreate,
        actor: dict,
        correlation_id: Optional[str] = None
    ) -> VehicleDocument:
        """
        RTO-FR-13: Upload compliance document (Insurance, Fitness, Permit, PUC).
        """
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        # Check authorization: owner or admin
        if vehicle.owner_citizen_id != actor["citizen_id"] and "ADMIN" not in actor.get("personas", []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to upload documents for this vehicle")

        doc_type = doc_in.document_type.upper()
        doc = VehicleDocument(
            vehicle_id=vehicle.id,
            document_type=doc_type,
            document_number=doc_in.document_number,
            file_reference=doc_in.file_reference,
            issue_date=doc_in.issue_date or (datetime.utcnow() - timedelta(days=1)),
            expiry_date=doc_in.expiry_date,
            is_valid=True
        )
        db.add(doc)

        log_audit_trail(
            db=db,
            actor_id=actor["citizen_id"],
            actor_role="VEHICLE_OWNER",
            action="COMPLIANCE_DOCUMENT_UPLOADED",
            entity_type="DOCUMENT",
            entity_id=doc.id,
            details={"vehicle_id": vehicle.id, "doc_type": doc_type, "expiry": doc_in.expiry_date.isoformat()},
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(doc)
        return doc

    @classmethod
    def get_vehicle_compliance(cls, db: Session, vehicle_id: str) -> ComplianceStatusResponse:
        """
        RTO-FR-13: Compliance tracking, expiry alerts, blocking on expiry.
        """
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        docs = db.query(VehicleDocument).filter(VehicleDocument.vehicle_id == vehicle_id).all()
        now = datetime.utcnow()
        warning_window = now + timedelta(days=30)

        expired_docs = []
        expiring_soon_docs = []
        valid_docs = []

        for d in docs:
            if d.expiry_date and d.expiry_date < now:
                expired_docs.append(d)
            elif d.expiry_date and d.expiry_date <= warning_window:
                expiring_soon_docs.append(d)
            else:
                valid_docs.append(d)

        # Missing any required documents?
        present_types = {d.document_type for d in docs}
        missing_required = [t for t in REQUIRED_COMPLIANCE_TYPES if t not in present_types]

        is_compliant = (len(expired_docs) == 0 and len(missing_required) == 0)
        blocking_reason = None
        
        if len(expired_docs) > 0:
            blocking_reason = f"Expired documents: {', '.join([d.document_type for d in expired_docs])}"
        elif len(missing_required) > 0:
            blocking_reason = f"Missing mandatory compliance documents: {', '.join(missing_required)}"

        can_operate = is_compliant and (vehicle.verification_status == "VERIFIED")

        return ComplianceStatusResponse(
            vehicle_id=vehicle.id,
            registration_number=vehicle.registration_number,
            is_compliant=is_compliant,
            status_summary="COMPLIANT" if is_compliant else "NON_COMPLIANT",
            expired_documents=[d for d in expired_docs],
            expiring_soon_documents=[d for d in expiring_soon_docs],
            valid_documents=[d for d in valid_docs],
            can_list=can_operate,
            can_book=can_operate,
            blocking_reason=blocking_reason
        )

    @classmethod
    def run_compliance_sweep(cls, db: Session) -> ExpiryCheckSummary:
        """
        RTO-FR-13: Scheduled/on-demand expiry checker.
        Alerts before expiry and blocks listing/booking on expiry.
        """
        now = datetime.utcnow()
        vehicles = db.query(Vehicle).all()
        
        total = len(vehicles)
        compliant = 0
        non_compliant = 0
        expired_count = 0
        expiring_soon_count = 0
        actions = []

        for v in vehicles:
            status_res = cls.get_vehicle_compliance(db, v.id)
            if not status_res.is_compliant:
                non_compliant += 1
                expired_count += len(status_res.expired_documents)

                # Auto-block: Pause rental listing if active
                listing = db.query(RentalListing).filter(RentalListing.vehicle_id == v.id).first()
                if listing and listing.status == ListingStatus.ACTIVE:
                    listing.status = ListingStatus.PAUSED
                    act_msg = f"Auto-paused listing for vehicle {v.registration_number} due to: {status_res.blocking_reason}"
                    actions.append(act_msg)
                    
                    record_event(
                        db=db,
                        event_type="ComplianceBlockingTriggered",
                        aggregate_type="VEHICLE",
                        aggregate_id=v.id,
                        payload={"vehicle_id": v.id, "reason": status_res.blocking_reason}
                    )
            else:
                compliant += 1

            expiring_soon_count += len(status_res.expiring_soon_documents)

        db.commit()
        return ExpiryCheckSummary(
            total_vehicles_checked=total,
            compliant_vehicles=compliant,
            non_compliant_vehicles=non_compliant,
            expired_docs_count=expired_count,
            expiring_soon_count=expiring_soon_count,
            actions_taken=actions
        )

