from app.remediation.runbook_registry import RUNBOOK_REGISTRY
from typing import Tuple

class PolicyEngine:
    @staticmethod
    def evaluate_remediation_risk(runbook: str, target: str) -> Tuple[bool, str]:
        """
        Validates parameters and runbooks against registry constraints.
        Returns (auto_approve, risk_level).
        """
        # Validate runbook name
        if runbook not in RUNBOOK_REGISTRY:
            return False, "CRITICAL"  # Untrusted or disallowed runbook
            
        # Validate target service parameter
        allowed_targets = ["gateway", "auth_service", "order_service", "payment_service", "database_service"]
        if target not in allowed_targets:
            return False, "CRITICAL"  # Untrusted target host/container
            
        risk = RUNBOOK_REGISTRY[runbook]["risk"]
        
        # Rules: LOW risk actions auto-approve. Others hold for operator review.
        if risk == "LOW":
            return True, risk
        return False, risk
