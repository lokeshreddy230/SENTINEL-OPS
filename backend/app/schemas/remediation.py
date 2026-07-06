from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional

class RemediationPlanBase(BaseModel):
    incident_id: str
    runbook: str
    target: str
    reason: Optional[str] = None
    risk: str
    rollback_available: bool = False

class RemediationPlanCreate(RemediationPlanBase):
    pass

class RemediationPlanResponse(RemediationPlanBase):
    id: int
    status: str

    class Config:
        from_attributes = True

class ApprovalBase(BaseModel):
    remediation_plan_id: int
    status: str
    reason: Optional[str] = None

class ApprovalResponse(ApprovalBase):
    id: int
    approver_id: Optional[int] = None
    decided_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ExecutionRecordResponse(BaseModel):
    id: int
    remediation_plan_id: int
    started_at: datetime
    completed_at: Optional[datetime] = None
    status: str
    output: Optional[str] = None

    class Config:
        from_attributes = True

class VerificationResultResponse(BaseModel):
    id: int
    remediation_plan_id: int
    timestamp: datetime
    success: bool
    metrics_before: Dict[str, Any] = {}
    metrics_after: Dict[str, Any] = {}
    details: Optional[str] = None

    class Config:
        from_attributes = True
