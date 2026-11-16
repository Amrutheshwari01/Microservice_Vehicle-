from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.listing import RentalListing
from app.schemas.listing import (
    RentalListingCreate,
    RentalListingUpdate,
    RentalListingResponse,
)
from app.modules.m3_listing.service import ListingService
from app.api.deps import require_vehicle_owner, get_current_actor

router = APIRouter(prefix="/listings", tags=["Rental Listings (RTO-M3)"])

@router.post("", response_model=RentalListingResponse, status_code=status.HTTP_201_CREATED)
def create_rental_listing(
    listing_in: RentalListingCreate,
    request: Request,
    db: Session = Depends(get_db),
    owner: dict = Depends(require_vehicle_owner)
):
    """
    RTO-FR-06: Create rental listing with rate card, deposit and rules.
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    return ListingService.create_listing(
        db=db,
        listing_in=listing_in,
        owner_actor=owner,
        correlation_id=correlation_id
    )

@router.patch("/{listing_id}", response_model=RentalListingResponse)
def update_rental_listing(
    listing_id: str,
    listing_in: RentalListingUpdate,
    request: Request,
    db: Session = Depends(get_db),
    owner: dict = Depends(require_vehicle_owner)
):
    """
    RTO-FR-07: Listing management; blocked during an active rental.
    """
    correlation_id = getattr(request.state, "correlation_id", None)
    return ListingService.update_listing(
        db=db,
        listing_id=listing_id,
        listing_in=listing_in,
        owner_actor=owner,
        correlation_id=correlation_id
    )

@router.get("", response_model=List[RentalListingResponse])
def list_rental_listings(
    owner_citizen_id: Optional[str] = None,
    status_filter: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all rental listings with optional owner or status filters.
    """
    query = db.query(RentalListing)
    if owner_citizen_id:
        query = query.filter(RentalListing.owner_citizen_id == owner_citizen_id)
    if status_filter:
        query = query.filter(RentalListing.status == status_filter.upper())
    return query.order_by(RentalListing.created_at.desc()).all()

@router.get("/{listing_id}", response_model=RentalListingResponse)
def get_rental_listing(
    listing_id: str,
    db: Session = Depends(get_db)
):
    listing = db.query(RentalListing).filter(RentalListing.id == listing_id).first()
    if not listing:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Rental listing not found")
    return listing

