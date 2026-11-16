from typing import Dict, Set
from fastapi import HTTPException, status
from app.models.vehicle import VehicleStatus

# Enforced Lifecycle State Machine (RTO-FR-04)
VALID_TRANSITIONS: Dict[str, Set[str]] = {
    VehicleStatus.PENDING: {
        VehicleStatus.VERIFIED,
        VehicleStatus.SUSPENDED
    },
    VehicleStatus.VERIFIED: {
        VehicleStatus.AVAILABLE,
        VehicleStatus.UNDER_MAINTENANCE,
        VehicleStatus.SUSPENDED
    },
    VehicleStatus.AVAILABLE: {
        VehicleStatus.RESERVED,
        VehicleStatus.IN_TRANSIT,
        VehicleStatus.UNDER_MAINTENANCE,
        VehicleStatus.SUSPENDED,
        VehicleStatus.VERIFIED
    },
    VehicleStatus.RESERVED: {
        VehicleStatus.RENTED,
        VehicleStatus.AVAILABLE, # If booking cancelled
        VehicleStatus.SUSPENDED
    },
    VehicleStatus.RENTED: {
        VehicleStatus.AVAILABLE, # Returned in good order
        VehicleStatus.UNDER_MAINTENANCE, # Returned with damage
        VehicleStatus.SUSPENDED
    },
    VehicleStatus.IN_TRANSIT: {
        VehicleStatus.AVAILABLE, # AgriLink delivery completed
        VehicleStatus.UNDER_MAINTENANCE,
        VehicleStatus.SUSPENDED
    },
    VehicleStatus.UNDER_MAINTENANCE: {
        VehicleStatus.AVAILABLE,
        VehicleStatus.VERIFIED,
        VehicleStatus.SUSPENDED
    },
    VehicleStatus.SUSPENDED: {
        VehicleStatus.VERIFIED,
        VehicleStatus.AVAILABLE,
        VehicleStatus.UNDER_MAINTENANCE
    }
}

class VehicleStateMachine:
    @classmethod
    def validate_transition(cls, current_status: str, target_status: str):
        allowed = VALID_TRANSITIONS.get(current_status, set())
        if target_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Illegal vehicle lifecycle transition from '{current_status}' to '{target_status}'. Permitted next states: {sorted(list(allowed))}"
            )
        return True

