from sqlalchemy import Column, Integer, String, Float, DateTime, JSON
from app.database import Base
import datetime

class Metric(Base):
    __tablename__ = "metrics"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    service_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    cpu_usage = Column(Float, default=0.0)
    memory_usage = Column(Float, default=0.0)
    request_rate = Column(Float, default=0.0)
    error_rate = Column(Float, default=0.0)
    latency = Column(Float, default=0.0)
    active_connections = Column(Float, default=0.0)
    db_pool_utilization = Column(Float, default=0.0)
    temperature = Column(Float, default=0.0)

class LogEvent(Base):
    __tablename__ = "log_events"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    service_id = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    level = Column(String, index=True, nullable=False)  # INFO, WARN, ERROR
    event_type = Column(String, index=True, nullable=False)
    trace_id = Column(String, index=True, nullable=True)
    message = Column(String, nullable=False)
    log_metadata = Column(JSON, default=dict)
