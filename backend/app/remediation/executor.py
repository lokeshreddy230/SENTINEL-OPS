import datetime
import logging
from sqlalchemy.orm import Session
from app.services.scenario_state import scenario_state
from app.models.remediation import RemediationPlan, ExecutionRecord

logger = logging.getLogger("sentinelops.remediation.executor")

class RunbookExecutor:
    @staticmethod
    def execute_runbook(db: Session, plan_id: int) -> tuple[bool, str]:
        """
        Executes the specified runbook in the sandbox environment.
        Saves execution logs in database record.
        """
        # Initialize execution record
        record = ExecutionRecord(
            remediation_plan_id=plan_id,
            started_at=datetime.datetime.utcnow(),
            status="running"
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        plan = db.query(RemediationPlan).filter(RemediationPlan.id == plan_id).first()
        if not plan:
            record.status = "failure"
            record.completed_at = datetime.datetime.utcnow()
            record.output = "Error: Remediation plan record missing from database."
            db.commit()
            return False, record.output
            
        logger.info(f"Starting execution of runbook '{plan.runbook}' on '{plan.target}'...")
        
        # Build terminal emulation log content
        logs = []
        logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Loading authorization profiles for target: {plan.target}...")
        logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Connection established to local agent shell.")
        
        success = True
        try:
            # Engage scenario recovery process in in-memory state
            scenario_state.start_recovery()
            
            if plan.runbook == "increase_demo_pool_limit":
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] executing: helm upgrade {plan.target} --set pool.max=50")
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Release updated. Connection pool limits scaled to 50.")
            elif plan.runbook == "rolling_restart":
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] executing: kubectl rollout restart deployment/{plan.target}")
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Rolling restart started. Swapping containers...")
            elif plan.runbook == "restart_service":
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] executing: docker restart {plan.target}")
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Container state set to RESTARTING. Completed successfully.")
            elif plan.runbook == "scale_service":
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] executing: kubectl scale deployment/{plan.target} --replicas=3")
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Deployment replicas scaled from 1 to 3.")
            elif plan.runbook == "activate_circuit_breaker":
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] executing: consul kv put config/gateway/breaker_active true")
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Circuit breaker configuration applied in key-value store.")
            elif plan.runbook == "rollback_configuration":
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] executing: git revert HEAD --no-edit && kubectl apply -f config/{plan.target}/")
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Reverted last git commit rollout. Applied baseline configuration.")
            elif plan.runbook == "flush_dns_cache":
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] executing: resolvectl flush-caches && systemctl restart systemd-resolved")
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Local resolver cache flushed. DNS caching daemon restarted.")
            else:
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] executing: local_script_runner --action={plan.runbook}")
                logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Script executed successfully.")
                
            record.status = "success"
            logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Execution finished. Exit code: 0")
        except Exception as e:
            success = False
            record.status = "failure"
            logs.append(f"[{datetime.datetime.utcnow().isoformat()}] Execution aborted: {e}")
            
        record.completed_at = datetime.datetime.utcnow()
        record.output = "\n".join(logs)
        db.commit()
        
        return success, record.output
