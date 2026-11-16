import pytest
from datetime import datetime, timedelta
from app.models.vehicle import Vehicle, VehicleStatus
from app.models.outbox import OutboxEvent
from app.schemas.vehicle import VehicleCreate
from app.schemas.listing import RentalListingCreate
from app.schemas.booking import AgriLinkVehicleRequest
from app.modules.m1_registration.service import RegistrationService
from app.modules.m3_listing.service import ListingService
from app.modules.m4_booking.agrilink_service import AgriLinkAssignmentService

def test_agrilink_vehicle_assignment(db):
    owner = {"citizen_id": "CIT-OWNER-001", "name": "Ramesh Patil", "personas": ["VEHICLE_OWNER"], "kyc_tier": "T2"}
    v = RegistrationService.register_vehicle(
        db,
        VehicleCreate(
            registration_number="KA-01-AG-5500",
            vehicle_class="LIGHT_COMMERCIAL",
            make_model="Mahindra Bolero Maxi Truck",
            capacity_kg=1250.0,
            rc_document_number="RC-KA01AG5500"
        ),
        owner
    )
    ListingService.create_listing(
        db,
        RentalListingCreate(
            vehicle_id=v.id,
            rate_per_hour=160.0,
            rate_per_day=1300.0,
            rate_per_km=14.0,
            security_deposit=2000.0,
            pickup_location="Kolar APMC"
        ),
        owner
    )

    start = datetime.utcnow() + timedelta(days=1)
    end = start + timedelta(hours=8)
    req = AgriLinkVehicleRequest(
        agrilink_job_ref="AGL-DEL-9911",
        delivery_person_citizen_id="CIT-DELIVERY-003",
        delivery_person_name="Suresh Gowda",
        delivery_person_kyc_tier="T3",
        delivery_person_licence_classes="LMV,HMV",
        vehicle_class="LIGHT_COMMERCIAL",
        min_capacity_kg=1000.0,
        start_time=start,
        end_time=end,
        idempotency_key="idemp-agl-9911"
    )

    bk = AgriLinkAssignmentService.assign_vehicle_for_job(db, req)
    assert bk.agrilink_job_ref == "AGL-DEL-9911"
    assert bk.status == "CONFIRMED"
    assert v.status == VehicleStatus.IN_TRANSIT

    # Check that Outbox recorded VehicleAssigned event for AgriLink broker
    event = db.query(OutboxEvent).filter(OutboxEvent.event_type == "VehicleAssigned").first()
    assert event is not None
    assert "AGL-DEL-9911" in event.payload

