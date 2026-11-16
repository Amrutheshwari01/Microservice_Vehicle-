from typing import Optional
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.vehicle import Vehicle, VehicleStatus, VerificationStatus, VehicleDocument
from app.models.listing import RentalListing, ListingStatus
from app.models.booking import Booking, BookingStatus
from app.schemas.listing import RentalListingCreate, RentalListingUpdate
from app.inter_service.outbox import record_event
from app.api.deps import log_audit_trail

class ListingService:

    @classmethod
    def create_listing(
        cls,
        db: Session,
        listing_in: RentalListingCreate,
        owner_actor: dict,
        correlation_id: Optional[str] = None
    ) -> RentalListing:
        """
        RTO-FR-06: Rental listing with rate card, deposit and rules.
        """
        owner_citizen_id = owner_actor["citizen_id"]
        
        vehicle = db.query(Vehicle).filter(Vehicle.id == listing_in.vehicle_id).first()
        if not vehicle:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vehicle not found")

        # Object-level ownership check (RTO-N06)
        if vehicle.owner_citizen_id != owner_citizen_id and "ADMIN" not in owner_actor.get("personas", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Unauthorized: You can only create rental listings for vehicles you own."
            )

        # Must be Verified
        if vehicle.verification_status != VerificationStatus.VERIFIED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot list vehicle for rent. Vehicle verification status is '{vehicle.verification_status}'. Must be VERIFIED."
            )

        # Check compliance documents: RTO-FR-06 & RTO-FR-13
        now = datetime.utcnow()
        expired_docs = (
            db.query(VehicleDocument)
            .filter(VehicleDocument.vehicle_id == vehicle.id)
            .filter(VehicleDocument.expiry_date != None)
            .filter(VehicleDocument.expiry_date < now)
            .all()
        )
        if expired_docs:
            expired_names = [f"{d.document_type} (Expired: {d.expiry_date.strftime('%Y-%m-%d')})" for d in expired_docs]
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot list vehicle. Compliance documents have expired: {', '.join(expired_names)}"
            )

        # Check existing listing
        existing = db.query(RentalListing).filter(RentalListing.vehicle_id == vehicle.id).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A rental listing already exists for this vehicle. Use PATCH to update it."
            )

        listing = RentalListing(
            vehicle_id=vehicle.id,
            owner_citizen_id=owner_citizen_id,
            rate_per_hour=listing_in.rate_per_hour,
            rate_per_day=listing_in.rate_per_day,
            rate_per_km=listing_in.rate_per_km,
            security_deposit=listing_in.security_deposit,
            pickup_location=listing_in.pickup_location,
            pickup_coordinates=listing_in.pickup_coordinates,
            rental_rules=listing_in.rental_rules,
            status=ListingStatus.ACTIVE
        )
        db.add(listing)

        # Set vehicle to AVAILABLE
        vehicle.status = VehicleStatus.AVAILABLE
        vehicle.updated_at = datetime.utcnow()

        log_audit_trail(
            db=db,
            actor_id=owner_citizen_id,
            actor_role="VEHICLE_OWNER",
            action="RENTAL_LISTING_CREATED",
            entity_type="LISTING",
            entity_id=listing.id,
            details={"vehicle_id": vehicle.id, "rate_per_day": listing.rate_per_day},
            correlation_id=correlation_id
        )

        record_event(
            db=db,
            event_type="RentalListingPublished",
            aggregate_type="LISTING",
            aggregate_id=listing.id,
            payload={
                "listing_id": listing.id,
                "vehicle_id": vehicle.id,
                "owner_citizen_id": owner_citizen_id,
                "rate_per_day": listing.rate_per_day
            },
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(listing)
        return listing

    @classmethod
    def update_listing(
        cls,
        db: Session,
        listing_id: str,
        listing_in: RentalListingUpdate,
        owner_actor: dict,
        correlation_id: Optional[str] = None
    ) -> RentalListing:
        """
        RTO-FR-07: Listing management; blocked during an active rental.
        """
        listing = db.query(RentalListing).filter(RentalListing.id == listing_id).first()
        if not listing:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Listing not found")

        # Object-level authorisation check
        if listing.owner_citizen_id != owner_actor["citizen_id"] and "ADMIN" not in owner_actor.get("personas", []):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Unauthorized to edit this listing")

        # Check for active rental (RTO-FR-07)
        active_booking = (
            db.query(Booking)
            .filter(Booking.vehicle_id == listing.vehicle_id)
            .filter(Booking.status.in_([BookingStatus.CONFIRMED, BookingStatus.ACTIVE]))
            .first()
        )
        if active_booking:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Listing cannot be modified, paused or withdrawn while an active booking ({active_booking.booking_ref}) exists."
            )

        # Update fields
        if listing_in.rate_per_hour is not None:
            listing.rate_per_hour = listing_in.rate_per_hour
        if listing_in.rate_per_day is not None:
            listing.rate_per_day = listing_in.rate_per_day
        if listing_in.rate_per_km is not None:
            listing.rate_per_km = listing_in.rate_per_km
        if listing_in.security_deposit is not None:
            listing.security_deposit = listing_in.security_deposit
        if listing_in.pickup_location is not None:
            listing.pickup_location = listing_in.pickup_location
        if listing_in.pickup_coordinates is not None:
            listing.pickup_coordinates = listing_in.pickup_coordinates
        if listing_in.rental_rules is not None:
            listing.rental_rules = listing_in.rental_rules
        if listing_in.status is not None:
            listing.status = listing_in.status.upper()

        listing.updated_at = datetime.utcnow()

        log_audit_trail(
            db=db,
            actor_id=owner_actor["citizen_id"],
            actor_role="VEHICLE_OWNER",
            action="RENTAL_LISTING_UPDATED",
            entity_type="LISTING",
            entity_id=listing.id,
            details={"status": listing.status},
            correlation_id=correlation_id
        )

        db.commit()
        db.refresh(listing)
        return listing

