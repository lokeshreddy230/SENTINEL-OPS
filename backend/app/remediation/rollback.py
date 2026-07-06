import datetime
import logging
from sqlalchemy.orm import Session
from app.services.scenario_state import scenario_state
from app.models.remediation import RemediationPlan, ExecutionRecord

logger = logging.getLogger("sentinelops.remediation.rollback")

class RollbackExecutor:
    @staticmethod
    def execute_rollback(db: Session, plan_id: int) -> bool:
        """
        Reverts the action taken by the remediation plan if verification failed.
        """
        plan = db.query(RemediationPlan).filter(RemediationPlan.id == plan_id).first()
        if not plan:
            return False
            
        logger.warning(f"Reverting runbook change for plan {plan_id} on target '{plan.target}'...")
        
        # Reset the dynamic scenario state back to normal configuration
        scenario_state.reset()
        
        plan.status = "rolled_back"
        
        # Log rollback action
        record = ExecutionRecord(
            remediation_plan_id=plan_id,
            started_at=datetime.datetime.utcnow(),
            completed_at=datetime.datetime.utcnow(),
            status="rolled_back",
            output=f"[{datetime.datetime.utcnow().isoformat()}] Rollback engaged. Configuration parameters restored to baseline values."
        )
        db.add(record)
        db.commit()
        
        return True
