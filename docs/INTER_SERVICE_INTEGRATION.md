# AgriLink RTO Microservice: Inter-Service Data Exchange Guide
**Document:** Inter-Microservice Contract Specification · **Ecosystem:** AgriLink · **Protocol:** REST + Outbox Events

---

## 1. Overview
As Microservice 3 of the AgriLink ecosystem, the RTO & Vehicle Registry service interfaces with multiple sibling microservices:
1. **Citizen Identity Service (CIS-M4)**: Validates authentication tokens, persona claims (`VEHICLE_OWNER`, `RENTER`, `ADMIN`), KYC tier claims (`T1`, `T2`, `T3`), and driving licence classes (`LMV`, `HMV`, `TRACTOR`, `MCWG`).
2. **Citizen Wallet Service (CIS-M6)**: Executes fund holds before booking confirmation, releases payouts to owners upon trip completion, processes damage deductions, and refunds deposits.
3. **AgriLink Delivery System (AGL-M5)**: Dispatches delivery assignment requests for agricultural logistics and listens for `VehicleAssigned` domain events.
4. **External RTO National Registry (Vahan Adapter)**: Verifies vehicle registration certificates (RCs).

---

## 2. Inbound APIs for Other Microservices

### 2.1 AgriLink Delivery Job Vehicle Request (AGL-M5 -> RTO)
When an AgriLink farmer delivery job needs an assigned vehicle, AgriLink calls this endpoint:
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

### 2.2 Wallet Callback Webhook (CIS-M6 -> RTO)
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

## 3. Outbound Calls (RTO -> Sibling Microservices)

### 3.1 Fund Reservation on Wallet Service (CIS-M6)
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

## 4. Published Domain Events (Transactional Outbox - S06)
All state-changing business operations atomically record domain events into the `outbox_events` table within the same ACID database transaction:

| Event Type | Aggregate Type | Trigger Requirement | Subscribing Services |
|---|---|---|---|
| `VehicleRegistered` | `VEHICLE` | RTO-FR-01 | RTO Officials, Analytics |
| `VehicleStatusChanged` | `VEHICLE` | RTO-FR-04 | Fleet Management, Search Cache |
| `RentalListingPublished`| `LISTING` | RTO-FR-06 | AgriLink Marketplace, Search Cache |
| `BookingConfirmed` | `BOOKING` | RTO-FR-08, 09 | Citizen Wallet (CIS-M6), Notifications |
| `VehicleAssigned` | `BOOKING` | RTO-FR-12 | AgriLink Delivery (AGL-M5) |
| `VehicleHandoverCompleted` | `BOOKING` | RTO-FR-10 | Telematics, Audit Service |
| `RentalSettlementCompleted` | `BOOKING` | RTO-FR-10 | Citizen Wallet (CIS-M6), Accounting |
| `BookingCancelled` | `BOOKING` | RTO-FR-11 | Citizen Wallet (CIS-M6), Notifications |
| `ComplianceBlockingTriggered` | `VEHICLE` | RTO-FR-13 | Vehicle Owner Alerts, Admin Portal |

### Reading & Polling Outbox Events:
- **Poll Outbox:** `GET /v1/inter-service/outbox?published_filter=false`
- **Simulate Dispatch Worker:** `POST /v1/inter-service/outbox/dispatch`
- **Service Catalog Metadata:** `GET /v1/inter-service/catalog`

