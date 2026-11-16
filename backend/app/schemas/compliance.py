from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.schemas.vehicle import DocumentResponse

class ComplianceStatusResponse(BaseModel):
    vehicle_id: str
    registration_number: str
    is_compliant: bool
    status_summary: str
    expired_documents: List[DocumentResponse] = []
    expiring_soon_documents: List[DocumentResponse] = []
    valid_documents: List[DocumentResponse] = []
    can_list: bool
    can_book: bool
    blocking_reason: Optional[str] = None

class ExpiryCheckSummary(BaseModel):
    total_vehicles_checked: int
    compliant_vehicles: int
    non_compliant_vehicles: int
    expired_docs_count: int
    expiring_soon_count: int
    actions_taken: List[str] = []

