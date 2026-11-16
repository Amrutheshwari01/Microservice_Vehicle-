import os
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.api.middleware import CorrelationIdMiddleware
from app.api.v1 import (
    auth,
    vehicles,
    listings,
    bookings,
    compliance,
    records,
    vehicle_requests,
    inter_service_events,
)
from app.models.user import User
from app.models.vehicle import Vehicle, VehicleDocument, VehicleStatus, VerificationStatus, VehicleClass, DocumentType
from app.models.listing import RentalListing, ListingStatus
from app.inter_service.wallet_client import WalletClient
from app.api.v1.auth import hash_password

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("rto_microservice")

app = FastAPI(
    title="AgriLink RTO & Vehicle Registry Microservice",
    description="Microservice 3 of the AgriLink ecosystem. Handles vehicle registration, verification, fleet availability, rental listing, booking saga with wallet holds, AgriLink delivery vehicle assignment, and compliance tracking.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# S04: Correlation ID middleware
app.add_middleware(CorrelationIdMiddleware)

# API v1 Routers
app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
app.include_router(vehicles.router, prefix=settings.API_V1_PREFIX)
app.include_router(listings.router, prefix=settings.API_V1_PREFIX)
app.include_router(bookings.router, prefix=settings.API_V1_PREFIX)
app.include_router(vehicle_requests.router, prefix=settings.API_V1_PREFIX)
app.include_router(compliance.router, prefix=settings.API_V1_PREFIX)
app.include_router(records.router, prefix=settings.API_V1_PREFIX)
app.include_router(inter_service_events.router, prefix=settings.API_V1_PREFIX)

@app.on_event("startup")
def on_startup():
    # Create tables
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
    seed_initial_data()

def seed_initial_data():
    db = SessionLocal()
    try:
        # Seed default users if empty
        if db.query(User).count() == 0:
            logger.info("Seeding default demo users...")
            demo_users = [
                User(
                    id="CIT-OWNER-001",
                    name="Ramesh Patil",
                    email="ramesh@agrilink.in",
                    phone="+91 98765 43210",
                    password_hash=hash_password("ramesh123"),
                    role="VEHICLE_OWNER",
                    kyc_tier="T2",
                    driving_licence_classes="LMV,HMV,TRACTOR"
                ),
                User(
                    id="CIT-RENTER-002",
                    name="Priya Sharma",
                    email="priya@agrilink.in",
                    phone="+91 98450 11223",
                    password_hash=hash_password("priya123"),
                    role="RENTER",
                    kyc_tier="T2",
                    driving_licence_classes="LMV,MCWG"
                ),
                User(
                    id="CIT-DELIVERY-003",
                    name="Suresh Gowda",
                    email="suresh@agrilink.in",
                    phone="+91 99001 55442",
                    password_hash=hash_password("suresh123"),
                    role="DELIVERY_PERSON",
                    kyc_tier="T3",
                    driving_licence_classes="LMV,HMV"
                ),
                User(
                    id="CIT-ADMIN-001",
                    name="Officer V. K. Rao",
                    email="admin@agrilink.in",
                    phone="+91 80222 33445",
                    password_hash=hash_password("admin123"),
                    role="ADMIN",
                    kyc_tier="T3",
                    driving_licence_classes="LMV"
                )
            ]
            db.add_all(demo_users)
            db.commit()

        count = db.query(Vehicle).count()
        if count == 0:
            logger.info("Seeding realistic sample vehicles and listings...")
            now = datetime.utcnow()

            # 1. Tata Ace Gold (Light Commercial) - Ramesh Patil
            v1 = Vehicle(
                registration_number="KA-01-AB-1234",
                vehicle_class=VehicleClass.LIGHT_COMMERCIAL,
                make_model="Tata Ace Gold Plus (0.75 Ton)",
                capacity_kg=850.0,
                seating_capacity=2,
                fuel_type="DIESEL",
                owner_citizen_id="CIT-OWNER-001",
                owner_name="Ramesh Patil",
                status=VehicleStatus.AVAILABLE,
                verification_status=VerificationStatus.VERIFIED,
                verification_reason="Physical & Vahan registry verified"
            )
            db.add(v1)
            db.flush()

            # Documents for v1
            db.add_all([
                VehicleDocument(vehicle_id=v1.id, document_type=DocumentType.RC, document_number="RC-KA01AB1234", file_reference="enc://rc_ka01ab1234.pdf", issue_date=now - timedelta(days=100), expiry_date=now + timedelta(days=1200)),
                VehicleDocument(vehicle_id=v1.id, document_type=DocumentType.INSURANCE, document_number="INS-992144", file_reference="enc://ins_ka01ab1234.pdf", issue_date=now - timedelta(days=50), expiry_date=now + timedelta(days=315)),
                VehicleDocument(vehicle_id=v1.id, document_type=DocumentType.FITNESS, document_number="FIT-881200", file_reference="enc://fit_ka01ab1234.pdf", issue_date=now - timedelta(days=50), expiry_date=now + timedelta(days=315)),
                VehicleDocument(vehicle_id=v1.id, document_type=DocumentType.PUC, document_number="PUC-774112", file_reference="enc://puc_ka01ab1234.pdf", issue_date=now - timedelta(days=30), expiry_date=now + timedelta(days=150)),
            ])

            # Listing for v1
            l1 = RentalListing(
                vehicle_id=v1.id,
                owner_citizen_id="CIT-OWNER-001",
                rate_per_hour=150.0,
                rate_per_day=1200.0,
                rate_per_km=12.0,
                security_deposit=2000.0,
                pickup_location="Hebbal APMC Yard, Bengaluru",
                pickup_coordinates="13.0358,77.5970",
                rental_rules="Commercial LMV licence required. Return with clean deck and same fuel level.",
                status=ListingStatus.ACTIVE
            )
            db.add(l1)

            # 2. Mahindra 575 DI (Tractor) - Ramesh Patil
            v2 = Vehicle(
                registration_number="KA-04-MK-9988",
                vehicle_class=VehicleClass.TRACTOR,
                make_model="Mahindra 575 DI Sarpanch (45 HP)",
                capacity_kg=2500.0,
                seating_capacity=1,
                fuel_type="DIESEL",
                owner_citizen_id="CIT-OWNER-001",
                owner_name="Ramesh Patil",
                status=VehicleStatus.AVAILABLE,
                verification_status=VerificationStatus.VERIFIED,
                verification_reason="Agricultural registry verified"
            )
            db.add(v2)
            db.flush()

            db.add_all([
                VehicleDocument(vehicle_id=v2.id, document_type=DocumentType.RC, document_number="RC-KA04MK9988", file_reference="enc://rc_ka04mk9988.pdf", issue_date=now - timedelta(days=120), expiry_date=now + timedelta(days=1500)),
                VehicleDocument(vehicle_id=v2.id, document_type=DocumentType.INSURANCE, document_number="INS-881122", file_reference="enc://ins_ka04mk9988.pdf", issue_date=now - timedelta(days=60), expiry_date=now + timedelta(days=300)),
                VehicleDocument(vehicle_id=v2.id, document_type=DocumentType.FITNESS, document_number="FIT-771199", file_reference="enc://fit_ka04mk9988.pdf", issue_date=now - timedelta(days=60), expiry_date=now + timedelta(days=300)),
                VehicleDocument(vehicle_id=v2.id, document_type=DocumentType.PUC, document_number="PUC-551100", file_reference="enc://puc_ka04mk9988.pdf", issue_date=now - timedelta(days=20), expiry_date=now + timedelta(days=160)),
            ])

            l2 = RentalListing(
                vehicle_id=v2.id,
                owner_citizen_id="CIT-OWNER-001",
                rate_per_hour=250.0,
                rate_per_day=2200.0,
                rate_per_km=25.0,
                security_deposit=3500.0,
                pickup_location="Devanahalli Farmer Produce Hub, Bengaluru Rural",
                pickup_coordinates="13.2483,77.7126",
                rental_rules="Tractor / heavy agricultural machinery licence required. Trolley included.",
                status=ListingStatus.ACTIVE
            )
            db.add(l2)

            # 3. Piaggio Ape Xtra LDX (Mini Truck / 3-Wheeler)
            v3 = Vehicle(
                registration_number="KA-05-EV-4411",
                vehicle_class=VehicleClass.AUTO_RICKSHAW,
                make_model="Piaggio Ape Auto Plus (Cargo 500kg)",
                capacity_kg=550.0,
                seating_capacity=1,
                fuel_type="CNG",
                owner_citizen_id="CIT-OWNER-001",
                owner_name="Ramesh Patil",
                status=VehicleStatus.AVAILABLE,
                verification_status=VerificationStatus.VERIFIED,
                verification_reason="Vahan registry verified"
            )
            db.add(v3)
            db.flush()

            db.add_all([
                VehicleDocument(vehicle_id=v3.id, document_type=DocumentType.RC, document_number="RC-KA05EV4411", file_reference="enc://rc_ka05ev4411.pdf", issue_date=now - timedelta(days=80), expiry_date=now + timedelta(days=900)),
                VehicleDocument(vehicle_id=v3.id, document_type=DocumentType.INSURANCE, document_number="INS-332211", file_reference="enc://ins_ka05ev4411.pdf", issue_date=now - timedelta(days=40), expiry_date=now + timedelta(days=320)),
                VehicleDocument(vehicle_id=v3.id, document_type=DocumentType.FITNESS, document_number="FIT-221100", file_reference="enc://fit_ka05ev4411.pdf", issue_date=now - timedelta(days=40), expiry_date=now + timedelta(days=320)),
                VehicleDocument(vehicle_id=v3.id, document_type=DocumentType.PUC, document_number="PUC-110099", file_reference="enc://puc_ka05ev4411.pdf", issue_date=now - timedelta(days=10), expiry_date=now + timedelta(days=170)),
            ])

            l3 = RentalListing(
                vehicle_id=v3.id,
                owner_citizen_id="CIT-OWNER-001",
                rate_per_hour=90.0,
                rate_per_day=750.0,
                rate_per_km=9.0,
                security_deposit=1200.0,
                pickup_location="Yeshwanthpur Wholesale Market, Bengaluru",
                pickup_coordinates="13.0280,77.5404",
                rental_rules="Ideal for small farm produce and retail market transport.",
                status=ListingStatus.ACTIVE
            )
            db.add(l3)

            # 4. Vehicle with expired PUC to test RTO-FR-13 compliance alert & auto-blocking
            v4 = Vehicle(
                registration_number="KA-03-EX-0001",
                vehicle_class=VehicleClass.LIGHT_COMMERCIAL,
                make_model="Mahindra Bolero Maxi Truck",
                capacity_kg=1200.0,
                seating_capacity=2,
                fuel_type="DIESEL",
                owner_citizen_id="CIT-OWNER-001",
                owner_name="Ramesh Patil",
                status=VehicleStatus.AVAILABLE,
                verification_status=VerificationStatus.VERIFIED,
                verification_reason="Vahan registry verified"
            )
            db.add(v4)
            db.flush()

            # Expired PUC document (expired 15 days ago)
            db.add_all([
                VehicleDocument(vehicle_id=v4.id, document_type=DocumentType.RC, document_number="RC-KA03EX0001", file_reference="enc://rc_ka03ex0001.pdf", issue_date=now - timedelta(days=400), expiry_date=now + timedelta(days=600)),
                VehicleDocument(vehicle_id=v4.id, document_type=DocumentType.INSURANCE, document_number="INS-EX001", file_reference="enc://ins_ka03ex0001.pdf", issue_date=now - timedelta(days=200), expiry_date=now + timedelta(days=165)),
                VehicleDocument(vehicle_id=v4.id, document_type=DocumentType.FITNESS, document_number="FIT-EX001", file_reference="enc://fit_ka03ex0001.pdf", issue_date=now - timedelta(days=200), expiry_date=now + timedelta(days=165)),
                VehicleDocument(vehicle_id=v4.id, document_type=DocumentType.PUC, document_number="PUC-EX001", file_reference="enc://puc_ka03ex0001.pdf", issue_date=now - timedelta(days=200), expiry_date=now - timedelta(days=15)), # EXPIRED!
            ])

            db.commit()
            logger.info("Sample vehicles seeded successfully.")
    except Exception as e:
        logger.error(f"Error seeding data: {e}")
        db.rollback()
    finally:
        db.close()

# Mount frontend files if frontend directory exists
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")

    @app.get("/")
    def serve_frontend():
        index_file = os.path.join(frontend_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"status": "Frontend not yet built. Visit /docs for OpenAPI swagger."}

