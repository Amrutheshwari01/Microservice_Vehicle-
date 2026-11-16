import pytest
from app.inter_service.outbox import record_event, dispatch_pending_events
from app.inter_service.wallet_client import WalletClient
from app.inter_service.identity_client import decode_token_claims, generate_mock_token

def test_outbox_transactional_recording_and_dispatch(db):
    # 1. Record event
    event = record_event(
        db=db,
        event_type="TestCrossServiceEvent",
        aggregate_type="BOOKING",
        aggregate_id="test-bk-100",
        payload={"message": "Data exchange payload"}
    )
    assert event.published is False
    db.commit()

    # 2. Dispatch pending events
    dispatched = dispatch_pending_events(db)
    assert len(dispatched) >= 1
    assert any(e.event_type == "TestCrossServiceEvent" for e in dispatched)

def test_wallet_client_hold_release_and_refund():
    # 1. Hold funds
    success, hold_id, msg = WalletClient.create_hold(
        citizen_id="CIT-RENTER-002",
        amount=1500.0,
        reference_id="BK-TEST-REF-01",
        idempotency_key="idemp-wallet-test-01"
    )
    assert success is True
    assert hold_id.startswith("W-HLD-")

    # 2. Release rental share to owner
    rel_ok, rel_msg = WalletClient.release_hold(
        hold_id=hold_id,
        amount_to_owner=1000.0,
        owner_citizen_id="CIT-OWNER-001",
        reference_id="BK-TEST-REF-01"
    )
    assert rel_ok is True

    # 3. Refund deposit to renter
    ref_ok, ref_msg = WalletClient.refund_hold(
        hold_id=hold_id,
        refund_amount=500.0,
        reference_id="BK-TEST-REF-01"
    )
    assert ref_ok is True

def test_identity_token_generation_and_decoding():
    token = generate_mock_token("CIT-OWNER-001")
    claims = decode_token_claims(token)
    assert claims["citizen_id"] == "CIT-OWNER-001"
    assert "VEHICLE_OWNER" in claims["personas"]
    assert claims["kyc_tier"] == "T2"

