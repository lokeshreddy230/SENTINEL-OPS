from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text, Boolean
from app.database import Base
import datetime

class RemediationPlan(Base):
    __tablename__ = "remediation_plans"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    runbook = Column(String, nullable=False)  # restart_service, scale_service, etc.
    target = Column(String, nullable=False)  # service name
    reason = Column(String, nullable=True)
    risk = Column(String, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    rollback_available = Column(Boolean, default=False)
    status = Column(String, default="proposed")  # proposed, approved, rejected, executing, completed, failed, rolled_back

class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    remediation_plan_id = Column(Integer, ForeignKey("remediation_plans.id", ondelete="CASCADE"), index=True, nullable=False)
    approver_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    status = Column(String, default="pending")  # pending, approved, rejected
    decided_at = Column(DateTime, nullable=True)
    reason = Column(String, nullable=True)

class ExecutionRecord(Base):
    __tablename__ = "execution_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    remediation_plan_id = Column(Integer, ForeignKey("remediation_plans.id", ondelete="CASCADE"), index=True, nullable=False)
    started_at = Column(DateTime, default=datetime.datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")  # running, success, failure
    output = Column(Text, nullable=True)

class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    remediation_plan_id = Column(Integer, ForeignKey("remediation_plans.id", ondelete="CASCADE"), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    success = Column(Boolean, default=False)
    metrics_before = Column(JSON, default=dict)
    metrics_after = Column(JSON, default=dict)
    details = Column(Text, nullable=True)
