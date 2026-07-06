from sqlalchemy.orm import Session
from app.models.incident import Incident, Investigation, Hypothesis
from app.models.metric import Metric, LogEvent
from app.services.incident_service import IncidentService
from app.services.ai_service import AIService
from app.websocket.manager import event_publisher
import datetime
import json
import logging

logger = logging.getLogger("sentinelops.agents.investigator")

class InvestigatorAgent:
    @staticmethod
    async def investigate(db: Session, incident_id: str) -> dict:
        logger.info(f"Investigator Agent starting analysis for incident: {incident_id}")
        
        # 1. Fetch incident
        incident = IncidentService.get_incident(db, incident_id)
        if not incident:
            logger.error(f"Incident {incident_id} not found.")
            return {}
            
        IncidentService.add_event(db, incident_id, "Investigator", "Beginning trace analysis and log correlation...")
        
        # 2. Gather metrics (last 10 minutes)
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=10)
        recent_metrics = db.query(Metric)\
            .filter(Metric.service_id == incident.service_id, Metric.timestamp >= cutoff)\
            .order_by(Metric.timestamp.desc())\
            .limit(20)\
            .all()
            
        metrics_summary = [
            {
                "timestamp": m.timestamp.isoformat(),
                "cpu": m.cpu_usage,
                "mem": m.memory_usage,
                "latency": m.latency,
                "errors": m.error_rate,
                "db_pool": m.db_pool_utilization
            }
            for m in recent_metrics
        ]
        
        # 3. Gather logs (last 50 logs)
        recent_logs = db.query(LogEvent)\
            .filter(LogEvent.service_id == incident.service_id)\
            .order_by(LogEvent.timestamp.desc())\
            .limit(50)\
            .all()
            
        logs_summary = [
            {
                "timestamp": l.timestamp.isoformat(),
                "level": l.level,
                "message": l.message,
                "trace_id": l.trace_id
            }
            for l in recent_logs
        ]
        
        # 4. Search RAG memory for similar historical incidents
        from app.rag.retriever import IncidentRetriever
        symptoms_query = f"{incident.title} {incident.description}"
        similar_incidents = IncidentRetriever.get_similar_incidents(
            symptoms=symptoms_query,
            service_id=incident.service_id,
            limit=2
        )
        
        # Log similar incidents search
        if similar_incidents:
            matched_ids = ", ".join([inc["incident_id"] for inc in similar_incidents])
            IncidentService.add_event(
                db, 
                incident_id, 
                "Investigator", 
                f"RAG search matched historical incidents: {matched_ids}"
            )
        else:
            IncidentService.add_event(
                db, 
                incident_id, 
                "Investigator", 
                "RAG search did not match any similar historical incidents."
            )
        
        # 5. Call LLM provider or fallback Demo Mode
        raw_result = AIService.analyze_incident(
            incident_title=incident.title,
            affected_service=incident.service_id,
            logs=logs_summary,
            metrics=metrics_summary,
            similar_incidents=similar_incidents
        )
        
        # 6. Save investigation results in Database
        investigation = Investigation(
            incident_id=incident_id,
            summary=raw_result.get("summary", "Investigation completed."),
            created_at=datetime.datetime.utcnow()
        )
        db.add(investigation)
        db.commit()
        db.refresh(investigation)
        
        recommended_hyp = raw_result.get("recommended_hypothesis", "")
        chosen_confidence = 0.0
        
        # Save hypotheses
        for hyp in raw_result.get("hypotheses", []):
            db_hyp = Hypothesis(
                investigation_id=investigation.id,
                root_cause=hyp.get("root_cause", "Unknown"),
                confidence=hyp.get("confidence", 0.0),
                evidence=hyp.get("evidence", []),
                contradicting_evidence=hyp.get("contradicting_evidence", [])
            )
            db.add(db_hyp)
            
            if db_hyp.root_cause == recommended_hyp:
                chosen_confidence = db_hyp.confidence
                
        # 7. Update incident with probable root cause
        incident.root_cause = recommended_hyp
        incident.confidence = chosen_confidence
        incident.status = "investigating_complete"
        db.commit()
        
        IncidentService.add_event(
            db, 
            incident_id, 
            "Investigator", 
            f"Root cause hypothesis generated: '{recommended_hyp}' (Confidence: {chosen_confidence:.2f})"
        )
        
        await event_publisher.publish("incident_event", {
            "incident_id": incident_id,
            "sender": "Investigator",
            "message": f"Investigation complete. Probable cause: {recommended_hyp}",
            "type": "incident_update"
        })
        
        return raw_result
