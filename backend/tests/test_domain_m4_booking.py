import pytest
from datetime import datetime, timedelta
from fastapi import HTTPException
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.booking import BookingStatus
from app.schemas.vehicle import VehicleCreate
from app.schemas.listing import RentalListingCreate
from app.schemas.booking import BookingCreateRequest, HandoverCreateRequest, ReturnCreateRequest, CancellationRequest
from app.modules.m1_registration.service import RegistrationService
from app.modules.m3_listing.service import ListingService
from app.modules.m4_booking.service import BookingService

def setup_vehicle_and_listing(db):
    owner = {"citizen_id": "CIT-OWNER-001", "name": "Ramesh Patil", "personas": ["VEHICLE_OWNER"], "kyc_tier": "T2"}
    v = RegistrationService.register_vehicle(
        db,
        VehicleCreate(
            registration_number="KA-05-BK-1111",
            vehicle_class="LIGHT_COMMERCIAL",
            make_model="Tata Ace Gold",
            capacity_kg=850.0,
            rc_document_number="RC-KA05BK1111"
        ),
        owner
    )
    listing = ListingService.create_listing(
        db,
        RentalListingCreate(
            vehicle_id=v.id,
            rate_per_hour=150.0,
            rate_per_day=1200.0,
            rate_per_km=12.0,
            security_deposit=2000.0,
            pickup_location="Hebbal APMC"
        ),
        owner
    )
    return v, listing

def test_booking_eligibility_kyc_and_licence(db):
    v, listing = setup_vehicle_and_listing(db)

    # 1. Renter with Tier T0 (fails RTO-FR-08)
    low_kyc_renter = {
        "citizen_id": "CIT-LOW-001",
        "name": "Low KYC User",
        "kyc_tier": "T0",
        "driving_licence_classes": ["LMV"],
        "personas": ["RENTER"]
    }
    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=5)

    req = BookingCreateRequest(vehicle_id=v.id, start_time=start, end_time=end, idempotency_key="idemp-low-kyc")
    with pytest.raises(HTTPException) as exc_info:
        BookingService.create_booking(db, req, low_kyc_renter)
    assert exc_info.value.status_code == 403
    assert "below the required Tier 1" in exc_info.value.detail

    # 2. Renter with no matching licence class (fails RTO-FR-08)
    no_licence_renter = {
        "citizen_id": "CIT-NOLIC-001",
        "name": "No Licence User",
        "kyc_tier": "T2",
        "driving_licence_classes": ["MCWG"], # Only two-wheeler licence
        "personas": ["RENTER"]
    }
    with pytest.raises(HTTPException) as exc_lic:
        BookingService.create_booking(db, req, no_licence_renter)
    assert exc_lic.value.status_code == 403
    assert "Ineligible licence" in exc_lic.value.detail

def test_booking_saga_and_overlap_prevention(db):
    v, listing = setup_vehicle_and_listing(db)
    valid_renter = {
        "citizen_id": "CIT-RENTER-002",
        "name": "Priya Sharma",
        "kyc_tier": "T2",
        "driving_licence_classes": ["LMV", "HMV"],
        "personas": ["RENTER"]
    }
    start = datetime.utcnow() + timedelta(days=2)
    end = start + timedelta(hours=6)

    # 1. Create valid booking -> Saga confirms with wallet hold
    req1 = BookingCreateRequest(vehicle_id=v.id, start_time=start, end_time=end, idempotency_key="idemp-saga-001")
    bk1 = BookingService.create_booking(db, req1, valid_renter)
    assert bk1.status == BookingStatus.CONFIRMED
    assert bk1.wallet_hold_status == "FUNDS_HELD"
    assert v.status == VehicleStatus.RESERVED

    # 2. RTO-N01: Overlap Prevention -> Attempt booking overlapping with bk1
    overlap_start = start + timedelta(hours=2)
    overlap_end = end + timedelta(hours=2)
    req_overlap = BookingCreateRequest(vehicle_id=v.id, start_time=overlap_start, end_time=overlap_end, idempotency_key="idemp-overlap-002")
    with pytest.raises(HTTPException) as exc_overlap:
        BookingService.create_booking(db, req_overlap, valid_renter)
    assert exc_overlap.value.status_code == 409
    assert "Overlap conflict" in exc_overlap.value.detail

def test_handover_return_and_settlement(db):
    v, listing = setup_vehicle_and_listing(db)
    renter = {
        "citizen_id": "CIT-RENTER-002",
        "name": "Priya Sharma",
        "kyc_tier": "T2",
        "driving_licence_classes": ["LMV"],
        "personas": ["RENTER"]
    }
    start = datetime.utcnow() + timedelta(days=3)
    end = start + timedelta(hours=8)
    bk = BookingService.create_booking(
        db,
        BookingCreateRequest(vehicle_id=v.id, start_time=start, end_time=end, idempotency_key="idemp-trip-001"),
        renter
    )

    # 1. Handover (RTO-FR-10)
    bk_active = BookingService.record_handover(
        db,
        bk.id,
        HandoverCreateRequest(odometer_reading=45100.0, fuel_level_percent=95.0, condition_notes="Good"),
        renter
    )
    assert bk_active.status == BookingStatus.ACTIVE
    assert v.status == VehicleStatus.RENTED

    # 2. Return & Settlement (RTO-FR-10)
    bk_completed = BookingService.record_return(
        db,
        bk.id,
        ReturnCreateRequest(odometer_reading=45240.0, fuel_level_percent=92.0, condition_notes="All clean", damage_detected=False),
        renter
    )
    assert bk_completed.status == BookingStatus.COMPLETED
    assert v.status == VehicleStatus.AVAILABLE

def test_booking_cancellation_policy(db):
    v, listing = setup_vehicle_and_listing(db)
    renter = {
        "citizen_id": "CIT-RENTER-002",
        "name": "Priya Sharma",
        "kyc_tier": "T2",
        "driving_licence_classes": ["LMV"],
        "personas": ["RENTER"]
    }
    start = datetime.utcnow() + timedelta(days=4)
    end = start + timedelta(hours=10)
    bk = BookingService.create_booking(
        db,
        BookingCreateRequest(vehicle_id=v.id, start_time=start, end_time=end, idempotency_key="idemp-cancel-001"),
        renter
    )

    # Cancel (>24 hours -> 0 fee, 100% refund)
    bk_cancelled = BookingService.cancel_booking(
        db,
        bk.id,
        CancellationRequest(reason="Cooperative postponed loading"),
        renter
    )
    assert bk_cancelled.status == BookingStatus.CANCELLED
    assert bk_cancelled.cancellation_fee == 0.0
    assert bk_cancelled.refund_amount == bk_cancelled.total_hold_amount
    assert v.status == VehicleStatus.AVAILABLE

