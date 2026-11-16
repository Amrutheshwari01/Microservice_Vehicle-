from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.booking import AgriLinkVehicleRequest, BookingResponse
from app.modules.m4_booking.agrilink_service import AgriLinkAssignmentService

router = APIRouter(prefix="/vehicle-requests", tags=["AgriLink Delivery Integration (RTO-FR-12)"])

@router.post("", response_model=BookingResponse, status_code=status.HTTP_201_CREATED)
def assign_agrilink_delivery_vehicle(
    req: AgriLinkVehicleRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    RTO-FR-12: AgriLink delivery vehicle assignment.
    Called by AgriLink system (AGL-M5) on behalf of delivery persons.
    Allocates vehicle, reserves funds on delivery wallet, moves vehicle to IN_TRANSIT,
    and publishes VehicleAssigned outbox event.
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    return AgriLinkAssignmentService.assign_vehicle_for_job(
        db=db,
        req=req,
        correlation_id=correlation_id
    )

