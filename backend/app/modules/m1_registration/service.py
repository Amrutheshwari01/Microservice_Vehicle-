import uuid
from datetime import datetime, timedelta
from typing import Tuple, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.vehicle import (
    Vehicle,
    VehicleDocument,
    VerificationRequest,
    VehicleStatus,
    VerificationStatus,
    DocumentType
)
from app.schemas.vehicle import VehicleCreate, VerificationReviewRequest
from app.inter_service.mock_external_services import RegistryVerificationAdapter
from app.utils.crypto import store_encrypted_document
from app.inter_service.outbox import record_event
from app.api.deps import log_audit_trail

class RegistrationService:

    @classmethod
    def register_vehicle(
        cls,
        db: Session,
        vehicle_in: VehicleCreate,
        owner_actor: dict,
        correlation_id: Optional[str] = None
    ) -> Vehicle:
        """
        RTO-FR-01: Vehicle registration with RC document
        RTO-FR-03: Ownership validation against KYC identity
        """
        owner_citizen_id = owner_actor["citizen_id"]
        owner_name = owner_actor["name"]

        # Check for existing registration number
        clean_reg = vehicle_in.registration_number.upper().strip()
        existing = db.query(Vehicle).filter(Vehicle.registration_number == clean_reg).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Vehicle with registration number '{clean_reg}' is already registered."
            )

        # Store encrypted RC document (RTO-N06)
        file_bytes = (vehicle_in.rc_file_data or f"MOCK_RC_BINARY_DATA_{clean_reg}").encode()
        encrypted_ref = store_encrypted_document(file_bytes, f"rc_{clean_reg}.pdf")

        # Create vehicle in PENDING status (RTO-FR-01)
        vehicle = Vehicle(
            registration_number=clean_reg,
            vehicle_class=vehicle_in.vehicle_class,
            make_model=vehicle_in.make_model,
            capacity_kg=vehicle_in.capacity_kg,
            seating_capacity=vehicle_in.seating_capacity,
            fuel_type=vehicle_in.fuel_type,
            owner_citizen_id=owner_citizen_id, # Plain citizen_id value (RTO-FR-03)
            owner_name=owner_name,
            status=VehicleStatus.PENDING,
            verification_status=VerificationStatus.PENDING
        )
        db.add(vehicle)
        db.flush()

        # Add RC document record
        expiry_date = vehicle_in.rc_expiry_date or (datetime.utcnow() + timedelta(days=365 * 5))
        rc_doc = VehicleDocument(
            vehicle_id=vehicle.id,
            document_type=DocumentType.RC,
            document_number=vehicle_in.rc_document_number,
            file_reference=encrypted_ref,
            issue_date=datetime.utcnow() - timedelta(days=30),
            expiry_date=expiry_date,
            is_valid=True
        )
        db.add(rc_doc)

        # Trigger RTO-FR-02 RC Verification via Adapter
        v_status, v_reason, details = RegistryVerificationAdapter.verify_rc(clean_reg, owner_name)
        
        verif_req = VerificationRequest(
            vehicle_id=vehicle.id,
            status=v_status,
            retry_count=0 if v_status == VerificationStatus.VERIFIED else 1,
            next_retry_at=(datetime.utcnow() + timedelta(hours=1)) if v_status == "REQUIRES_ADMIN_REVIEW" else None,
            adapter_response=str(details)
        )
        db.add(verif_req)

        # Update vehicle verification status
        vehicle.verification_status = v_status
        vehicle.verification_reason = v_reason

        if v_status == VerificationStatus.VERIFIED:
            vehicle.status = VehicleStatus.VERIFIED
        elif v_status == VerificationStatus.REJECTED:
            vehicle.status = VehicleStatus.SUSPENDED

        # Record audit trail (RTO-FR-14)
        log_audit_trail(
            db=db,
            actor_id=owner_citizen_id,
            actor_role="VEHICLE_OWNER",
            action="VEHICLE_REGISTERED",
            entity_type="VEHICLE",
            entity_id=vehicle.id,
            details={"reg_no": clean_reg, "verif_status": v_status},
            correlation_id=correlation_id
        )

        # Outbox event
        record_event(
            db=db,
            event_type="VehicleRegistered",
            aggregate_type="VEHICLE",
            aggregate_id=vehicle.id,
            payload={
                "vehicle_id": vehicle.id,
                "registration_number": clean_reg,
                "owner_citizen_id": owner_citizen_id,
                "verification_status": v_status
            },
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(vehicle)
        return vehicle

    @classmethod
    def review_verification(
        cls,
        db: Session,
        vehicle_id: str,
        review_in: VerificationReviewRequest,
        admin_actor: dict,
        correlation_id: Optional[str] = None
    ) -> Vehicle:
        """
        RTO-FR-02: Administrator verification review fallback.
        """
        vehicle = db.query(Vehicle).filter(Vehicle.id == vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        decision = review_in.decision.upper()
        if decision not in [VerificationStatus.VERIFIED, VerificationStatus.REJECTED]:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Decision must be VERIFIED or REJECTED")

        vehicle.verification_status = decision
        vehicle.verification_reason = review_in.reason or f"Administrative review by {admin_actor['name']}"
        vehicle.status = VehicleStatus.VERIFIED if decision == VerificationStatus.VERIFIED else VehicleStatus.SUSPENDED

        # Update verification request
        verif_req = db.query(VerificationRequest).filter(VerificationRequest.vehicle_id == vehicle_id).first()
        if verif_req:
            verif_req.status = decision
            verif_req.admin_notes = review_in.admin_notes

        log_audit_trail(
            db=db,
            actor_id=admin_actor["citizen_id"],
            actor_role="ADMIN",
            action="ADMIN_VERIFICATION_REVIEW",
            entity_type="VEHICLE",
            entity_id=vehicle.id,
            details={"decision": decision, "reason": review_in.reason},
            correlation_id=correlation_id
        )

        record_event(
            db=db,
            event_type="VehicleVerificationReviewed",
            aggregate_type="VEHICLE",
            aggregate_id=vehicle.id,
            payload={"vehicle_id": vehicle.id, "decision": decision},
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(vehicle)
        return vehicle

