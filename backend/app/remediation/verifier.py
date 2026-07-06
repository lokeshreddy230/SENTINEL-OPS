import datetime
import logging
from sqlalchemy.orm import Session
from app.models.remediation import VerificationResult, RemediationPlan
from app.models.metric import Metric

logger = logging.getLogger("sentinelops.remediation.verifier")

class TelemetryVerifier:
    @staticmethod
    def verify_recovery(db: Session, plan_id: int) -> bool:
        """
        Validates telemetry health parameters after runbook execution.
        Saves before/after metric snapshots for safety verification logs.
        """
        plan = db.query(RemediationPlan).filter(RemediationPlan.id == plan_id).first()
        if not plan:
            return False
            
        logger.info(f"Verifier running verification checks for plan {plan_id} (target: {plan.target})...")
        
        # Grab recent metric items to compile before/after comparisons
        history = db.query(Metric)\
            .filter(Metric.service_id == plan.target)\
            .order_by(Metric.timestamp.desc())\
            .limit(6)\
            .all()
            
        if not history:
            return False
            
        latest = history[0]
        # In this simulation, we consider the service recovered if the latest metrics are normal
        is_recovered = latest.error_rate < 1.0 and latest.db_pool_utilization < 0.95 and latest.latency < 500.0
        
        # Assemble metrics snapshots
        before_metric = history[-1] if len(history) > 1 else latest
        
        verification = VerificationResult(
            remediation_plan_id=plan_id,
            timestamp=datetime.datetime.utcnow(),
            success=is_recovered,
            metrics_before={
                "cpu": before_metric.cpu_usage,
                "mem": before_metric.memory_usage,
                "error_rate": before_metric.error_rate,
                "latency": before_metric.latency,
                "db_pool": before_metric.db_pool_utilization
            },
            metrics_after={
                "cpu": latest.cpu_usage,
                "mem": latest.memory_usage,
                "error_rate": latest.error_rate,
                "latency": latest.latency,
                "db_pool": latest.db_pool_utilization
            },
            details=f"Verification completed. CPU: {latest.cpu_usage:.1f}%, Error Rate: {latest.error_rate:.2f}%, Latency: {latest.latency:.1f}ms. Status: {'RECOVERED' if is_recovered else 'ANOMALOUS'}"
        )
        db.add(verification)
        db.commit()
        
        return is_recovered
