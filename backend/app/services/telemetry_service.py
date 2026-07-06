from sqlalchemy.orm import Session
from app.models.metric import Metric, LogEvent
from app.models.service import Service
from app.schemas.metric import MetricCreate, LogEventCreate
from typing import List, Dict, Any
import datetime

class TelemetryService:
    @staticmethod
    def record_metric(db: Session, metric_in: MetricCreate) -> Metric:
        db_metric = Metric(
            service_id=metric_in.service_id,
            cpu_usage=metric_in.cpu_usage,
            memory_usage=metric_in.memory_usage,
            request_rate=metric_in.request_rate,
            error_rate=metric_in.error_rate,
            latency=metric_in.latency,
            active_connections=metric_in.active_connections,
            db_pool_utilization=metric_in.db_pool_utilization,
            temperature=metric_in.temperature,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(db_metric)
        db.commit()
        db.refresh(db_metric)
        return db_metric

    @staticmethod
    def record_log(db: Session, log_in: LogEventCreate) -> LogEvent:
        db_log = LogEvent(
            service_id=log_in.service_id,
            level=log_in.level,
            event_type=log_in.event_type,
            trace_id=log_in.trace_id,
            message=log_in.message,
            log_metadata=log_in.log_metadata,
            timestamp=datetime.datetime.utcnow()
        )
        db.add(db_log)
        db.commit()
        db.refresh(db_log)
        return db_log

    @staticmethod
    def get_live_metrics(db: Session) -> List[Metric]:
        # Returns the latest metric for each unique service
        services = db.query(Service.id).all()
        service_ids = [s[0] for s in services]
        
        live_metrics = []
        for service_id in service_ids:
            latest = db.query(Metric)\
                .filter(Metric.service_id == service_id)\
                .order_by(Metric.timestamp.desc())\
                .first()
            if latest:
                live_metrics.append(latest)
        return live_metrics

    @staticmethod
    def get_metric_history(db: Session, service_id: str, minutes: int = 15) -> List[Metric]:
        cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=minutes)
        return db.query(Metric)\
            .filter(Metric.service_id == service_id, Metric.timestamp >= cutoff)\
            .order_by(Metric.timestamp.asc())\
            .all()

    @staticmethod
    def get_recent_logs(db: Session, service_id: str = None, limit: int = 100) -> List[LogEvent]:
        query = db.query(LogEvent)
        if service_id:
            query = query.filter(LogEvent.service_id == service_id)
        return query.order_by(LogEvent.timestamp.desc()).limit(limit).all()
