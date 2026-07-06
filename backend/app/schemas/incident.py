from pydantic import BaseModel
from datetime import datetime
from typing import List, Dict, Any, Optional
from app.schemas.remediation import RemediationPlanResponse

class IncidentBase(BaseModel):
    title: str
    description: Optional[str] = None
    severity: str
    service_id: str

class IncidentCreate(IncidentBase):
    pass

class IncidentEventResponse(BaseModel):
    id: int
    incident_id: str
    timestamp: datetime
    sender: str
    message: str

    class Config:
        from_attributes = True

class HypothesisResponse(BaseModel):
    id: int
    investigation_id: int
    root_cause: str
    confidence: float
    evidence: List[str] = []
    contradicting_evidence: List[str] = []

    class Config:
        from_attributes = True

class InvestigationResponse(BaseModel):
    id: int
    incident_id: str
    summary: Optional[str] = None
    created_at: datetime
    hypotheses: List[HypothesisResponse] = []

    class Config:
        from_attributes = True

class IncidentResponse(IncidentBase):
    id: str
    status: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    root_cause: Optional[str] = None
    confidence: Optional[float] = None
    events: List[IncidentEventResponse] = []
    remediation_plans: List[RemediationPlanResponse] = []

    class Config:
        from_attributes = True

class IncidentReportResponse(BaseModel):
    id: int
    incident_id: str
    created_at: datetime
    mttd: float
    mttr: float
    timeline: List[Dict[str, Any]] = []
    root_cause: Optional[str] = None
    evidence: Optional[str] = None
    actions_executed: List[Dict[str, Any]] = []
    preventive_recommendations: Optional[str] = None

    class Config:
        from_attributes = True
