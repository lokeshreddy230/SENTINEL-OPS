from sqlalchemy.orm import Session
from app.models.metric import Metric
import datetime
import numpy as np

def calculate_baseline(db: Session, service_id: str, field_name: str, lookback_minutes: int = 15) -> tuple[float, float]:
    """
    Retrieves and calculates the rolling mean and standard deviation for a given metric.
    Returns (mean, std_dev).
    """
    cutoff = datetime.datetime.utcnow() - datetime.timedelta(minutes=lookback_minutes)
    
    try:
        # Fetch the metric column dynamically using getattr
        metric_col = getattr(Metric, field_name)
        results = db.query(metric_col)\
            .filter(Metric.service_id == service_id, Metric.timestamp >= cutoff)\
            .all()
            
        vals = [float(r[0]) for r in results if r[0] is not None]
    except Exception:
        vals = []

    if len(vals) < 5:
        # Pinned baselines to handle clean cold-starts
        defaults = {
            "cpu_usage": 30.0,
            "memory_usage": 40.0,
            "request_rate": 65000.0,
            "error_rate": 0.02,
            "latency": 60.0,
            "active_connections": 15.0,
            "db_pool_utilization": 0.15
        }
        default_stds = {
            "cpu_usage": 15.0,
            "memory_usage": 15.0,
            "request_rate": 40000.0,
            "error_rate": 2.0,
            "latency": 35.0,
            "active_connections": 5.0,
            "db_pool_utilization": 0.10
        }
        return defaults.get(field_name, 10.0), default_stds.get(field_name, 5.0)
        
    std = float(np.std(vals))
    
    # Avoid division-by-zero or extremely tiny std ranges causing z-score explosions
    min_stds = {
        "cpu_usage": 5.0,
        "memory_usage": 5.0,
        "request_rate": 15.0,
        "error_rate": 2.0,
        "latency": 25.0,
        "active_connections": 3.0,
        "db_pool_utilization": 0.08
    }
    min_std = min_stds.get(field_name, 1.0)
    if std < min_std:
        std = min_std
        
    return float(np.mean(vals)), std
