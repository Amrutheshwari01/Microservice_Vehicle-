import pytest
from fastapi import HTTPException
from app.models.vehicle import Vehicle, VehicleStatus
from app.schemas.vehicle import VehicleCreate
from app.schemas.listing import RentalListingCreate, RentalListingUpdate
from app.modules.m1_registration.service import RegistrationService
from app.modules.m3_listing.service import ListingService

def test_listing_creation_and_update(db):
    owner = {"citizen_id": "CIT-OWNER-001", "name": "Ramesh Patil", "personas": ["VEHICLE_OWNER"], "kyc_tier": "T2"}
    v = RegistrationService.register_vehicle(
        db,
        VehicleCreate(
            registration_number="KA-01-LS-9988",
            vehicle_class="LIGHT_COMMERCIAL",
            make_model="Mahindra Supro",
            capacity_kg=800.0,
            rc_document_number="RC-KA01LS9988"
        ),
        owner
    )

    listing_in = RentalListingCreate(
        vehicle_id=v.id,
        rate_per_hour=140.0,
        rate_per_day=1100.0,
        rate_per_km=11.0,
        security_deposit=1800.0,
        pickup_location="Hebbal Mandi",
        rental_rules="No hazardous transport"
    )
    listing = ListingService.create_listing(db, listing_in, owner)
    assert listing.id is not None
    assert listing.status == "ACTIVE"
    assert v.status == VehicleStatus.AVAILABLE

    # Update listing
    update_in = RentalListingUpdate(rate_per_day=1200.0)
    updated = ListingService.update_listing(db, listing.id, update_in, owner)
    assert updated.rate_per_day == 1200.0

def test_listing_unauthorized_owner_rejected(db):
    owner1 = {"citizen_id": "CIT-OWNER-001", "name": "Ramesh Patil", "personas": ["VEHICLE_OWNER"], "kyc_tier": "T2"}
    other_owner = {"citizen_id": "CIT-OWNER-OTHER", "name": "Fake Owner", "personas": ["VEHICLE_OWNER"], "kyc_tier": "T2"}
    v = RegistrationService.register_vehicle(
        db,
        VehicleCreate(
            registration_number="KA-01-LS-1122",
            vehicle_class="LIGHT_COMMERCIAL",
            make_model="Tata Ace",
            capacity_kg=800.0,
            rc_document_number="RC-KA01LS1122"
        ),
        owner1
    )

    listing_in = RentalListingCreate(
        vehicle_id=v.id,
        rate_per_hour=140.0,
        rate_per_day=1100.0,
        rate_per_km=11.0,
        security_deposit=1800.0,
        pickup_location="Hebbal Mandi"
    )
    # Another person cannot list a vehicle they do not own
    with pytest.raises(HTTPException) as exc_info:
        ListingService.create_listing(db, listing_in, other_owner)
    assert exc_info.value.status_code == 403

