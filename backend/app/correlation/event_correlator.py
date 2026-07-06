import datetime
import logging
import asyncio
from sqlalchemy.orm import Session
from app.correlation.dependency_graph import DependencyGraph
from app.models.incident import Incident
from app.services.incident_service import IncidentService
from app.schemas.incident import IncidentCreate
from app.websocket.manager import event_publisher

logger = logging.getLogger("sentinelops.event_correlator")

class EventCorrelator:
    @staticmethod
    async def correlate_anomaly(db: Session, anomaly: dict) -> Incident:
        """
        Correlates a newly detected anomaly into an active incident or creates a new one.
        """
        service_id = anomaly["service"]
        metric_field = anomaly["affected_metric"]
        severity = anomaly["severity"]
        
        logger.info(f"Correlating anomaly: service={service_id}, metric={metric_field}, severity={severity}")
        
        # Look back 60 seconds for unresolved incidents
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(seconds=60)
        open_incidents = db.query(Incident)\
            .filter(Incident.status != "resolved", Incident.status != "failed", Incident.detected_at >= cutoff)\
            .order_by(Incident.detected_at.desc())\
            .all()
            
        for incident in open_incidents:
            # Check if this anomaly's service is related to the incident's service
            if DependencyGraph.is_dependent_or_related(db, incident.service_id, service_id):
                logger.info(f"Correlating anomaly on '{service_id}' to existing incident '{incident.id}' ('{incident.title}')")
                
                # Append correlation timeline event
                IncidentService.add_event(
                    db,
                    incident_id=incident.id,
                    sender="Correlator",
                    message=f"Correlated {severity} anomaly on '{service_id}' ({metric_field} = {anomaly['current_value']:.2f}) based on downstream relationship."
                )
                
                # Upgrade severity if incoming anomaly has a higher severity
                severity_ranks = {"LOW": 1, "MEDIUM": 2, "HIGH": 3, "CRITICAL": 4}
                if severity_ranks.get(severity, 0) > severity_ranks.get(incident.severity, 0):
                    incident.severity = severity
                    db.commit()
                    IncidentService.add_event(
                        db,
                        incident_id=incident.id,
                        sender="Correlator",
                        message=f"Upgraded incident severity to {severity}."
                    )
                
                # Notify frontend of incident status change
                await event_publisher.publish("incident_event", {
                    "incident_id": incident.id,
                    "sender": "Correlator",
                    "message": f"Correlated {severity} anomaly on '{service_id}' ({metric_field}) to incident {incident.id}.",
                    "type": "incident_update"
                })
                
                return incident

        # If no correlation match, spawn a new incident
        logger.info(f"No matching active incident. Spawning new incident for service={service_id}")
        
        title = f"High error/anomaly rate on {service_id}"
        description = f"Anomaly detector flagged {severity} deviations in {metric_field} on service {service_id} (value: {anomaly['current_value']:.2f}, baseline: {anomaly['baseline_value']:.2f})."
        
        from app.services.scenario_state import scenario_state
        if scenario_state.active_scenario == "4":
            title = "[GOOGLE-OUTAGE-2025] API Gateway Crash Loop"
            description = "Google Cloud API management system incorrect change rollout caused ServiceControl crash loops in regional API Gateways."
        elif scenario_state.active_scenario == "5":
            title = "[CLOUDFLARE-OUTAGE-2025] Bot Management DB Permission Outage"
            description = "Cloudflare Bot Management feature file exceeded maximum size limits due to a database permission alteration."
        elif scenario_state.active_scenario == "6":
            title = "[AWS-OUTAGE-2025] DynamoDB DNS Lookup Failure"
            description = "AWS DynamoDB DNS automated management service failed in region US-EAST-1, causing cascading failures in dependent microservices."
        elif anomaly["affected_metric"] == "db_pool_utilization":
            title = f"Database connection pool exhaustion on {service_id}"
        elif anomaly["affected_metric"] == "memory_usage" and anomaly["trend"] == "increasing":
            title = f"Progressive memory growth (leak risk) on {service_id}"
            
        incident_in = IncidentCreate(
            title=title,
            description=description,
            severity=severity,
            service_id=service_id
        )
        
        new_incident = IncidentService.create_incident(db, incident_in, severity)
        
        # Publish notification for new incident
        await event_publisher.publish("incident_event", {
            "incident_id": new_incident.id,
            "sender": "Detector",
            "message": f"New incident created: {new_incident.title}",
            "type": "incident_new",
            "data": {
                "id": new_incident.id,
                "title": new_incident.title,
                "severity": new_incident.severity,
                "status": new_incident.status,
                "service_id": new_incident.service_id,
                "detected_at": new_incident.detected_at.isoformat()
            }
        })
        
        # Trigger async investigation
        # In Phase 3/4, we can run a simple mock or call investigator agent. We'll trigger investigation now.
        asyncio.create_task(run_investigation_background(new_incident.id))
        
        return new_incident

async def run_investigation_background(incident_id: str):
    await asyncio.sleep(2.0)
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        from app.agents.orchestrator import orchestrate_investigation_flow
        await orchestrate_investigation_flow(db, incident_id)
    except Exception as e:
        logger.error(f"Error in background agent orchestration: {e}")
    finally:
        db.close()
