from pydantic import BaseModel
from datetime import datetime
from typing import Dict, Any, Optional

class MetricBase(BaseModel):
    service_id: str
    cpu_usage: float
    memory_usage: float
    request_rate: float
    error_rate: float
    latency: float
    active_connections: float
    db_pool_utilization: float
    temperature: float = 0.0

class MetricCreate(MetricBase):
    pass

class MetricResponse(MetricBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True

class LogEventBase(BaseModel):
    service_id: str
    level: str
    event_type: str
    trace_id: Optional[str] = None
    message: str
    log_metadata: Dict[str, Any] = {}

class LogEventCreate(LogEventBase):
    pass

class LogEventResponse(LogEventBase):
    id: int
    timestamp: datetime

    class Config:
        from_attributes = True
