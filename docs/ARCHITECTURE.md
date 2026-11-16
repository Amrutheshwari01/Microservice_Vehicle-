# AgriLink Commercial Fleet & Logistics Platform
## System Architecture & Technical Specification
**Ecosystem:** AgriLink · **Platform Service:** Commercial Fleet & Logistics · **Version:** 1.0.0

---

## 1. System Architecture Overview
The **Fleet & Logistics Service** is an independently deployable platform service within the AgriLink commerce ecosystem. It handles vehicle registration, RC document verification against national registries, rental listing and rate cards, fleet availability search, rental bookings with digital wallet escrow sagas, assignment of vehicles to AgriLink delivery jobs, and compliance tracking.

```mermaid
flowchart TD
    subgraph Clients["Actor Interfaces (Multilingual: EN, HI, KN)"]
        Owner["Vehicle Owner / Transporter"]
        Renter["Customer / Renter"]
        Admin["Admin / Operations"]
        Voice["Voice Search Input (Web Speech)"]
    end

    subgraph Fleet_Platform["Commercial Fleet Platform (Port 8000)"]
        API["FastAPI REST Endpoints (OpenAPI v3)"]
        MW["Correlation ID & Idempotency Middleware"]

        subgraph Core_Modules["Domain Modules"]
            M1["Registration & Vahan Verification"]
            M2["Vehicle Availability & Fleet Marketplace"]
            M3["Rental Listings & Rate Cards"]
            M4["Booking Escrow, Settlement & Logistics Dispatch"]
            M5["Compliance Tracking, Safety Audits & Exports"]
        end

        Outbox["Transactional Outbox Engine"]
        DB[(Relational Database)]
        Filestore[(AES-256 Encrypted Document Store)]
    end

    subgraph External_Services["Platform Connectivity"]
        CIS_Identity["Identity & Auth Service\nToken Claims & KYC Verification"]
        CIS_Wallet["Digital Wallet Service\nEscrow Hold, Release, Refund"]
        AGL_Delivery["Logistics Dispatch System\nDelivery Job Assignment Requests"]
        Ext_Registry["External State Vahan Registry Adapter\nExponential Retry & Admin Fallback"]
        AI_OCR["Smart AI/ML OCR Service\nRC Field Auto-Extraction"]
    end

    Owner --> API
    Renter --> API
    Admin --> API
    Voice --> Renter

    API --> MW --> Core_Modules
    Core_Modules --> DB
    Core_Modules --> Filestore
    Core_Modules --> Outbox

    M1 <--> Ext_Registry
    M1 <--> AI_OCR
    Core_Modules <--> CIS_Identity
    M4 <--> CIS_Wallet
    M4 <--> AGL_Delivery
    Outbox -.->|Event Bus Publish| CIS_Wallet
    Outbox -.->|VehicleAssigned Event| AGL_Delivery
```

---

## 2. Vehicle Lifecycle State Machine
The lifecycle of every registered vehicle strictly adheres to the state transitions below:

```mermaid
stateDiagram-v2
    [*] --> PENDING: Register Commercial Vehicle with RC
    PENDING --> VERIFIED: Vahan National Registry Verified
    PENDING --> SUSPENDED: RC Rejected / Blacklisted
    
    VERIFIED --> AVAILABLE: Publish Rental Listing
    VERIFIED --> UNDER_MAINTENANCE: Routine Maintenance
    VERIFIED --> SUSPENDED: Administrative Suspension
    
    AVAILABLE --> RESERVED: Booking Confirmed with Escrow
    AVAILABLE --> IN_TRANSIT: Logistics Delivery Assigned
    AVAILABLE --> UNDER_MAINTENANCE: Scheduled Maintenance
    AVAILABLE --> SUSPENDED: Document Expired / Compliance Expiry
    
    RESERVED --> RENTED: Handover Recorded (Trip Starts)
    RESERVED --> AVAILABLE: Booking Cancelled
    
    RENTED --> AVAILABLE: Return & Wallet Settlement (Trip Completes)
    RENTED --> UNDER_MAINTENANCE: Return with Reported Damage
    
    IN_TRANSIT --> AVAILABLE: Delivery Job Completed
    IN_TRANSIT --> UNDER_MAINTENANCE: Damaged in Transit
    
    UNDER_MAINTENANCE --> AVAILABLE: Repaired & Compliant
    UNDER_MAINTENANCE --> VERIFIED: Listing Paused
    
    SUSPENDED --> VERIFIED: Renewed Certificates / Verified by Operations
```

---

## 3. Booking Escrow Saga & Automated Settlement

```mermaid
sequenceDiagram
    autonumber
    actor Renter as Customer / Renter
    participant Fleet as Fleet Platform API
    participant Outbox as Transactional Outbox
    participant DB as Platform Database
    participant Wallet as Digital Wallet Service
    actor Owner as Vehicle Owner

    Renter->>Fleet: POST /v1/bookings (vehicle_id, timeslot, idempotency_key)
    Fleet->>Fleet: Validate KYC Status & Driving Licence Class
    Fleet->>DB: Check Overlap Exclusion (Zero Double-Booking)
    Fleet->>Fleet: Compute Duration, Base Rent, Deposit & Total Hold
    Fleet->>DB: Create Booking in PENDING_HOLD & Start Saga (60s Deadline)
    
    Fleet->>Wallet: POST /v1/holds (citizen_id, total_hold, ref, idempotency_key)
    alt Funds Available
        Wallet-->>Fleet: 200 OK (FundsHeld, hold_id)
        Fleet->>DB: Update Booking (CONFIRMED) & Vehicle (RESERVED)
        Fleet->>Outbox: Record 'BookingConfirmed' Event
        Fleet-->>Renter: 201 Created (Booking Confirmed)
    else Insufficient Funds or Timeout (>60s)
        Wallet-->>Fleet: 402 Payment Required
        Fleet->>DB: Auto-Cancel Booking (FAILED) & Vehicle (AVAILABLE)
        Fleet-->>Renter: 402 Failed (Auto-cancelled within 60s)
    end

    Note over Renter,Owner: Trip Starts (Vehicle Handover)
    Renter->>Fleet: POST /v1/bookings/{id}/handover (odometer, fuel, notes)
    Fleet->>DB: Booking (ACTIVE), Vehicle (RENTED)

    Note over Renter,Owner: Trip Ends (Return & Settlement)
    Renter->>Fleet: POST /v1/bookings/{id}/return (odometer, fuel, damage)
    Fleet->>Wallet: POST /v1/holds/{id}/release (Release base rent to Owner)
    Wallet-->>Owner: Funds Credited to Owner Wallet
    Fleet->>Wallet: POST /v1/holds/{id}/refund (Refund deposit minus damage to Renter)
    Wallet-->>Renter: Deposit Credited to Renter Wallet
    Fleet->>DB: Booking (COMPLETED), Vehicle (AVAILABLE)
    Fleet->>Outbox: Record 'RentalSettlementCompleted' Event
```

---

## 4. Key Architectural Standards
- **Zero Double-Booking Guarantee:** Atomic database range overlap verification on confirmed time slots.
- **Digital Wallet Escrow:** Real-time fund hold before booking confirmation with automated timeout cancellation.
- **Registry Outage Resilience:** Asynchronous retry queue with exponential back-off and administrative review queue.
- **Enterprise Security:** JWT-based stateless authentication, role authorization, and AES-256 envelope document encryption.
- **Event-Driven Outbox:** Transactional outbox engine ensuring reliable cross-system message delivery.
- **Multilingual Localization:** Dynamic English, Hindi (हिंदी), and Kannada (ಕನ್ನಡ) dictionary with browser voice recognition.
