from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.incident import IncidentReport
from app.schemas.incident import IncidentReportResponse
from typing import List

router = APIRouter(prefix="/api/reports", tags=["Reports"])

@router.get("", response_model=List[IncidentReportResponse])
def list_reports(db: Session = Depends(get_db)):
    """
    Lists all generated post-mortem reports.
    """
    return db.query(IncidentReport).order_by(IncidentReport.created_at.desc()).all()

@router.get("/{incident_id}", response_model=IncidentReportResponse)
def get_report(incident_id: str, db: Session = Depends(get_db)):
    """
    Retrieves a single incident post-mortem report by incident ID.
    """
    report = db.query(IncidentReport).filter(IncidentReport.incident_id == incident_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Incident report not found")
    return report
