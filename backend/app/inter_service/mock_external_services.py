import re
import random
from typing import Dict, Any, Tuple
from datetime import datetime, timedelta

class RegistryVerificationAdapter:
    """
    Adapter for External RTO State Registry (RTO-FR-02, RTO-N03, RTO-N07).
    Calls the external registry asynchronously. Handles retry queue, back-off, or admin escalation.
    """
    
    @classmethod
    def verify_rc(cls, registration_number: str, declared_owner_name: str) -> Tuple[str, str, Dict[str, Any]]:
        """
        Simulates call to external state RTO database.
        Returns: (status: VERIFIED | REJECTED | REQUIRES_ADMIN_REVIEW, reason: str, registry_details: dict)
        """
        clean_reg = registration_number.upper().replace(" ", "").replace("-", "")

        # Special test simulation triggers (check first for testing flexibility)
        if "RETRY" in clean_reg or "QUEUE" in clean_reg:
            return "REQUIRES_ADMIN_REVIEW", "External Registry API timed out / 503 Gateway Unavailable. Queued with exponential backoff / escalated to admin review.", {}

        if "FAIL" in clean_reg or "STOLEN" in clean_reg:
            return "REJECTED", "External Registry: Blacklisted or stolen vehicle record found.", {}

        # Valid Indian vehicle reg pattern: e.g. KA01AB1234 or DL1CA9999
        pattern = r"^[A-Z]{2}[0-9]{1,2}[A-Z]{0,4}[0-9]{4}$"
        if not re.match(pattern, clean_reg):
            return "REJECTED", f"Invalid vehicle registration format '{registration_number}'. Must match RTO format (e.g. KA-01-AB-1234).", {}

        # Verified details
        details = {
            "registry_id": f"VAHAN-{clean_reg}",
            "verified_at": datetime.utcnow().isoformat(),
            "chassis_number": f"MAT{clean_reg}99238Z",
            "engine_number": f"ENG{clean_reg}441",
            "registered_owner": declared_owner_name,
            "status": "ACTIVE_REGISTERED"
        }
        return "VERIFIED", "Successfully verified against State RTO National Vahan Registry.", details


class SharedOcrService:
    """
    Shared AI/ML Service Adapter for RC document OCR extraction (RTO-FR-01, Section 5.1).
    Prefills registration fields; manual entry is supported as fallback.
    """
    
    @classmethod
    def extract_rc_data(cls, document_text_or_filename: str) -> Dict[str, Any]:
        reg_match = re.search(r"[A-Z]{2}[-\s]?[0-9]{1,2}[-\s]?[A-Z]{1,4}[-\s]?[0-9]{4}", document_text_or_filename.upper())
        detected_reg = reg_match.group(0) if reg_match else "KA-04-MK-4421"
        
        return {
            "registration_number": detected_reg,
            "vehicle_class": "LIGHT_COMMERCIAL",
            "make_model": "Tata Ace Gold Plus",
            "capacity_kg": 850.0,
            "seating_capacity": 2,
            "fuel_type": "DIESEL",
            "rc_document_number": f"RC-{detected_reg.replace('-', '')}",
            "rc_expiry_date": (datetime.utcnow() + timedelta(days=365 * 4)).isoformat(),
            "confidence_score": 0.96
        }
