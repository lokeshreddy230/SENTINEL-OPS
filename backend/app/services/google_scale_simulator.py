"""
SentinelOps - Google-Scale Real-Time Data Simulator
==================================================
This module provides realistic, real-time infrastructure data 
mimicking Google/Netflix-scale systems.

Usage (Easy Integration):
-------------------------
from app.services.google_scale_simulator import GoogleScaleSimulator

sim = GoogleScaleSimulator()
metrics = sim.get_current_metrics()
logs = sim.get_recent_logs(count=50)

# For real-time streaming (FastAPI + WebSocket)
async def stream_data(websocket):
    while True:
        data = sim.generate_realtime_update()
        await websocket.send_json(data)
        await asyncio.sleep(2)
"""

import random
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from dataclasses import dataclass, asdict
import asyncio

# ============================================
# CONFIGURATION - Google-Scale Simulation
# ============================================
SERVICES = [
    "auth-service", "payment-service", "notification-service",
    "search-service", "recommendation-engine", "user-profile",
    "video-streaming", "analytics-pipeline", "cdn-edge"
]

REGIONS = ["us-central1", "europe-west1", "asia-northeast1", "us-east1"]

METRIC_TYPES = ["cpu", "memory", "network", "disk", "request_rate", "error_rate", "latency_p99"]

# Realistic base values (Google-scale)
BASE_VALUES = {
    "cpu": (10, 40),
    "memory": (20, 50),
    "network": (120, 980),
    "disk": (25, 55),
    "request_rate": (4500, 125000),
    "error_rate": (0.001, 0.05),
    "latency_p99": (15, 110)
}


@dataclass
class ServiceMetrics:
    service: str
    region: str
    timestamp: str
    cpu: float
    memory: float
    network_mbps: float
    disk: float
    request_rate: int
    error_rate: float
    latency_p99: int
    status: str


class GoogleScaleSimulator:
    def __init__(self, seed: int = 42):
        random.seed(seed)
        self.current_state: Dict[str, Dict] = {}
        self.incident_history: List[Dict] = []
        self._initialize_state()
        self.last_update = time.time()

    def _initialize_state(self):
        """Initialize realistic baseline for all services"""
        for service in SERVICES:
            self.current_state[service] = {}
            for region in REGIONS[:3]:  # 3 active regions per service
                self.current_state[service][region] = {
                    "cpu": random.uniform(*BASE_VALUES["cpu"]),
                    "memory": random.uniform(*BASE_VALUES["memory"]),
                    "network_mbps": random.uniform(*BASE_VALUES["network"]),
                    "disk": random.uniform(*BASE_VALUES["disk"]),
                    "request_rate": random.randint(*BASE_VALUES["request_rate"]),
                    "error_rate": random.uniform(*BASE_VALUES["error_rate"]),
                    "latency_p99": random.randint(*BASE_VALUES["latency_p99"]),
                    "last_anomaly": None
                }

    def _apply_natural_drift(self, service: str, region: str):
        """Simulate realistic fluctuations"""
        state = self.current_state[service][region]
        
        # Natural variation
        drift = {
            "cpu": random.uniform(-2.5, 2.5),
            "memory": random.uniform(-1.5, 1.5),
            "network_mbps": random.uniform(-45, 60),
            "disk": random.uniform(-0.5, 0.5),
            "request_rate": random.randint(-1200, 1800),
            "error_rate": random.uniform(-0.01, 0.01),
            "latency_p99": random.randint(-5, 5)
        }
        
        for key, value in drift.items():
            if key in state:
                new_val = state[key] + value
                
                # Clamp to realistic bounds
                if key in ["cpu", "memory", "disk"]:
                    new_val = max(5, min(75, new_val))
                elif key == "error_rate":
                    new_val = max(0.0001, min(0.15, new_val))
                elif key == "latency_p99":
                    new_val = max(10, min(180, new_val))
                elif key == "request_rate":
                    new_val = max(800, min(250000, new_val))
                
                state[key] = round(new_val, 2) if isinstance(new_val, float) else int(new_val)

    def inject_anomaly(self, service: str = None, severity: str = "medium"):
        """Inject realistic anomalies for demo scenarios"""
        if not service:
            service = random.choice(SERVICES)
        
        region = random.choice(list(self.current_state[service].keys()))
        state = self.current_state[service][region]
        
        if severity == "high":
            state["cpu"] = random.uniform(92, 99)
            state["memory"] = random.uniform(88, 97)
            state["error_rate"] = random.uniform(8.5, 18.2)
            state["latency_p99"] = random.randint(1200, 3800)
            state["request_rate"] = int(state["request_rate"] * 0.3)
        elif severity == "medium":
            state["cpu"] = random.uniform(78, 91)
            state["memory"] = random.uniform(75, 86)
            state["error_rate"] = random.uniform(3.8, 7.5)
            state["latency_p99"] = random.randint(650, 1150)
        else:
            state["error_rate"] = random.uniform(1.8, 3.9)
            state["latency_p99"] = random.randint(320, 580)
        
        state["last_anomaly"] = datetime.utcnow().isoformat()
        
        return {
            "service": service,
            "region": region,
            "severity": severity,
            "timestamp": datetime.utcnow().isoformat()
        }

    def get_current_metrics(self) -> List[Dict]:
        """Return current metrics for all services"""
        now = datetime.utcnow().isoformat()
        metrics = []
        
        for service, regions in self.current_state.items():
            for region, state in regions.items():
                status = "healthy"
                if state["error_rate"] > 5 or state["cpu"] > 90:
                    status = "critical"
                elif state["error_rate"] > 2 or state["cpu"] > 75:
                    status = "warning"
                
                metrics.append({
                    "service": service,
                    "region": region,
                    "timestamp": now,
                    "cpu": round(state["cpu"], 1),
                    "memory": round(state["memory"], 1),
                    "network_mbps": round(state["network_mbps"], 1),
                    "disk": round(state["disk"], 1),
                    "request_rate": state["request_rate"],
                    "error_rate": round(state["error_rate"], 2),
                    "latency_p99": state["latency_p99"],
                    "status": status
                })
        
        return metrics

    def get_recent_logs(self, count: int = 30) -> List[Dict]:
        """Generate realistic log entries"""
        logs = []
        now = datetime.utcnow()
        
        for i in range(count):
            service = random.choice(SERVICES)
            region = random.choice(REGIONS[:3])
            timestamp = (now - timedelta(seconds=random.randint(0, 300))).isoformat()
            
            level = random.choices(
                ["INFO", "WARN", "ERROR", "DEBUG"],
                weights=[65, 18, 12, 5]
            )[0]
            
            if level == "ERROR":
                messages = [
                    f"Connection pool exhausted for {service}",
                    "Database timeout after 30s",
                    "Circuit breaker tripped",
                    "gRPC call failed: UNAVAILABLE",
                    "Memory allocation failed"
                ]
            elif level == "WARN":
                messages = [
                    "High latency detected",
                    "Rate limit approaching",
                    "Cache miss rate elevated",
                    "Replica count below target"
                ]
            else:
                messages = [
                    "Request processed successfully",
                    "Health check passed",
                    "Metrics exported to Prometheus",
                    "Auto-scaling triggered"
                ]
            
            logs.append({
                "timestamp": timestamp,
                "service": service,
                "region": region,
                "level": level,
                "message": random.choice(messages),
                "trace_id": f"trace-{random.randint(100000, 999999)}"
            })
        
        return sorted(logs, key=lambda x: x["timestamp"], reverse=True)

    def generate_realtime_update(self) -> Dict[str, Any]:
        """Generate a single real-time data update packet"""
        # Apply natural drift to 60% of services
        for service in random.sample(SERVICES, k=int(len(SERVICES) * 0.6)):
            for region in self.current_state[service]:
                self._apply_natural_drift(service, region)
        
        # Occasionally inject anomalies (demo purposes)
        if random.random() < 0.12:
            anomaly = self.inject_anomaly(severity=random.choice(["medium", "high"]))
            self.incident_history.append(anomaly)
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "metrics": self.get_current_metrics(),
            "logs": self.get_recent_logs(8),
            "active_incidents": len([i for i in self.incident_history if 
                                   (datetime.utcnow() - datetime.fromisoformat(i["timestamp"])).seconds < 300])
        }

    def get_health_summary(self) -> Dict:
        """High-level health dashboard data"""
        metrics = self.get_current_metrics()
        critical = sum(1 for m in metrics if m["status"] == "critical")
        warning = sum(1 for m in metrics if m["status"] == "warning")
        
        return {
            "total_services": len(SERVICES) * 3,
            "healthy": len(metrics) - critical - warning,
            "warning": warning,
            "critical": critical,
            "overall_status": "critical" if critical > 0 else ("warning" if warning > 2 else "healthy"),
            "last_updated": datetime.utcnow().isoformat()
        }


# Singleton instance for easy integration
simulator = GoogleScaleSimulator()


# ============================================
# FASTAPI INTEGRATION HELPERS
# ============================================

def get_simulator() -> GoogleScaleSimulator:
    """Dependency injection helper for FastAPI"""
    return simulator
