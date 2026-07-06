import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.service import Service
from app.models.metric import Metric, LogEvent
from app.models.incident import Incident
from app.models.remediation import RemediationPlan, Approval
from app.ml.anomaly_detector import AnomalyDetector
from app.correlation.event_correlator import EventCorrelator
from app.correlation.root_cause_ranker import RootCauseRanker
from app.remediation.runbook_registry import RUNBOOK_REGISTRY
from app.remediation.policy_engine import PolicyEngine
from app.services.redaction import redact_secrets
from app.services.incident_service import IncidentService
from app.services.scenario_state import scenario_state
from app.agents.orchestrator import orchestrate_investigation_flow
import datetime
import asyncio

# Setup a clean local test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

import app.agents.orchestrator
app.agents.orchestrator.SessionLocal = TestingSessionLocal


@pytest.fixture(scope="function")
def db():
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    
    # Seed services
    services_to_seed = [
        {"id": "gateway", "name": "API Gateway", "dependencies": ["auth_service", "order_service"]},
        {"id": "auth_service", "name": "Auth Service", "dependencies": []},
        {"id": "order_service", "name": "Order Service", "dependencies": ["payment_service", "database_service"]},
        {"id": "payment_service", "name": "Payment Service", "dependencies": []},
        {"id": "database_service", "name": "Database Service", "dependencies": []},
    ]
    for s in services_to_seed:
        db_service = Service(id=s["id"], name=s["name"], dependencies=s["dependencies"], status="healthy")
        session.add(db_service)
    session.commit()
    
    yield session
    
    session.close()
    Base.metadata.drop_all(bind=engine)

def test_secret_redaction():
    text = "Database connection string: postgresql://admin:secretPass@localhost:5432/db"
    redacted = redact_secrets(text)
    assert "secretPass" not in redacted
    assert "[REDACTED]" in redacted

    api_text = "API Key: api_key='sk_live_abc123' token"
    assert "sk_live_abc123" not in redact_secrets(api_text)
    assert "[REDACTED]" in redact_secrets(api_text)

def test_anomaly_detection(db):
    # Insert historical baseline metrics
    for _ in range(10):
        m = Metric(service_id="database_service", cpu_usage=10.0, error_rate=0.0, db_pool_utilization=0.10)
        db.add(m)
    db.commit()

    # Create anomalous metric
    anomalous = Metric(service_id="database_service", cpu_usage=90.0, error_rate=15.0, db_pool_utilization=0.99)
    db.add(anomalous)
    db.commit()

    anomalies = AnomalyDetector.detect_anomalies(db, "database_service", anomalous)
    assert len(anomalies) > 0
    metrics_affected = [a["affected_metric"] for a in anomalies]
    assert "cpu_usage" in metrics_affected
    assert "error_rate" in metrics_affected

def test_runbook_allowlist_and_policy():
    # Allowlist test
    assert "increase_demo_pool_limit" in RUNBOOK_REGISTRY
    assert "arbitrary_command" not in RUNBOOK_REGISTRY

    # Policy risk evaluation
    auto_approve_low, risk_low = PolicyEngine.evaluate_remediation_risk("scale_service", "payment_service")
    assert auto_approve_low is True
    assert risk_low == "LOW"

    auto_approve_high, risk_high = PolicyEngine.evaluate_remediation_risk("rolling_restart", "payment_service")
    assert auto_approve_high is False
    assert risk_high == "HIGH"

def test_root_cause_ranking(db):
    # Database anomaly at t0
    m_db = Metric(service_id="database_service", error_rate=100.0, timestamp=datetime.datetime.utcnow() - datetime.timedelta(seconds=10))
    db.add(m_db)
    
    # Order Service anomaly at t1
    m_order = Metric(service_id="order_service", error_rate=100.0, timestamp=datetime.datetime.utcnow())
    db.add(m_order)
    db.commit()

    ranked = RootCauseRanker.rank_root_causes(db, ["order_service", "database_service"])
    assert len(ranked) > 0
    assert ranked[0]["service_id"] == "database_service"  # database failed first and order_service depends on it
    assert ranked[0]["confidence"] > 0.8

@pytest.mark.asyncio
async def test_e2e_remediation_flow(db):
    scenario_state.reset()
    
    # 1. Trigger scenario 1
    scenario_state.trigger("1")
    assert scenario_state.active_scenario == "1"
    
    # 2. Simulate anomaly detection & correlation
    anomaly = {
        "is_anomaly": True,
        "anomaly_score": 1.0,
        "affected_metric": "db_pool_utilization",
        "service": "database_service",
        "severity": "CRITICAL",
        "baseline_value": 0.10,
        "current_value": 1.0,
        "trend": "increasing"
    }
    
    incident = await EventCorrelator.correlate_anomaly(db, anomaly)
    assert incident is not None
    assert incident.service_id == "database_service"
    
    # Call orchestrator flow directly for test execution
    await orchestrate_investigation_flow(db, incident.id)
    
    # Verify investigation succeeded
    db.refresh(incident)
    assert incident.status == "proposed"
    assert incident.root_cause is not None
    
    plan = db.query(RemediationPlan).filter(RemediationPlan.incident_id == incident.id).first()
    assert plan is not None
    assert plan.status == "proposed"  # Risk is MEDIUM, so it requires approval
    
    # 3. Operator Approval
    plan.status = "approved"
    approval = db.query(Approval).filter(Approval.remediation_plan_id == plan.id).first()
    if approval:
        approval.status = "approved"
    db.commit()
    
    # 4. Execute remediation
    from app.remediation.executor import RunbookExecutor
    from app.remediation.verifier import TelemetryVerifier
    
    success, output = RunbookExecutor.execute_runbook(db, plan.id)
    assert success is True
    assert scenario_state.is_recovering is True
    
    # Simulate verifier recovery check
    healthy_metric = Metric(
        service_id="database_service",
        cpu_usage=12.0,
        memory_usage=25.0,
        error_rate=0.0,
        latency=5.0,
        db_pool_utilization=0.15,
        timestamp=datetime.datetime.utcnow()
    )
    db.add(healthy_metric)
    db.commit()

    scenario_state.recovered = True
    verified = TelemetryVerifier.verify_recovery(db, plan.id)
    assert verified is True
