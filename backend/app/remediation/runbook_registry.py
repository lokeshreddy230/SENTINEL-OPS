# Approved Runbook Registry
# Prevents arbitrary shell executions by locking execution to allowed functions only.

RUNBOOK_REGISTRY = {
    "increase_demo_pool_limit": {
        "risk": "MEDIUM",
        "rollback_available": True,
        "description": "Increases database connection pool limit dynamically from 20 to 50"
    },
    "rolling_restart": {
        "risk": "HIGH",
        "rollback_available": True,
        "description": "Performs zero-downtime rolling restart of container tasks"
    },
    "restart_service": {
        "risk": "HIGH",
        "rollback_available": False,
        "description": "Forcibly restarts service container process"
    },
    "scale_service": {
        "risk": "LOW",
        "rollback_available": True,
        "description": "Increases replica count of target service dynamically"
    },
    "activate_circuit_breaker": {
        "risk": "LOW",
        "rollback_available": True,
        "description": "Engages load-shedding circuit breaker upstream"
    },
}
