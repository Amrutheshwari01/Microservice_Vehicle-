# AgriLink Fleet & Logistics Platform: Inter-Service Data Exchange Guide
**Document:** Inter-Service Integration & Contract Specification · **Ecosystem:** AgriLink · **Protocol:** REST + Transactional Outbox Events

---

## 1. Overview
The **Fleet & Logistics Service** interfaces with core services across the AgriLink ecosystem:
1. **Identity & Authentication Service**: Validates authentication tokens, persona claims (`VEHICLE_OWNER`, `RENTER`, `ADMIN`), KYC tier claims (`T1`, `T2`, `T3`), and driving licence classes (`LMV`, `HMV`, `TRACTOR`, `MCWG`).
2. **Digital Wallet Service**: Executes fund holds before booking confirmation, releases payouts to owners upon trip completion, processes damage deductions, and refunds deposits.
3. **Logistics & Delivery Dispatch System**: Dispatches delivery assignment requests for agricultural produce logistics and listens for `VehicleAssigned` domain events.
4. **National Vahan Registry Adapter**: Verifies vehicle registration certificates (RCs) and ownership details.

---

## 2. Inbound APIs for Platform Services

### 2.1 Logistics Delivery Job Vehicle Request
When an AgriLink farmer delivery job needs an assigned transport vehicle, the dispatch system calls this endpoint:
- **Endpoint:** `POST /v1/vehicle-requests`
- **Headers:** `Content-Type: application/json`, `X-Correlation-ID: <uuid>`, `Idempotency-Key: <key>`
- **Request Payload:**
```json
{
  "agrilink_job_ref": "AGL-DEL-2026-9042",
  "delivery_person_citizen_id": "CIT-DELIVERY-003",
  "delivery_person_name": "Suresh Gowda",
  "delivery_person_kyc_tier": "T3",
  "delivery_person_licence_classes": "LMV,HMV",
  "vehicle_class": "LIGHT_COMMERCIAL",
  "min_capacity_kg": 700.0,
  "start_time": "2026-11-20T06:00:00Z",
  "end_time": "2026-11-20T18:00:00Z",
  "destination": "Kolar APMC Mandi",
  "idempotency_key": "idemp-agl-job-9042"
}
```
- **Response (201 Created):**
```json
{
  "id": "e90a1fc7-8c84-4d01-9005-c998148e832f",
  "booking_ref": "AGL-261120-7A9B1C",
  "vehicle_id": "v-1234-5678",
  "status": "CONFIRMED",
  "agrilink_job_ref": "AGL-DEL-2026-9042",
  "total_hold_amount": 3200.0,
  "wallet_hold_status": "FUNDS_HELD",
  "created_at": "2026-11-16T09:30:00Z"
}
```
- **Lifecycle Side-Effect:** The allocated vehicle status transitions to `IN_TRANSIT`.
- **Event Published:** Emits `VehicleAssigned` event to the Transactional Outbox.

---

### 2.2 Wallet Callback Webhook
For asynchronous wallet event notifications:
- **Endpoint:** `POST /v1/inter-service/mock-wallet/webhook`
- **Request Payload:**
```json
{
  "event": "FundsHeld",
  "hold_id": "W-HLD-882910AF",
  "booking_id": "e90a1fc7-8c84-4d01-9005-c998148e832f",
  "amount": 3200.0,
  "status": "HELD",
  "timestamp": "2026-11-16T09:30:05Z"
}
```

---

## 3. Outbound Calls

### 3.1 Fund Reservation on Wallet Service
During the 2-Phase Booking Saga:
- **Call:** `POST /v1/mock-wallet/holds`
- **Payload:**
```json
{
  "citizen_id": "CIT-RENTER-002",
  "amount": 3200.0,
  "currency": "INR",
  "purpose": "VEHICLE_RENTAL_HOLD",
  "reference_id": "BK-261120-A8B9C0",
  "idempotency_key": "idemp-bk-uuid-001"
}
```

### 3.2 Rental Payout & Deposit Settlement
Upon vehicle return:
- **Payout to Owner:** `POST /v1/mock-wallet/holds/{id}/release`
  - Body: `{"amount_to_release": 1200.0, "beneficiary_citizen_id": "CIT-OWNER-001", "reference_id": "BK-261120-A8B9C0"}`
- **Deposit Refund to Renter:** `POST /v1/mock-wallet/holds/{id}/refund`
  - Body: `{"amount_to_refund": 2000.0, "reference_id": "BK-261120-A8B9C0"}`

---

## 4. Published Domain Events (Transactional Outbox)
All state-changing business operations atomically record domain events into the `outbox_events` table within the same ACID database transaction:

| Event Type | Aggregate Type | Trigger Operation | Subscribing Systems |
|---|---|---|---|
| `VehicleRegistered` | `VEHICLE` | Vehicle Onboarding & Vahan Registry Check | Operations, Analytics |
| `VehicleStatusChanged` | `VEHICLE` | Vehicle Lifecycle State Transition | Fleet Management, Search Cache |
| `RentalListingPublished`| `LISTING` | Rental Listing Published or Updated | Marketplace, Search Cache |
| `BookingConfirmed` | `BOOKING` | Booking Confirmed with Escrow Hold | Digital Wallet, Notifications |
| `VehicleAssigned` | `BOOKING` | Logistics Delivery Job Assigned | Logistics Dispatch, Driver App |
| `VehicleHandoverCompleted` | `BOOKING` | Odometer/Condition Handover Recorded | Telematics, Audit Service |
| `RentalSettlementCompleted` | `BOOKING` | Trip Complete & Wallet Settled | Digital Wallet, Accounting |
| `BookingCancelled` | `BOOKING` | Customer / Policy Cancellation | Digital Wallet, Notifications |
| `ComplianceBlockingTriggered` | `VEHICLE` | Certificate Expiry Sweep Triggered | Owner Alerts, Admin Portal |

### Reading & Polling Outbox Events:
- **Poll Outbox:** `GET /v1/inter-service/outbox?published_filter=false`
- **Dispatch Worker Trigger:** `POST /v1/inter-service/outbox/dispatch`
- **Service Catalog Metadata:** `GET /v1/inter-service/catalog`
