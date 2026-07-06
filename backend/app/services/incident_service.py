from sqlalchemy.orm import Session
from app.models.incident import Incident, IncidentEvent, IncidentReport
from app.models.remediation import RemediationPlan, Approval
from app.schemas.incident import IncidentCreate
from typing import List, Optional
import datetime

class IncidentService:
    @staticmethod
    def get_incident(db: Session, incident_id: str) -> Optional[Incident]:
        return db.query(Incident).filter(Incident.id == incident_id).first()

    @staticmethod
    def get_incidents(db: Session) -> List[Incident]:
        return db.query(Incident).order_by(Incident.detected_at.desc()).all()

    @staticmethod
    def create_incident(db: Session, incident_in: IncidentCreate, severity: str = "MEDIUM") -> Incident:
        db_incident = Incident(
            title=incident_in.title,
            description=incident_in.description,
            severity=severity,
            service_id=incident_in.service_id,
            status="detected",
            detected_at=datetime.datetime.utcnow()
        )
        db.add(db_incident)
        db.commit()
        db.refresh(db_incident)
        
        # Add initial incident event
        IncidentService.add_event(
            db, 
            incident_id=db_incident.id, 
            sender="Detector", 
            message=f"Incident detected on service '{incident_in.service_id}': {incident_in.title}"
        )
        
        return db_incident

    @staticmethod
    def add_event(db: Session, incident_id: str, sender: str, message: str) -> IncidentEvent:
        db_event = IncidentEvent(
            incident_id=incident_id,
            sender=sender,
            message=message,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(db_event)
        
        # Also update incident status/time if required
        db.commit()
        db.refresh(db_event)
        return db_event

    @staticmethod
    def update_incident_status(db: Session, incident_id: str, status: str, root_cause: str = None, confidence: float = None) -> Optional[Incident]:
        db_incident = IncidentService.get_incident(db, incident_id)
        if not db_incident:
            return None
        
        db_incident.status = status
        if root_cause:
            db_incident.root_cause = root_cause
        if confidence is not None:
            db_incident.confidence = confidence
            
        if status == "resolved":
            db_incident.resolved_at = datetime.datetime.utcnow()
            
        db.commit()
        db.refresh(db_incident)
        return db_incident

    @staticmethod
    def get_incident_events(db: Session, incident_id: str) -> List[IncidentEvent]:
        return db.query(IncidentEvent)\
            .filter(IncidentEvent.incident_id == incident_id)\
            .order_by(IncidentEvent.timestamp.asc())\
            .all()

    @staticmethod
    def get_incident_remediation_plans(db: Session, incident_id: str) -> List[RemediationPlan]:
        return db.query(RemediationPlan)\
            .filter(RemediationPlan.incident_id == incident_id)\
            .all()
            
    @staticmethod
    def get_incident_report(db: Session, incident_id: str) -> Optional[IncidentReport]:
        return db.query(IncidentReport).filter(IncidentReport.incident_id == incident_id).first()
