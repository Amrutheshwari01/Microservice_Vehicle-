import pytest
from datetime import datetime, timedelta
from app.models.vehicle import Vehicle, DocumentType
from app.schemas.vehicle import VehicleCreate, DocumentCreate
from app.schemas.listing import RentalListingCreate
from app.modules.m1_registration.service import RegistrationService
from app.modules.m3_listing.service import ListingService
from app.modules.m5_compliance.service import ComplianceService
from app.modules.m5_compliance.export_service import ExportService

def test_compliance_tracking_and_auto_block(db):
    owner = {"citizen_id": "CIT-OWNER-001", "name": "Ramesh Patil", "personas": ["VEHICLE_OWNER"], "kyc_tier": "T2"}
    v = RegistrationService.register_vehicle(
        db,
        VehicleCreate(
            registration_number="KA-05-CP-3333",
            vehicle_class="LIGHT_COMMERCIAL",
            make_model="Tata Ace",
            capacity_kg=750.0,
            rc_document_number="RC-KA05CP3333"
        ),
        owner
    )

    # 1. Add valid Insurance
    doc = ComplianceService.add_document(
        db,
        v.id,
        DocumentCreate(
            document_type="INSURANCE",
            document_number="INS-KA05CP3333",
            file_reference="enc://ins_ka05cp3333.pdf",
            expiry_date=datetime.utcnow() + timedelta(days=180)
        ),
        owner
    )
    assert doc.id is not None

    # 2. Check compliance status
    status_res = ComplianceService.get_vehicle_compliance(db, v.id)
    assert status_res.vehicle_id == v.id

    # 3. Add expired PUC document to test expiry detection
    ComplianceService.add_document(
        db,
        v.id,
        DocumentCreate(
            document_type="PUC",
            document_number="PUC-EXPIRED-01",
            file_reference="enc://puc_expired.pdf",
            expiry_date=datetime.utcnow() - timedelta(days=5) # Expired 5 days ago!
        ),
        owner
    )

    # 4. Run compliance sweep -> detects non-compliance
    sweep_summary = ComplianceService.run_compliance_sweep(db)
    assert sweep_summary.non_compliant_vehicles >= 1
    assert sweep_summary.expired_docs_count >= 1

def test_admin_records_and_csv_export(db):
    owner = {"citizen_id": "CIT-OWNER-001", "name": "Ramesh Patil", "personas": ["VEHICLE_OWNER"], "kyc_tier": "T2"}
    RegistrationService.register_vehicle(
        db,
        VehicleCreate(
            registration_number="KA-01-EX-8888",
            vehicle_class="LIGHT_COMMERCIAL",
            make_model="Tata Ace",
            capacity_kg=750.0,
            rc_document_number="RC-KA01EX8888"
        ),
        owner
    )

    # Fetch audit records
    records = ExportService.get_full_audit_records(db, limit=10)
    assert len(records) >= 1

    # Export records to CSV
    csv_str = ExportService.export_records_csv(db)
    assert "Event ID" in csv_str
    assert "VEHICLE" in csv_str

    # Export vehicle registry table to CSV
    veh_csv = ExportService.export_vehicle_registry_csv(db)
    assert "KA-01-EX-8888" in veh_csv

