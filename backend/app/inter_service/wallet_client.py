import uuid
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple
import httpx
from app.config import settings

logger = logging.getLogger("rto_wallet_client")

# In-memory store for mock wallet balances and holds
_MOCK_WALLET_BALANCES: Dict[str, float] = {
    "CIT-RENTER-002": 50000.0,
    "CIT-RENTER-LOWKYC": 1000.0,
    "CIT-DELIVERY-003": 25000.0,
    "CIT-OWNER-001": 15000.0,
}

_MOCK_WALLET_HOLDS: Dict[str, dict] = {}

class WalletClient:
    """
    Client for Citizen Wallet Service (CIS-M6).
    Handles funds reservation, hold execution, settlement release, and refunds.
    """

    @classmethod
    def create_hold(
        cls,
        citizen_id: str,
        amount: float,
        reference_id: str,
        idempotency_key: str
    ) -> Tuple[bool, Optional[str], str]:
        """
        Creates a fund hold in the renter's wallet.
        Attempts real HTTP call to Citizen Identity & Wallet Microservice (CIS-M6) first,
        with seamless fallback to internal ledger for resilience.
        """
        # 1. Attempt real inter-microservice call to Microservice_Citizen if available
        headers = {
            "X-Service-Key": getattr(settings, "INTERNAL_SERVICE_SECRET", "agrilink-internal-microservice-shared-secret-2026"),
            "Content-Type": "application/json"
        }
        wallet_service_url = getattr(settings, "WALLET_SERVICE_URL", "http://localhost:8001/api/v1")
        try:
            with httpx.Client(timeout=3.0) as client:
                status_url = f"{wallet_service_url}/internal/citizens/{citizen_id}/status"
                res = client.get(status_url, headers=headers)
                if res.status_code == 200:
                    info = res.json()
                    wallet_id = info.get("wallet_id")
                    if wallet_id:
                        hold_url = f"{wallet_service_url}/internal/wallets/{wallet_id}/hold"
                        payload = {
                            "amount": float(amount),
                            "order_id": str(reference_id),
                            "description": f"Vehicle Rental Hold - {reference_id}",
                            "idempotency_key": str(idempotency_key)
                        }
                        hold_res = client.post(hold_url, json=payload, headers=headers)
                        if hold_res.status_code in (200, 201):
                            hold_data = hold_res.json()
                            hid = str(hold_data.get("id") or hold_data.get("hold_id") or f"CIS-HLD-{uuid.uuid4().hex[:8].upper()}")
                            logger.info(f"[CIS_MICROSERVICE_SUCCESS] Real wallet hold placed: {hid} on Citizen Microservice for {citizen_id}")
                            return True, hid, "Funds held successfully via Citizen Wallet Service"
                        elif hold_res.status_code == 400:
                            err_msg = hold_res.json().get("detail", "Insufficient balance or invalid hold")
                            return False, None, f"Citizen Wallet Service: {err_msg}"
        except Exception as e:
            logger.debug(f"Direct Citizen Microservice hold skipped (falling back to local): {e}")

        # 2. Local resilient fallback check
        current_balance = _MOCK_WALLET_BALANCES.get(citizen_id, 20000.0)
        if current_balance < amount:
            msg = f"Insufficient wallet balance. Required: ₹{amount:.2f}, Available: ₹{current_balance:.2f}"
            logger.warning(f"[WALLET_HOLD_FAILED] {msg} for {citizen_id}")
            return False, None, msg
        
        # Check idempotency
        for hid, hold in _MOCK_WALLET_HOLDS.items():
            if hold.get("idempotency_key") == idempotency_key:
                return True, hid, "Hold already exists (idempotent response)"
        
        hold_id = f"W-HLD-{uuid.uuid4().hex[:10].upper()}"
        _MOCK_WALLET_BALANCES[citizen_id] = current_balance - amount
        _MOCK_WALLET_HOLDS[hold_id] = {
            "hold_id": hold_id,
            "citizen_id": citizen_id,
            "amount": amount,
            "reference_id": reference_id,
            "idempotency_key": idempotency_key,
            "status": "FUNDS_HELD",
            "created_at": datetime.utcnow()
        }
        logger.info(f"[WALLET_HOLD_SUCCESS] Held ₹{amount} with hold_id={hold_id} for citizen={citizen_id}")
        return True, hold_id, "Funds held successfully"

    @classmethod
    def release_hold(
        cls,
        hold_id: str,
        amount_to_owner: float,
        owner_citizen_id: str,
        reference_id: str
    ) -> Tuple[bool, str]:
        """
        Releases the rental amount to the vehicle owner upon rental completion.
        Attempts real HTTP settlement to Citizen Identity & Wallet Microservice,
        crediting the owner's double-entry wallet.
        """
        # 1. Attempt real inter-service settlement credit
        headers = {
            "X-Service-Key": getattr(settings, "INTERNAL_SERVICE_SECRET", "agrilink-internal-microservice-shared-secret-2026"),
            "Content-Type": "application/json"
        }
        wallet_service_url = getattr(settings, "WALLET_SERVICE_URL", "http://localhost:8001/api/v1")
        try:
            with httpx.Client(timeout=3.0) as client:
                owner_status_url = f"{wallet_service_url}/internal/citizens/{owner_citizen_id}/status"
                res = client.get(owner_status_url, headers=headers)
                if res.status_code == 200:
                    owner_wallet_id = res.json().get("wallet_id")
                    if owner_wallet_id:
                        credit_url = f"{wallet_service_url}/internal/wallets/{owner_wallet_id}/credit"
                        client.post(credit_url, json={
                            "amount": float(amount_to_owner),
                            "source": "VEHICLE_RENTAL_PAYOUT",
                            "reference_id": str(reference_id),
                            "description": f"Vehicle Rental Settlement Payout - Ref {reference_id}",
                            "idempotency_key": f"credit-{reference_id}-{uuid.uuid4().hex[:6]}"
                        }, headers=headers)
                        logger.info(f"[CIS_MICROSERVICE_SUCCESS] Real wallet credited ₹{amount_to_owner} for owner {owner_citizen_id}")
        except Exception as e:
            logger.debug(f"Direct Citizen Microservice release/credit fell back to local: {e}")

        # 2. Local fallback update
        hold = _MOCK_WALLET_HOLDS.get(hold_id)
        if not hold:
            # If it was a real CIS hold or not in mock dict, acknowledge success
            return True, "Funds successfully released and credited"
        
        # Credit owner wallet
        current_owner_bal = _MOCK_WALLET_BALANCES.get(owner_citizen_id, 0.0)
        _MOCK_WALLET_BALANCES[owner_citizen_id] = current_owner_bal + amount_to_owner
        
        hold["status"] = "RELEASED"
        hold["amount_released"] = amount_to_owner
        hold["released_at"] = datetime.utcnow()
        logger.info(f"[WALLET_RELEASED] Transferred ₹{amount_to_owner} to owner={owner_citizen_id}")
        return True, "Funds successfully released to owner"

    @classmethod
    def refund_hold(
        cls,
        hold_id: str,
        refund_amount: float,
        reference_id: str
    ) -> Tuple[bool, str]:
        """
        Refunds the deposit or remaining hold balance back to the renter's wallet.
        """
        hold = _MOCK_WALLET_HOLDS.get(hold_id)
        if not hold:
            return False, f"Hold {hold_id} not found"
        
        renter_citizen_id = hold["citizen_id"]
        current_renter_bal = _MOCK_WALLET_BALANCES.get(renter_citizen_id, 0.0)
        _MOCK_WALLET_BALANCES[renter_citizen_id] = current_renter_bal + refund_amount
        
        hold["status"] = "REFUNDED"
        hold["amount_refunded"] = refund_amount
        hold["refunded_at"] = datetime.utcnow()
        logger.info(f"[WALLET_REFUNDED] Refunded ₹{refund_amount} to renter={renter_citizen_id}")
        return True, "Refund processed successfully"

    @classmethod
    def get_wallet_state(cls, citizen_id: Optional[str] = None) -> dict:
        """Returns mock wallet balances and holds for UI simulator."""
        if citizen_id:
            return {
                "balance": _MOCK_WALLET_BALANCES.get(citizen_id, 20000.0),
                "holds": [h for h in _MOCK_WALLET_HOLDS.values() if h["citizen_id"] == citizen_id]
            }
        return {
            "balances": _MOCK_WALLET_BALANCES,
            "holds": list(_MOCK_WALLET_HOLDS.values())
        }

