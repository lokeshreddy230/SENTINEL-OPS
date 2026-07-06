from typing import TypedDict, List, Dict, Any, Annotated
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.agents.investigator import InvestigatorAgent
from app.agents.remediator import RemediatorAgent
from app.services.incident_service import IncidentService
from app.websocket.manager import event_publisher
import logging

logger = logging.getLogger("sentinelops.agents.orchestrator")

# Define LangGraph workflow state
class AgentWorkflowState(TypedDict):
    incident_id: str
    service_id: str
    metrics: List[Dict[str, Any]]
    logs: List[Dict[str, Any]]
    similar_incidents: List[Dict[str, Any]]
    hypotheses: List[Dict[str, Any]]
    recommended_hypothesis: str
    proposed_runbook: Dict[str, Any]
    policy_approved: bool

# Graph node 1: Investigation Node
async def investigate_node(state: AgentWorkflowState) -> Dict[str, Any]:
    incident_id = state["incident_id"]
    logger.info(f"[LangGraph Node] Running investigator node for incident: {incident_id}")
    
    db = SessionLocal()
    try:
        # Run Investigator Agent logic
        raw_result = await InvestigatorAgent.investigate(db, incident_id)
        
        return {
            "hypotheses": raw_result.get("hypotheses", []),
            "recommended_hypothesis": raw_result.get("recommended_hypothesis", "Unknown")
        }
    except Exception as e:
        logger.error(f"[LangGraph Node] Error in investigate_node: {e}")
        return {"recommended_hypothesis": "Unknown"}
    finally:
        db.close()

# Graph node 2: Remediation Proposal Node
async def remediate_node(state: AgentWorkflowState) -> Dict[str, Any]:
    incident_id = state["incident_id"]
    recommended_cause = state["recommended_hypothesis"]
    logger.info(f"[LangGraph Node] Running remediator node for incident={incident_id}, cause={recommended_cause}")
    
    db = SessionLocal()
    try:
        # Run Remediator Agent logic
        plan = await RemediatorAgent.propose_remediation(db, incident_id, recommended_cause)
        
        return {
            "proposed_runbook": {
                "id": plan.id,
                "runbook": plan.runbook,
                "target": plan.target,
                "risk": plan.risk,
                "status": plan.status
            },
            "policy_approved": plan.status == "approved"
        }
    except Exception as e:
        logger.error(f"[LangGraph Node] Error in remediate_node: {e}")
        return {"policy_approved": False}
    finally:
        db.close()

# Initialize StateGraph
workflow = StateGraph(AgentWorkflowState)

# Add nodes
workflow.add_node("investigate", investigate_node)
workflow.add_node("propose_remediation", remediate_node)

# Set entry point
workflow.set_entry_point("investigate")

# Set connections
workflow.add_edge("investigate", "propose_remediation")
workflow.add_edge("propose_remediation", END)

# Compile graph
compiled_workflow = workflow.compile()

async def orchestrate_investigation_flow(db: Session, incident_id: str):
    """
    Triggers the LangGraph multi-agent compilation and runs the workflow.
    """
    logger.info(f"LangGraph Orchestrator triggered for incident: {incident_id}")
    
    incident = IncidentService.get_incident(db, incident_id)
    if not incident:
        return
        
    initial_state: AgentWorkflowState = {
        "incident_id": incident_id,
        "service_id": incident.service_id,
        "metrics": [],
        "logs": [],
        "similar_incidents": [],
        "hypotheses": [],
        "recommended_hypothesis": "",
        "proposed_runbook": {},
        "policy_approved": False
    }
    
    try:
        # Run the compiled LangGraph workflow asynchronously
        await compiled_workflow.ainvoke(initial_state)
        logger.info(f"LangGraph workflow execution completed for incident {incident_id}")
    except Exception as e:
        logger.error(f"Error executing LangGraph ainvoke: {e}")
        # Fallback to direct execution if LangGraph errors out
        logger.info("Executing direct fallback orchestration...")
        raw_result = await InvestigatorAgent.investigate(db, incident_id)
        recommended = raw_result.get("recommended_hypothesis", "Unknown")
        await RemediatorAgent.propose_remediation(db, incident_id, recommended)
