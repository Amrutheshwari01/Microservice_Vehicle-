-- ====================================================================
-- AgriLink Commercial Fleet & Logistics Platform
-- Supabase (PostgreSQL) Production Schema & Seed Data
-- ====================================================================

-- 1. Enable UUID Extension (Optional convenience)
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ====================================================================
-- TABLE 1: users (Citizen Accounts, Custom Auth & Biometrics)
-- ====================================================================
CREATE TABLE IF NOT EXISTS users (
    id VARCHAR(64) PRIMARY KEY,
    name VARCHAR(120) NOT NULL,
    email VARCHAR(120) UNIQUE NOT NULL,
    phone VARCHAR(20),
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(32) NOT NULL DEFAULT 'RENTER',
    kyc_tier VARCHAR(16) NOT NULL DEFAULT 'T1',
    driving_licence_classes VARCHAR(100) NOT NULL DEFAULT 'LMV',
    face_descriptor TEXT,            -- 4096-dim ZNCC biometric vector (JSON array)
    face_thumbnail TEXT,             -- Base64 JPEG avatar image
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);

-- ====================================================================
-- TABLE 2: vehicles (Commercial Fleet Registry)
-- ====================================================================
CREATE TABLE IF NOT EXISTS vehicles (
    id VARCHAR(36) PRIMARY KEY,
    registration_number VARCHAR(32) UNIQUE NOT NULL,
    vehicle_class VARCHAR(32) NOT NULL,
    make_model VARCHAR(100) NOT NULL,
    capacity_kg DOUBLE PRECISION NOT NULL DEFAULT 500.0,
    seating_capacity INTEGER NOT NULL DEFAULT 2,
    fuel_type VARCHAR(20) NOT NULL DEFAULT 'DIESEL',
    owner_citizen_id VARCHAR(64) NOT NULL,
    owner_name VARCHAR(100) NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    verification_status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    verification_reason TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vehicles_reg ON vehicles(registration_number);
CREATE INDEX IF NOT EXISTS idx_vehicles_class ON vehicles(vehicle_class);
CREATE INDEX IF NOT EXISTS idx_vehicles_owner ON vehicles(owner_citizen_id);
CREATE INDEX IF NOT EXISTS idx_vehicles_status ON vehicles(status);

-- ====================================================================
-- TABLE 3: vehicle_documents (RC, Fitness, Insurance, PUC)
-- ====================================================================
CREATE TABLE IF NOT EXISTS vehicle_documents (
    id VARCHAR(36) PRIMARY KEY,
    vehicle_id VARCHAR(36) NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    document_type VARCHAR(32) NOT NULL,
    document_number VARCHAR(64) NOT NULL,
    file_reference VARCHAR(255) NOT NULL,
    issue_date TIMESTAMP WITH TIME ZONE,
    expiry_date TIMESTAMP WITH TIME ZONE,
    is_valid BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vdocs_vehicle_id ON vehicle_documents(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_vdocs_type ON vehicle_documents(document_type);
CREATE INDEX IF NOT EXISTS idx_vdocs_expiry ON vehicle_documents(expiry_date);

-- ====================================================================
-- TABLE 4: verification_requests (Vahan Verification Retry Queue)
-- ====================================================================
CREATE TABLE IF NOT EXISTS verification_requests (
    id VARCHAR(36) PRIMARY KEY,
    vehicle_id VARCHAR(36) NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_RETRY',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 5,
    next_retry_at TIMESTAMP WITH TIME ZONE,
    adapter_response TEXT,
    admin_notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_vreq_vehicle_id ON verification_requests(vehicle_id);

-- ====================================================================
-- TABLE 5: rental_listings (Rate Cards & APMC Pickup Locations)
-- ====================================================================
CREATE TABLE IF NOT EXISTS rental_listings (
    id VARCHAR(36) PRIMARY KEY,
    vehicle_id VARCHAR(36) UNIQUE NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    owner_citizen_id VARCHAR(64) NOT NULL,
    rate_per_hour DOUBLE PRECISION NOT NULL DEFAULT 150.0,
    rate_per_day DOUBLE PRECISION NOT NULL DEFAULT 1200.0,
    rate_per_km DOUBLE PRECISION NOT NULL DEFAULT 12.0,
    security_deposit DOUBLE PRECISION NOT NULL DEFAULT 2000.0,
    pickup_location VARCHAR(255) NOT NULL,
    pickup_coordinates VARCHAR(64),
    rental_rules TEXT,
    status VARCHAR(32) NOT NULL DEFAULT 'ACTIVE',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_listings_vehicle_id ON rental_listings(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_listings_owner ON rental_listings(owner_citizen_id);
CREATE INDEX IF NOT EXISTS idx_listings_status ON rental_listings(status);

-- ====================================================================
-- TABLE 6: availability_windows (Time-slot Reservation Locks)
-- ====================================================================
CREATE TABLE IF NOT EXISTS availability_windows (
    id VARCHAR(36) PRIMARY KEY,
    listing_id VARCHAR(36) NOT NULL REFERENCES rental_listings(id) ON DELETE CASCADE,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    is_available BOOLEAN DEFAULT TRUE,
    notes VARCHAR(255)
);

CREATE INDEX IF NOT EXISTS idx_avail_listing_id ON availability_windows(listing_id);
CREATE INDEX IF NOT EXISTS idx_avail_start ON availability_windows(start_time);
CREATE INDEX IF NOT EXISTS idx_avail_end ON availability_windows(end_time);

-- ====================================================================
-- TABLE 7: bookings (Reservations, Escrow Holds & Financials)
-- ====================================================================
CREATE TABLE IF NOT EXISTS bookings (
    id VARCHAR(36) PRIMARY KEY,
    booking_ref VARCHAR(32) UNIQUE NOT NULL,
    vehicle_id VARCHAR(36) NOT NULL REFERENCES vehicles(id) ON DELETE CASCADE,
    renter_citizen_id VARCHAR(64) NOT NULL,
    renter_name VARCHAR(100) NOT NULL,
    renter_kyc_tier VARCHAR(16) NOT NULL,
    renter_licence_classes VARCHAR(255) NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING_HOLD',
    agrilink_job_ref VARCHAR(64),
    estimated_duration_hours DOUBLE PRECISION NOT NULL DEFAULT 1.0,
    base_rent_amount DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    deposit_amount DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    total_hold_amount DOUBLE PRECISION NOT NULL DEFAULT 0.0,
    wallet_hold_id VARCHAR(64),
    wallet_hold_status VARCHAR(32) DEFAULT 'NONE',
    idempotency_key VARCHAR(128) UNIQUE NOT NULL,
    cancellation_reason VARCHAR(255),
    cancellation_fee DOUBLE PRECISION DEFAULT 0.0,
    refund_amount DOUBLE PRECISION DEFAULT 0.0,
    cancelled_by VARCHAR(64),
    cancelled_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_bookings_ref ON bookings(booking_ref);
CREATE INDEX IF NOT EXISTS idx_bookings_vehicle ON bookings(vehicle_id);
CREATE INDEX IF NOT EXISTS idx_bookings_renter ON bookings(renter_citizen_id);
CREATE INDEX IF NOT EXISTS idx_bookings_status ON bookings(status);
CREATE INDEX IF NOT EXISTS idx_bookings_start ON bookings(start_time);
CREATE INDEX IF NOT EXISTS idx_bookings_end ON bookings(end_time);

-- ====================================================================
-- TABLE 8: booking_sagas (Distributed Saga Coordination)
-- ====================================================================
CREATE TABLE IF NOT EXISTS booking_sagas (
    id VARCHAR(36) PRIMARY KEY,
    booking_id VARCHAR(36) UNIQUE NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    saga_state VARCHAR(32) NOT NULL DEFAULT 'STARTED',
    deadline TIMESTAMP WITH TIME ZONE NOT NULL,
    compensation_reason VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- ====================================================================
-- TABLE 9: handover_records (Odometer, Fuel & Return Settlement)
-- ====================================================================
CREATE TABLE IF NOT EXISTS handover_records (
    id VARCHAR(36) PRIMARY KEY,
    booking_id VARCHAR(36) NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
    handover_type VARCHAR(16) NOT NULL,
    recorded_by_citizen_id VARCHAR(64) NOT NULL,
    odometer_reading DOUBLE PRECISION NOT NULL,
    fuel_level_percent DOUBLE PRECISION NOT NULL,
    condition_notes TEXT,
    damage_detected BOOLEAN DEFAULT FALSE,
    damage_amount DOUBLE PRECISION DEFAULT 0.0,
    photos TEXT,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_handover_booking_id ON handover_records(booking_id);

-- ====================================================================
-- TABLE 10: outbox_events (Transactional Event Dispatch)
-- ====================================================================
CREATE TABLE IF NOT EXISTS outbox_events (
    id VARCHAR(36) PRIMARY KEY,
    event_type VARCHAR(64) NOT NULL,
    aggregate_type VARCHAR(32) NOT NULL,
    aggregate_id VARCHAR(64) NOT NULL,
    payload TEXT NOT NULL,
    published BOOLEAN DEFAULT FALSE,
    published_at TIMESTAMP WITH TIME ZONE,
    retry_count INTEGER DEFAULT 0,
    correlation_id VARCHAR(64),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_outbox_pub ON outbox_events(published);
CREATE INDEX IF NOT EXISTS idx_outbox_type ON outbox_events(event_type);

-- ====================================================================
-- TABLE 11: audit_events (Compliance & Security Audit Trail)
-- ====================================================================
CREATE TABLE IF NOT EXISTS audit_events (
    id VARCHAR(36) PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    actor_id VARCHAR(64) NOT NULL,
    actor_role VARCHAR(32) NOT NULL,
    action VARCHAR(64) NOT NULL,
    entity_type VARCHAR(32) NOT NULL,
    entity_id VARCHAR(64) NOT NULL,
    details TEXT,
    correlation_id VARCHAR(64)
);

CREATE INDEX IF NOT EXISTS idx_audit_time ON audit_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_actor ON audit_events(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_action ON audit_events(action);

-- ====================================================================
-- SEED DATA: Default Demo Accounts (Password: [name]123)
-- ====================================================================
INSERT INTO users (id, name, email, phone, password_hash, role, kyc_tier, driving_licence_classes)
VALUES 
('CIT-OWNER-001', 'Ramesh Patil', 'ramesh@agrilink.in', '+91 98765 43210', 'd79b9b0068735222956cfb810842db2371cf78696ec06093cb49a029db9ab8168673f4e24eb62f5bca94957e8eb248e8da8d75ea9c6a1e36c2e391307b22d1ad', 'VEHICLE_OWNER', 'T2', 'LMV,HMV,TRACTOR'),
('CIT-RENTER-002', 'Priya Sharma', 'priya@agrilink.in', '+91 98450 11223', 'a587ce381a17937746ae0453e0d86940a0ef19d2aa7a6c525f0f3747d7c6adabff3dbfb687c71ba76319bc30d32c5890e0b3d5b06d44a0e98031d9b3e157297e', 'RENTER', 'T2', 'LMV,MCWG'),
('CIT-DELIVERY-003', 'Suresh Gowda', 'suresh@agrilink.in', '+91 97312 34567', '4e58a74e548ab03b609c95d9fb9c00b0e515d48da142fc69fcf72834b6e5114aa75cbe61c9ecba5db22fc539dfd6666ebf7b1968da9d8f99e829399eb2f1db12', 'DELIVERY_PERSON', 'T2', 'LMV,HMV'),
('CIT-ADMIN-001', 'Officer Rao', 'admin@agrilink.in', '+91 99000 88776', 'b18be574aa91ad7a5d933e144d18ecba54bb2001e9d1bf7b11d9f485db1f94d93ee14092b3c2bb023d508930438b4f65809f6e6aa45532d8471e8d98d89a263d', 'ADMIN', 'T3', 'LMV,HMV,TRACTOR,MCWG')
ON CONFLICT (email) DO NOTHING;
