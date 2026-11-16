import pytest
from app.models.vehicle import Vehicle, VehicleStatus, VerificationStatus, VehicleClass
from app.schemas.vehicle import VehicleCreate, VerificationReviewRequest
from app.modules.m1_registration.service import RegistrationService

def test_registration_service_success(db):
    owner = {
        "citizen_id": "CIT-OWNER-001",
        "name": "Ramesh Patil",
        "personas": ["VEHICLE_OWNER"],
        "kyc_tier": "T2"
    }
    v_in = VehicleCreate(
        registration_number="KA-05-AB-1234",
        vehicle_class="LIGHT_COMMERCIAL",
        make_model="Tata Ace Gold",
        capacity_kg=750.0,
        seating_capacity=2,
        fuel_type="DIESEL",
        rc_document_number="RC-KA05AB1234"
    )
    v = RegistrationService.register_vehicle(db, v_in, owner)
    assert v.id is not None
    assert v.registration_number == "KA-05-AB-1234"
    assert v.owner_citizen_id == "CIT-OWNER-001"
    assert v.owner_name == "Ramesh Patil"
    assert v.verification_status == VerificationStatus.VERIFIED
    assert v.status == VehicleStatus.VERIFIED

def test_admin_review_fallback(db):
    owner = {
        "citizen_id": "CIT-OWNER-001",
        "name": "Ramesh Patil",
        "personas": ["VEHICLE_OWNER"],
        "kyc_tier": "T2"
    }
    admin = {
        "citizen_id": "CIT-ADMIN-001",
        "name": "Admin Official",
        "personas": ["ADMIN"]
    }
    v_in = VehicleCreate(
        registration_number="KA-01-RETRY-9999",
        vehicle_class="TRACTOR",
        make_model="Mahindra 575 DI",
        capacity_kg=2000.0,
        rc_document_number="RC-RETRY-9999"
    )
    v = RegistrationService.register_vehicle(db, v_in, owner)
    assert v.verification_status == "REQUIRES_ADMIN_REVIEW"

    # Admin reviews
    review_in = VerificationReviewRequest(
        decision="VERIFIED",
        reason="Physically checked RTO serial",
        admin_notes="Approved"
    )
    v_rev = RegistrationService.review_verification(db, v.id, review_in, admin)
    assert v_rev.verification_status == VerificationStatus.VERIFIED
    assert v_rev.status == VehicleStatus.VERIFIED

