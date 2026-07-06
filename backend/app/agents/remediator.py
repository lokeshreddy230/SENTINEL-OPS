from sqlalchemy.orm import Session
from app.models.remediation import RemediationPlan, Approval
from app.services.incident_service import IncidentService
from app.websocket.manager import event_publisher
import datetime
import logging

from app.config import settings

logger = logging.getLogger("sentinelops.agents.remediator")

# Approved Runbook Registry
RUNBOOK_REGISTRY = {
    "increase_demo_pool_limit": {"risk": "MEDIUM", "rollback": True, "description": "Increases database connection pool limit from 20 to 50"},
    "rolling_restart": {"risk": "HIGH", "rollback": True, "description": "Performs zero-downtime rolling restart of container tasks"},
    "restart_service": {"risk": "HIGH", "rollback": False, "description": "Forcibly restarts service container process"},
    "scale_service": {"risk": "LOW", "rollback": True, "description": "Increases replica count of target service by +1"},
    "activate_circuit_breaker": {"risk": "LOW", "rollback": True, "description": "Engages load-shedding circuit breaker upstream"},
    "rollback_configuration": {"risk": "MEDIUM", "rollback": True, "description": "Reverts the last configuration rollout to restore baseline stability"},
    "flush_dns_cache": {"risk": "LOW", "rollback": False, "description": "Flushes local resolver cache to clear broken DNS queries"},
}

class RemediatorAgent:
    @staticmethod
    async def propose_remediation(db: Session, incident_id: str, root_cause: str) -> RemediationPlan:
        logger.info(f"Remediator Agent proposing plan for incident={incident_id}, root_cause={root_cause}")
        
        # Get incident service ID
        incident = IncidentService.get_incident(db, incident_id)
        service_id = incident.service_id if incident else None
        
        # Match root cause to runbook
        root_cause_lower = root_cause.lower()
        is_google = settings.TELEMETRY_SOURCE == "google_scale"
        
        if "google" in root_cause_lower or "servicecontrol" in root_cause_lower or "api gateway crash loop" in root_cause_lower:
            runbook = "rollback_configuration"
            target = service_id or ("cdn-edge" if is_google else "gateway")
            reason = "Incorrect API configuration rollout caused ServiceControl crash loop. Proposing config rollback."
        elif "cloudflare" in root_cause_lower or "bot" in root_cause_lower or "permission" in root_cause_lower:
            runbook = "rollback_configuration"
            target = service_id or ("auth-service" if is_google else "auth_service")
            reason = "Bot Management feature file exceeds size limits. Proposing DB permission configuration rollback."
        elif "aws" in root_cause_lower or "dns" in root_cause_lower or "dynamodb" in root_cause_lower:
            runbook = "flush_dns_cache"
            target = service_id or ("search-service" if is_google else "database_service")
            reason = "DynamoDB DNS lookup failures detected. Proposing DNS resolver cache flush."
        elif "pool" in root_cause_lower:
            runbook = "increase_demo_pool_limit"
            target = service_id or ("payment-service" if is_google else "database_service")
            reason = "Database connection pool saturated (100% capacity)."
        elif "leak" in root_cause_lower or "memory" in root_cause_lower:
            runbook = "rolling_restart"
            target = service_id or ("search-service" if is_google else "payment_service")
            reason = "Linear EWMA memory consumption growth trend detected."
        else:
            runbook = "restart_service"
            target = service_id or ("payment-service" if is_google else "database_service")
            reason = "Downstream service crash detected."

        registry_info = RUNBOOK_REGISTRY.get(runbook, {"risk": "HIGH", "rollback": False})
        risk = registry_info["risk"]
        rollback_available = registry_info["rollback"]
        
        IncidentService.add_event(
            db, 
            incident_id, 
            "Remediator", 
            f"Remediator matched root cause to registry runbook '{runbook}' on target '{target}'."
        )

        # Write Remediation Plan
        plan = RemediationPlan(
            incident_id=incident_id,
            runbook=runbook,
            target=target,
            reason=reason,
            risk=risk,
            rollback_available=rollback_available,
            status="proposed"
        )
        db.add(plan)
        db.commit()
        db.refresh(plan)

        # Policy Engine risk check
        # LOW risk -> Auto approval. MEDIUM/HIGH/CRITICAL -> Await human approval.
        if risk in ["MEDIUM", "HIGH", "CRITICAL"]:
            plan.status = "proposed"
            db.commit()
            
            # Create Approval request
            approval = Approval(
                remediation_plan_id=plan.id,
                status="pending"
            )
            db.add(approval)
            db.commit()
            
            IncidentService.add_event(
                db, 
                incident_id, 
                "PolicyEngine", 
                f"Risk rating: {risk}. Human operator authorization is REQUIRED. Runbook halted."
            )
            
            await event_publisher.publish("remediation_proposed", {
                "id": plan.id,
                "incident_id": plan.incident_id,
                "runbook": plan.runbook,
                "target": plan.target,
                "reason": plan.reason,
                "risk": plan.risk,
                "rollback_available": plan.rollback_available,
                "status": plan.status
            })
        else:
            # Low risk runs automatically
            plan.status = "approved"
            db.commit()
            IncidentService.add_event(
                db, 
                incident_id, 
                "PolicyEngine", 
                f"Risk rating: {risk}. Plan auto-approved by policy engine rules."
            )
            
            # We would trigger auto-execution here
            await event_publisher.publish("remediation_approved", {
                "id": plan.id,
                "incident_id": plan.incident_id,
                "runbook": plan.runbook,
                "target": plan.target,
                "status": plan.status
            })

        # Update overall incident status
        incident = IncidentService.get_incident(db, incident_id)
        incident.status = "proposed"
        db.commit()

        await event_publisher.publish("incident_event", {
            "incident_id": incident_id,
            "sender": "Remediator",
            "message": f"Remediation plan proposed: {runbook} ({risk} risk)",
            "type": "incident_update"
        })

        return plan
