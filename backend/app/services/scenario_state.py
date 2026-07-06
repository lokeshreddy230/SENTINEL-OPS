from typing import Optional
import datetime

class ScenarioState:
    def __init__(self):
        self.active_scenario: Optional[str] = None
        self.triggered_at: Optional[datetime.datetime] = None
        
        # Scenario specific variables
        self.db_pool_utilization: float = 0.10
        self.memory_leak_growth: float = 0.0
        self.cascading_failure_active: bool = False
        self.api_gateway_crash_loop: bool = False
        self.bot_mgmt_db_outage: bool = False
        self.dynamodb_dns_failure: bool = False
        
        # Recovery state (runbook effects)
        self.recovery_started_at: Optional[datetime.datetime] = None
        self.is_recovering: bool = False
        self.recovered: bool = False

    def trigger(self, scenario_id: str):
        self.active_scenario = scenario_id
        self.triggered_at = datetime.datetime.utcnow()
        self.recovery_started_at = None
        self.is_recovering = False
        self.recovered = False
        
        self.cascading_failure_active = False
        self.api_gateway_crash_loop = False
        self.bot_mgmt_db_outage = False
        self.dynamodb_dns_failure = False
        
        if scenario_id == "1":
            self.db_pool_utilization = 0.10
        elif scenario_id == "2":
            self.memory_leak_growth = 0.0
        elif scenario_id == "3":
            self.cascading_failure_active = True
        elif scenario_id == "4":
            self.api_gateway_crash_loop = True
        elif scenario_id == "5":
            self.bot_mgmt_db_outage = True
        elif scenario_id == "6":
            self.dynamodb_dns_failure = True
            
    def start_recovery(self):
        self.is_recovering = True
        self.recovery_started_at = datetime.datetime.utcnow()

    def reset(self):
        self.active_scenario = None
        self.triggered_at = None
        self.db_pool_utilization = 0.10
        self.memory_leak_growth = 0.0
        self.cascading_failure_active = False
        self.api_gateway_crash_loop = False
        self.bot_mgmt_db_outage = False
        self.dynamodb_dns_failure = False
        self.recovery_started_at = None
        self.is_recovering = False
        self.recovered = False

# Global singleton
scenario_state = ScenarioState()
