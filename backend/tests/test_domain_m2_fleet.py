import pytest
from fastapi import HTTPException
from app.models.vehicle import Vehicle, VehicleStatus, VehicleClass
from app.schemas.vehicle import VehicleCreate
from app.modules.m1_registration.service import RegistrationService
from app.modules.m2_fleet.service import FleetService

def test_fleet_lifecycle_state_machine(db):
    owner = {"citizen_id": "CIT-OWNER-001", "name": "Ramesh Patil", "personas": ["VEHICLE_OWNER"], "kyc_tier": "T2"}
    admin = {"citizen_id": "CIT-ADMIN-001", "name": "Admin Officer", "personas": ["ADMIN"]}

    # Register verified vehicle
    v = RegistrationService.register_vehicle(
        db,
        VehicleCreate(
            registration_number="KA-04-MK-1234",
            vehicle_class="LIGHT_COMMERCIAL",
            make_model="Tata Ace",
            capacity_kg=750.0,
            rc_document_number="RC-KA04MK1234"
        ),
        owner
    )
    assert v.status == VehicleStatus.VERIFIED

    # Transition VERIFIED -> UNDER_MAINTENANCE (Permitted)
    v_maint = FleetService.transition_vehicle_status(db, v.id, VehicleStatus.UNDER_MAINTENANCE, owner)
    assert v_maint.status == VehicleStatus.UNDER_MAINTENANCE

    # Illegal transition: UNDER_MAINTENANCE -> RENTED (must raise 400 HTTPException)
    with pytest.raises(HTTPException) as exc_info:
        FleetService.transition_vehicle_status(db, v.id, VehicleStatus.RENTED, owner)
    assert exc_info.value.status_code == 400
    assert "Illegal vehicle lifecycle transition" in exc_info.value.detail

    # Admin suspends vehicle (Permitted)
    v_susp = FleetService.transition_vehicle_status(db, v.id, VehicleStatus.SUSPENDED, admin, reason="Routine check")
    assert v_susp.status == VehicleStatus.SUSPENDED

def test_fleet_search_and_availability(db):
    owner = {"citizen_id": "CIT-OWNER-001", "name": "Ramesh Patil", "personas": ["VEHICLE_OWNER"], "kyc_tier": "T2"}
    v = RegistrationService.register_vehicle(
        db,
        VehicleCreate(
            registration_number="KA-04-MK-7777",
            vehicle_class="TRACTOR",
            make_model="Mahindra 575 DI",
            capacity_kg=2500.0,
            rc_document_number="RC-KA04MK7777"
        ),
        owner
    )
    # Check availability calendar
    cal = FleetService.get_vehicle_availability_calendar(db, v.id)
    assert cal["vehicle_id"] == v.id
    assert cal["busy_slots"] == []

