from sqlalchemy import Column, Integer, String, Float, DateTime, JSON, ForeignKey, Text
from app.database import Base
import datetime
import uuid

def generate_uuid():
    return f"inc_{uuid.uuid4().hex[:8]}"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    role = Column(String, default="SRE")  # SRE, operator

class Incident(Base):
    __tablename__ = "incidents"

    id = Column(String, primary_key=True, default=generate_uuid, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String, default="MEDIUM")  # LOW, MEDIUM, HIGH, CRITICAL
    status = Column(String, default="detected")  # detected, investigating, proposed, executing, verified, resolved, failed
    service_id = Column(String, index=True, nullable=False)
    detected_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)
    root_cause = Column(String, nullable=True)
    confidence = Column(Float, nullable=True)

class IncidentEvent(Base):
    __tablename__ = "incident_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    sender = Column(String, nullable=False)  # Detector, Investigator, Remediator, Executor, etc.
    message = Column(Text, nullable=False)

class Investigation(Base):
    __tablename__ = "investigations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

class Hypothesis(Base):
    __tablename__ = "hypotheses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    investigation_id = Column(Integer, ForeignKey("investigations.id", ondelete="CASCADE"), index=True, nullable=False)
    root_cause = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    evidence = Column(JSON, default=list)  # List of evidence strings
    contradicting_evidence = Column(JSON, default=list)  # List of contradicting evidence strings

class IncidentReport(Base):
    __tablename__ = "incident_reports"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    incident_id = Column(String, ForeignKey("incidents.id", ondelete="CASCADE"), index=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    mttd = Column(Float, default=0.0)  # in seconds
    mttr = Column(Float, default=0.0)  # in seconds
    timeline = Column(JSON, default=list)  # list of event dictionaries
    root_cause = Column(String, nullable=True)
    evidence = Column(Text, nullable=True)
    actions_executed = Column(JSON, default=list)
    preventive_recommendations = Column(Text, nullable=True)
