from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.remediation import RemediationPlan
from app.schemas.remediation import RemediationPlanResponse
from typing import List

router = APIRouter(prefix="/api/approvals", tags=["Approvals"])

@router.get("", response_model=List[RemediationPlanResponse])
def list_pending_approvals(db: Session = Depends(get_db)):
    """
    Returns a list of all proposed remediation plans waiting for SRE approval.
    """
    return db.query(RemediationPlan).filter(RemediationPlan.status == "proposed").all()
