import io
import csv
import json
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from app.models.vehicle import Vehicle, VehicleDocument
from app.models.booking import Booking, HandoverRecord
from app.models.audit import AuditEvent

class ExportService:
    """
    RTO-FR-14: Records, history and exports for Administrator and RTO Officials.
    """

    @classmethod
    def get_full_audit_records(cls, db: Session, limit: int = 100) -> List[Dict[str, Any]]:
        events = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc()).limit(limit).all()
        return [
            {
                "id": e.id,
                "timestamp": e.timestamp.isoformat(),
                "actor_id": e.actor_id,
                "actor_role": e.actor_role,
                "action": e.action,
                "entity_type": e.entity_type,
                "entity_id": e.entity_id,
                "details": json.loads(e.details) if e.details else {},
                "correlation_id": e.correlation_id
            }
            for e in events
        ]

    @classmethod
    def export_records_csv(cls, db: Session, entity_type: str = "ALL") -> str:
        """
        Exports audit and registry records in CSV format.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow(["Event ID", "Timestamp (UTC)", "Actor ID", "Actor Role", "Action", "Entity Type", "Entity ID", "Correlation ID", "Details"])
        
        query = db.query(AuditEvent).order_by(AuditEvent.timestamp.desc())
        if entity_type != "ALL":
            query = query.filter(AuditEvent.entity_type == entity_type.upper())
            
        for e in query.all():
            writer.writerow([
                e.id,
                e.timestamp.isoformat(),
                e.actor_id,
                e.actor_role,
                e.action,
                e.entity_type,
                e.entity_id,
                e.correlation_id or "",
                e.details or ""
            ])
            
        return output.getvalue()

    @classmethod
    def export_vehicle_registry_csv(cls, db: Session) -> str:
        """
        Exports official vehicle registry table to CSV.
        """
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["ID", "Registration No", "Class", "Make & Model", "Capacity (kg)", "Fuel", "Owner Citizen ID", "Owner Name", "Status", "Verification Status", "Registered At"])

        for v in db.query(Vehicle).order_by(Vehicle.created_at.desc()).all():
            writer.writerow([
                v.id,
                v.registration_number,
                v.vehicle_class,
                v.make_model,
                v.capacity_kg,
                v.fuel_type,
                v.owner_citizen_id,
                v.owner_name,
                v.status,
                v.verification_status,
                v.created_at.isoformat()
            ])
        return output.getvalue()

