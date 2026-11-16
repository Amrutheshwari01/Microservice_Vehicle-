# AgriLink RTO / Vehicle Registry & Rental Service Microservice
> **AgriLink Ecosystem · Microservice 3 (MS-03 / MS-04)**  
> Comprehensive Full-Stack Implementation: Layered Backend, Interactive Multilingual Frontend, Transactional Outbox, and Microservice Integration Hub.

---

## 🌟 Key Capabilities & Requirements Mapping

### 1. RTO-M1: Vehicle Registration & Verification
- **RTO-FR-01:** Vehicle registration with RC document upload and encrypted-at-rest storage (`AES-256` envelope encryption simulation). Includes optional **Shared AI/ML OCR** extraction to automatically prefill fields.
- **RTO-FR-02:** RC verification against National Vahan Registry via adapter. Implements exponential back-off retry queue (up to 24h) and fallback routing to the Administrator review queue.
- **RTO-FR-03:** Ownership validation against KYC token identity (`citizen_id` plain value without foreign keys into Identity service).

### 2. RTO-M2: Vehicle Availability & Fleet Management
- **RTO-FR-04:** Strict vehicle lifecycle state machine:
  `PENDING` ➔ `VERIFIED` ➔ `AVAILABLE` ➔ `RESERVED` ➔ `RENTED` ➔ `AVAILABLE`  
  Also supports `IN_TRANSIT` (AgriLink delivery job), `UNDER_MAINTENANCE`, and `SUSPENDED` (admin action).
- **RTO-FR-05:** High-speed fleet search with filters (class, payload capacity, price, location). Real-time **Availability Calendar** modal with slot exclusivity.

### 3. RTO-M3: Vehicle Rental Listing
- **RTO-FR-06:** Rental listings with rate cards (per hour, day, km), security deposit, APMC pickup locations, and rules. Blocked automatically if compliance documents are expired.
- **RTO-FR-07:** Listing management (edit, pause, withdraw); modifications strictly refused while an active rental exists.

### 4. RTO-M4: Rental Booking, Payments & AgriLink Delivery
- **RTO-FR-08:** Booking eligibility checks (KYC tier T1 or higher, driving licence class matching vehicle type).
- **RTO-N01:** **Strict Overlap Prevention** (Zero overlapping confirmed bookings enforced via DB constraints and range overlap checks).
- **RTO-FR-09 & RTO-N02:** **2-Phase Booking Saga**: Wallet fund hold (CIS-M6) before confirmation; auto-cancellation within 60s on hold failure.
- **RTO-FR-10:** Handover and Return metrics (odometer, fuel %, condition notes, damage deduction, and automatic wallet settlement releasing rent to owner and refunding deposit).
- **RTO-FR-11:** Cancellation policy engine with tiered refunds based on time-to-trip.
- **RTO-FR-12:** **AgriLink Delivery Vehicle Assignment** (`POST /v1/vehicle-requests`): Accepts delivery job reference from AgriLink system (AGL-M5), allocates vehicle, holds wallet funds, sets state to `IN_TRANSIT`, and emits `VehicleAssigned` event.

### 5. RTO-M5: Compliance & RTO Records
- **RTO-FR-13:** Compliance tracking (Insurance, Fitness, Permit, PUC), expiry alerts, and automated sweep that blocks listings and bookings on document expiry.
- **RTO-FR-14:** Official records, audit trail with correlation IDs (S04), and one-click export to CSV & JSON.

### 6. Inter-Microservice Connectivity (S06)
- **Transactional Outbox Pattern:** Guarantees atomic domain event recording and publishing.
- **Service Discovery Catalog:** Metadata endpoint at `/v1/inter-service/catalog`.
- **Citizen Identity Simulator (CIS-M4):** Token claims and persona switcher.
- **Citizen Wallet Simulator (CIS-M6):** Real-time balance and hold inspector.
- **Multilingual UI (S07):** English, Hindi (हिंदी), and Kannada (ಕನ್ನಡ) with Web Speech API voice search.

---

## 🚀 Quick Start Guide

### 1. Requirements
- Python 3.10+ (tested with Python 3.11)
- Modern Web Browser (Chrome, Edge, Firefox)

### 2. Run Backend & Frontend (Single Command)
```bash
python backend/run.py
```
* **Frontend Web Application:** [http://localhost:8000](http://localhost:8000)
* **Interactive OpenAPI Swagger Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)
* **Service Discovery Catalog:** [http://localhost:8000/v1/inter-service/catalog](http://localhost:8000/v1/inter-service/catalog)

### 3. Run Automated Domain Test Suite (84% Coverage)
```bash
python -m pytest backend/tests -v --cov=backend/app/modules --cov=backend/app/inter_service
```
All 16 test suites pass cleanly in ~1.5s with **84% domain test coverage** (exceeding RTO-N07's 70% requirement).

---

## 📁 Repository Structure
```
Vehicle_Microservice/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   ├── middleware.py           # Pure ASGI S04 Correlation ID middleware
│   │   │   ├── deps.py                 # Token claims & role authorization checks
│   │   │   └── v1/                     # Versioned REST endpoints (S02)
│   │   │       ├── vehicles.py         # Registration & search (RTO-M1, M2)
│   │   │       ├── listings.py         # Rental listings & rate cards (RTO-M3)
│   │   │       ├── bookings.py         # Booking saga & settlement (RTO-M4)
│   │   │       ├── vehicle_requests.py # AgriLink delivery job assignment (RTO-FR-12)
│   │   │       ├── compliance.py       # Expiry tracking & sweep (RTO-M5)
│   │   │       ├── records.py          # Admin audit & CSV export (RTO-FR-14)
│   │   │       └── inter_service_events.py # Outbox, wallet & catalog APIs
│   │   ├── config.py                   # Pydantic environment settings
│   │   ├── database.py                 # SQLAlchemy engine & session factory
│   │   ├── models/                     # SQLAlchemy relational schema
│   │   ├── schemas/                    # Pydantic validation contracts
│   │   ├── modules/                    # Layered domain business logic (S03)
│   │   │   ├── m1_registration/        # Registration & registry adapter
│   │   │   ├── m2_fleet/               # Lifecycle state machine & search
│   │   │   ├── m3_listing/             # Listing rules & rate cards
│   │   │   ├── m4_booking/             # Booking saga, pricing & settlement
│   │   │   └── m5_compliance/          # Expiry alerts & audit exports
│   │   ├── inter_service/              # Outbox, Wallet client, Identity client
│   │   └── main.py                     # FastAPI application & static mounts
│   ├── tests/                          # Comprehensive PyTest domain test suites
│   ├── requirements.txt                # Python dependencies
│   └── run.py                          # Microservice launcher
├── frontend/
│   ├── index.html                      # Single Page Application
│   ├── css/styles.css                  # Modern responsive design
│   └── js/
│       ├── i18n.js                     # Multilingual dictionary (EN, HI, KN - S07)
│       ├── api.js                      # REST API client with correlation IDs
│       ├── voice.js                    # Web Speech API voice search (S07)
│       └── app.js                      # UI state & interactive modals
├── docs/
│   ├── ARCHITECTURE.md                 # ATAM evaluation & state machine diagrams
│   └── INTER_SERVICE_INTEGRATION.md    # Cross-microservice data exchange guide
└── README.md
```

---

## 📡 Key API Endpoints Summary

| Method | Endpoint | Description | Layer / Module |
|---|---|---|---|
| `POST` | `/v1/vehicles` | Register vehicle with RC upload & auto-verify | RTO-M1 (RTO-FR-01, 03) |
| `POST` | `/v1/vehicles/ocr-extract` | Shared AI/ML OCR extraction helper | Shared AI Service (RTO-FR-01) |
| `GET` | `/v1/vehicles/search` | Fleet search with filters & compliance check | RTO-M2 (RTO-FR-05) |
| `GET` | `/v1/vehicles/{id}/availability` | Availability calendar showing busy/free slots | RTO-M2 (RTO-FR-05) |
| `PATCH` | `/v1/vehicles/{id}/status` | Enforce vehicle lifecycle state transitions | RTO-M2 (RTO-FR-04) |
| `POST` | `/v1/vehicles/{id}/verification-review` | Administrator verification decision fallback | RTO-M1 (RTO-FR-02) |
| `POST` | `/v1/listings` | Create rental listing with rate card | RTO-M3 (RTO-FR-06) |
| `PATCH` | `/v1/listings/{id}` | Edit, pause, or withdraw rental listing | RTO-M3 (RTO-FR-07) |
| `POST` | `/v1/bookings` | 2-Phase booking request with wallet hold saga | RTO-M4 (RTO-FR-08, 09) |
| `POST` | `/v1/bookings/{id}/handover` | Record vehicle handover metrics (odometer/fuel) | RTO-M4 (RTO-FR-10) |
| `POST` | `/v1/bookings/{id}/return` | Record return & execute wallet settlement | RTO-M4 (RTO-FR-10) |
| `POST` | `/v1/bookings/{id}/cancel` | Cancellation policy calculation and refund | RTO-M4 (RTO-FR-11) |
| `POST` | `/v1/vehicle-requests` | **AgriLink delivery vehicle assignment** | RTO-M4 (RTO-FR-12) |
| `POST` | `/v1/vehicles/{id}/documents` | Upload compliance certificates with expiry | RTO-M5 (RTO-FR-13) |
| `POST` | `/v1/compliance/sweep` | Scan fleet and auto-block expired vehicles | RTO-M5 (RTO-FR-13) |
| `GET` | `/v1/records/export` | Download audit history (CSV / JSON) | RTO-M5 (RTO-FR-14) |
| `GET` | `/v1/records/export/vehicles` | Download official vehicle registry (CSV) | RTO-M5 (RTO-FR-14) |
| `GET` | `/v1/inter-service/outbox` | View transactional outbox event queue | S06 Data Exchange |
| `POST` | `/v1/inter-service/outbox/dispatch` | Publish pending outbox events to broker | S06 Data Exchange |
| `GET` | `/v1/inter-service/catalog` | Microservice catalog & contract metadata | S02 Service Discovery |

