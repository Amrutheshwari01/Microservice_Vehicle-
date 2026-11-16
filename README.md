# AgriLink Commercial Fleet & Logistics Platform

> **AgriLink Ecosystem · Commercial Fleet, Vehicle Registry & Logistics Platform**  
> Full-stack production-ready platform: Layered FastAPI backend, interactive multilingual frontend, digital wallet escrow, Vahan registry verification adapter, and real-time transactional event stream.

---

## 🌟 Platform Capabilities

### 1. Commercial Vehicle Onboarding & Verification
- **Automated Vehicle Registration:** Register commercial vehicles with Registration Certificate (RC) number and document upload with encrypted-at-rest storage. Includes **Smart OCR auto-fill** to streamline document entry.
- **National Vahan Registry Verification:** Immediate automated verification adapter against the government vehicle database, complete with retry queue and fallback routing to the operations review queue.
- **Identity & KYC Token Validation:** Verified ownership binding to user identity with KYC tier validation.

### 2. Vehicle Availability & Fleet Marketplace
- **Vehicle Lifecycle State Machine:** Strict, deterministic state transitions:  
  `PENDING` ➔ `VERIFIED` ➔ `AVAILABLE` ➔ `RESERVED` ➔ `RENTED` ➔ `AVAILABLE`  
  Also supports `IN_TRANSIT` (logistics delivery job), `UNDER_MAINTENANCE`, and `SUSPENDED` (compliance alert).
- **High-Speed Fleet Marketplace Search:** Real-time filtering by location (APMC market yards), vehicle class (light commercial, agricultural tractor, heavy truck, 3-wheeler auto), minimum payload capacity, and daily budget.
- **Availability Calendar:** Real-time busy/free slot inspector with strict double-booking protection.

### 3. Rental Listings & Rate Management
- **Dynamic Rate Cards:** Hourly, daily, and per-kilometer rates, refundable security deposit, APMC pickup locations, and custom rental rules.
- **Listing Lifecycle Management:** Edit, pause, or withdraw listings. Active rental modifications are strictly protected against mid-trip tampering.

### 4. Booking Escrow, Trip Handover & Automated Settlement
- **Driver Eligibility Verification:** Enforces valid driving licence classes matching the vehicle type (LMV, HMV, Tractor, 3-Wheeler) and KYC verification.
- **Strict Overlap Prevention:** Database constraints guarantee zero double-booking on confirmed vehicles.
- **Protected Wallet Escrow:** Rental fees and security deposits are reserved in the digital wallet upon confirmation. Automatic cancellation on reservation failure.
- **Trip Handover & Return Metrics:** Comprehensive condition tracking (odometer, fuel %, inspection notes, damage deductions).
- **Automated Settlement:** Automatic wallet settlement upon trip completion — releases base rent payout to the vehicle owner and refunds the security deposit back to the customer.
- **Fair Cancellation Engine:** Automated tiered refund policy based on notice period.

### 5. Automated Logistics & Delivery Dispatch
- **AgriLink Farm-to-Market Dispatch:** Accepts delivery job assignments, matches optimal commercial vehicles from the nearest APMC hub, transitions vehicle status to `IN_TRANSIT`, and emits real-time tracking events.

### 6. Compliance, Safety & Audit Records
- **Automated Fleet Safety Scans:** Continuously tracks Insurance, Fitness, State Permit, and PUC certificate expirations; automatically pauses non-compliant vehicles from search listings.
- **Official Records & Audit Trails:** End-to-end audit log with distributed correlation tracking IDs and one-click export to CSV & JSON.

### 7. Custom User Authentication & Multilingual Support
- **Full Authentication Control:** Users can freely register new accounts with their own chosen credentials (name, email, password, role, driving licence) and log in seamlessly.
- **Complimentary Welcome Credits:** Every new account receives ₹30,000 instant wallet credits to test bookings.
- **Multilingual Support:** English, Hindi (हिंदी), and Kannada (ಕನ್ನಡ) localization with Web Speech API voice search.

---

## 🚀 Quick Start Guide

### 1. Requirements
- Python 3.10+
- Modern Web Browser (Chrome, Edge, Firefox)

### 2. Run Backend & Frontend
```bash
python backend/run.py
```
* **Frontend Web Application:** [http://localhost:8000](http://localhost:8000)
* **Interactive OpenAPI Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Service Discovery Catalog:** [http://localhost:8000/v1/inter-service/catalog](http://localhost:8000/v1/inter-service/catalog)

### 3. Run Automated Domain Test Suite
```bash
python -m pytest backend/tests -v
```
All 17 domain test suites pass cleanly with full coverage across all functional domains.

---

## 📁 Repository Structure
```
Microservice_Vehicle-/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── middleware.py           # Correlation ID tracking middleware
│   │   │   ├── deps.py                 # Token claims & role authorization checks
│   │   │   └── v1/                     # Versioned REST endpoints
│   │   │       ├── auth.py             # User signup, login & session endpoints
│   │   │       ├── vehicles.py         # Registration & fleet search
│   │   │       ├── listings.py         # Rental listings & rate cards
│   │   │       ├── bookings.py         # Booking saga, handover & settlement
│   │   │       ├── vehicle_requests.py # Logistics delivery dispatch
│   │   │       ├── compliance.py       # Expiry tracking & safety sweeps
│   │   │       ├── records.py          # Admin audit & CSV export
│   │   │       └── inter_service_events.py # Outbox, wallet & catalog APIs
│   │   ├── config.py                   # Environment settings & storage paths
│   │   ├── database.py                 # SQLAlchemy engine & session factory
│   │   ├── models/                     # Relational schema (vehicles, listings, bookings, users)
│   │   ├── schemas/                    # Pydantic validation contracts
│   │   ├── modules/                    # Layered business logic
│   │   │   ├── m1_registration/        # Registration & Vahan registry adapter
│   │   │   ├── m2_fleet/               # Lifecycle state machine & search
│   │   │   ├── m3_listing/             # Listing rules & rate cards
│   │   │   ├── m4_booking/             # Booking saga, pricing & settlement
│   │   │   └── m5_compliance/          # Expiry alerts & audit exports
│   │   ├── inter_service/              # Outbox, Wallet client, Identity client
│   │   └── main.py                     # FastAPI application & static mounts
│   ├── tests/                          # Domain test suites
│   ├── requirements.txt                # Python dependencies
│   └── run.py                          # Server launcher
├── frontend/
│   ├── index.html                      # Production Single Page Application
│   ├── css/styles.css                  # Responsive UI design & component styles
│   └── js/
│       ├── i18n.js                     # Multilingual dictionary (EN, HI, KN)
│       ├── api.js                      # REST API client with correlation tracking
│       ├── voice.js                    # Web Speech API voice search
│       └── app.js                      # UI state, authentication & interactive modals
├── docs/
│   ├── ARCHITECTURE.md                 # System architecture & state machine diagrams
│   └── INTER_SERVICE_INTEGRATION.md    # Integration contracts & event streams
└── README.md
```

---

## 📡 REST API Endpoints

| Method | Endpoint | Description | Domain |
|---|---|---|---|
| `POST` | `/v1/auth/signup` | Register custom user credentials | Authentication |
| `POST` | `/v1/auth/login` | Sign in with email and password | Authentication |
| `GET` | `/v1/auth/me` | Fetch active profile and live wallet balance | Authentication |
| `POST` | `/v1/vehicles` | Register commercial vehicle with RC upload & auto-verify | Fleet Registry |
| `POST` | `/v1/vehicles/ocr-extract` | Smart OCR document extraction helper | Smart Services |
| `GET` | `/v1/vehicles/search` | Fleet search with filters & compliance check | Fleet Marketplace |
| `GET` | `/v1/vehicles/{id}/availability` | Availability calendar showing busy/free slots | Fleet Marketplace |
| `PATCH` | `/v1/vehicles/{id}/status` | Enforce vehicle lifecycle state transitions | Fleet Registry |
| `POST` | `/v1/vehicles/{id}/verification-review` | Administrator verification decision fallback | Fleet Operations |
| `POST` | `/v1/listings` | Create rental listing with rate card | Rental Listings |
| `PATCH` | `/v1/listings/{id}` | Edit, pause, or withdraw rental listing | Rental Listings |
| `POST` | `/v1/bookings` | Booking request with wallet escrow hold | Bookings & Escrow |
| `POST` | `/v1/bookings/{id}/handover` | Record vehicle handover metrics (odometer/fuel) | Trip Operations |
| `POST` | `/v1/bookings/{id}/return` | Record return & execute wallet settlement | Trip Operations |
| `POST` | `/v1/bookings/{id}/cancel` | Cancellation policy calculation and refund | Bookings & Escrow |
| `POST` | `/v1/vehicle-requests` | Logistics delivery vehicle dispatch | Logistics Dispatch |
| `POST` | `/v1/vehicles/{id}/documents` | Upload compliance certificates with expiry | Safety & Compliance |
| `POST` | `/v1/compliance/sweep` | Scan fleet and auto-block expired vehicles | Safety & Compliance |
| `GET` | `/v1/records/export` | Download audit history (CSV / JSON) | Official Records |
| `GET` | `/v1/records/export/vehicles` | Download official vehicle registry (CSV) | Official Records |
| `GET` | `/v1/inter-service/outbox` | View transactional outbox event queue | Event Stream |
| `POST` | `/v1/inter-service/outbox/dispatch` | Publish pending outbox events | Event Stream |
| `GET` | `/v1/inter-service/catalog` | Platform API contracts & discovery metadata | Service Catalog |
