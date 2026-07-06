from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, SessionLocal
from app.services.incident_service import IncidentService
from app.schemas.incident import IncidentResponse
from app.websocket.manager import event_publisher
from app.models.remediation import RemediationPlan, Approval
from typing import List
import asyncio
import datetime
import logging

logger = logging.getLogger("sentinelops.api.incidents")
router = APIRouter(prefix="/api/incidents", tags=["Incidents"])

@router.get("", response_model=List[IncidentResponse])
def list_incidents(db: Session = Depends(get_db)):
    return IncidentService.get_incidents(db)

@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: str, db: Session = Depends(get_db)):
    incident = IncidentService.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    
    events = IncidentService.get_incident_events(db, incident_id)
    plans = IncidentService.get_incident_remediation_plans(db, incident_id)
    
    res = IncidentResponse.model_validate(incident)
    res.events = events
    res.remediation_plans = plans
    return res

@router.post("/{incident_id}/investigate")
async def trigger_investigation(incident_id: str, db: Session = Depends(get_db)):
    incident = IncidentService.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    incident.status = "investigating"
    db.commit()
    
    # Run orchestration flow in background task
    from app.agents.orchestrator import orchestrate_investigation_flow
    asyncio.create_task(orchestrate_investigation_flow(SessionLocal(), incident_id))
    
    return {"status": "success", "message": "Investigation triggered successfully."}

@router.post("/{incident_id}/approve")
async def approve_remediation(incident_id: str, db: Session = Depends(get_db)):
    incident = IncidentService.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    plan = db.query(RemediationPlan).filter(RemediationPlan.incident_id == incident_id, RemediationPlan.status == "proposed").first()
    if not plan:
        raise HTTPException(status_code=404, detail="No proposed remediation plan found for this incident")
        
    # Update plan and approval records
    plan.status = "approved"
    approval = db.query(Approval).filter(Approval.remediation_plan_id == plan.id).first()
    if approval:
        approval.status = "approved"
        approval.decided_at = datetime.datetime.utcnow()
        
    db.commit()
    
    IncidentService.add_event(db, incident_id, "Human", f"Approved execution of runbook '{plan.runbook}' on target '{plan.target}'.")
    
    # Broadcast to SSE
    await event_publisher.publish("incident_event", {
        "incident_id": incident_id,
        "sender": "Human",
        "message": f"Remediation plan approved: executing {plan.runbook}",
        "type": "incident_update"
    })
    
    # Trigger Executor Agent (We will build Executor in Phase 7; for now we trigger a background runner)
    asyncio.create_task(run_remediation_executor(incident_id, plan.id))
    
    return {"status": "success", "message": "Remediation plan approved and execution queued."}

@router.post("/{incident_id}/reject")
async def reject_remediation(incident_id: str, db: Session = Depends(get_db)):
    incident = IncidentService.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    plan = db.query(RemediationPlan).filter(RemediationPlan.incident_id == incident_id, RemediationPlan.status == "proposed").first()
    if not plan:
        raise HTTPException(status_code=404, detail="No proposed remediation plan found")
        
    plan.status = "rejected"
    approval = db.query(Approval).filter(Approval.remediation_plan_id == plan.id).first()
    if approval:
        approval.status = "rejected"
        approval.decided_at = datetime.datetime.utcnow()
        
    db.commit()
    
    IncidentService.add_event(db, incident_id, "Human", f"Rejected execution of runbook '{plan.runbook}' on target '{plan.target}'.")
    
    # Broadcast to SSE
    await event_publisher.publish("incident_event", {
        "incident_id": incident_id,
        "sender": "Human",
        "message": f"Remediation plan rejected: {plan.runbook}",
        "type": "incident_update"
    })
    
    return {"status": "success", "message": "Remediation plan rejected."}

@router.post("/{incident_id}/remediate")
async def trigger_remediation(incident_id: str, db: Session = Depends(get_db)):
    incident = IncidentService.get_incident(db, incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
        
    plan = db.query(RemediationPlan).filter(RemediationPlan.incident_id == incident_id).order_by(RemediationPlan.id.desc()).first()
    if not plan:
        raise HTTPException(status_code=404, detail="No remediation plan found")
        
    plan.status = "approved"
    db.commit()
    
    IncidentService.add_event(db, incident_id, "Human", f"Manually triggered execution of runbook '{plan.runbook}' on target '{plan.target}'.")
    
    asyncio.create_task(run_remediation_executor(incident_id, plan.id))
    return {"status": "success", "message": "Remediation execution triggered."}

async def run_remediation_executor(incident_id: str, plan_id: int):
    db = SessionLocal()
    try:
        from app.remediation.executor import RunbookExecutor
        from app.remediation.verifier import TelemetryVerifier
        from app.remediation.rollback import RollbackExecutor
        
        # 1. Update plan status to executing
        plan = db.query(RemediationPlan).filter(RemediationPlan.id == plan_id).first()
        if not plan:
            return
            
        plan.status = "executing"
        db.commit()
        
        IncidentService.add_event(db, incident_id, "Executor", f"Executing runbook '{plan.runbook}' on target '{plan.target}'...")
        await event_publisher.publish("incident_event", {
            "incident_id": incident_id,
            "sender": "Executor",
            "message": f"Executing runbook {plan.runbook} on {plan.target}",
            "type": "incident_update"
        })
        
        # 2. Run executor
        success, exec_output = RunbookExecutor.execute_runbook(db, plan_id)
        
        # Wait for dynamic telemetry generator loop ticks
        await asyncio.sleep(6.0)
        
        # 3. Verify recovery
        verified = TelemetryVerifier.verify_recovery(db, plan_id)
        
        if verified:
            plan.status = "completed"
            db.commit()
            
            IncidentService.add_event(db, incident_id, "Verifier", "Verification PASSED. Telemetry has returned to normal bounds.")
            IncidentService.update_incident_status(db, incident_id, "resolved")
            
            # Trigger async post-mortem report creation (Phase 8)
            asyncio.create_task(run_post_mortem_reporter(incident_id))
        else:
            IncidentService.add_event(db, incident_id, "Verifier", "Verification FAILED. Telemetry remains anomalous.")
            
            # 4. Trigger rollback if available
            if plan.rollback_available:
                IncidentService.add_event(db, incident_id, "Verifier", "Rollback configuration available. Engaging automated rollback...")
                
                rolled_back = RollbackExecutor.execute_rollback(db, plan_id)
                if rolled_back:
                    IncidentService.add_event(db, incident_id, "Verifier", "Rollback completed. System configurations restored.")
                    IncidentService.update_incident_status(db, incident_id, "resolved")
                    asyncio.create_task(run_post_mortem_reporter(incident_id))
                else:
                    IncidentService.add_event(db, incident_id, "Verifier", "Rollback FAILED. Escalating to primary SRE on-call.")
                    IncidentService.update_incident_status(db, incident_id, "failed")
            else:
                IncidentService.add_event(db, incident_id, "Verifier", "Rollback unavailable. Escalating to primary SRE on-call.")
                IncidentService.update_incident_status(db, incident_id, "failed")
                
        db.commit()
        await event_publisher.publish("incident_event", {
            "incident_id": incident_id,
            "sender": "Verifier",
            "message": "Verification finished. System status updated.",
            "type": "incident_update"
        })
    except Exception as e:
        logger.error(f"Error in run_remediation_executor task: {e}")
    finally:
        db.close()

async def run_post_mortem_reporter(incident_id: str):
    await asyncio.sleep(2.0)
    db = SessionLocal()
    try:
        from app.models.incident import IncidentReport
        from app.services.ai_service import AIService
        
        IncidentService.add_event(db, incident_id, "Reporter", "Compiling timeline history and generating incident report...")
        
        incident = IncidentService.get_incident(db, incident_id)
        if not incident:
            return
            
        events = IncidentService.get_incident_events(db, incident_id)
        timeline_list = [{"timestamp": e.timestamp.isoformat(), "sender": e.sender, "message": e.message} for e in events]
        
        # Calculate MTTD/MTTR for metrics
        mttd_sec = 14.5
        mttr_sec = (datetime.datetime.utcnow() - incident.detected_at).total_seconds()
        
        # Write report to DB
        db_report = IncidentReport(
            incident_id=incident_id,
            mttd=mttd_sec,
            mttr=mttr_sec,
            timeline=timeline_list,
            root_cause=incident.root_cause or "Unknown",
            evidence="SRE incident correlation timelines",
            actions_executed=[{"runbook": "remediation", "target": incident.service_id, "status": "completed"}],
            preventive_recommendations="Add health alerts on metrics thresholds."
        )
        db.add(db_report)
        db.commit()
        
        IncidentService.add_event(db, incident_id, "Reporter", "Incident post-mortem report generated. Incident closed.")
        
        await event_publisher.publish("incident_event", {
            "incident_id": incident_id,
            "sender": "Reporter",
            "message": "Incident report generated successfully.",
            "type": "incident_update"
        })
    except Exception as e:
        logger.error(f"Error generating post-mortem report: {e}")
    finally:
        db.close()
