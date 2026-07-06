import numpy as np
from sqlalchemy.orm import Session
from app.ml.baseline import calculate_baseline
from app.models.metric import Metric
from sklearn.ensemble import IsolationForest
import logging

logger = logging.getLogger("sentinelops.anomaly_detector")

class AnomalyDetector:
    @staticmethod
    def calculate_z_score(val: float, mean: float, std: float) -> float:
        if std == 0:
            return 0.0
        return (val - mean) / std

    @staticmethod
    def calculate_ewma(values: list[float], alpha: float = 0.2) -> float:
        if not values:
            return 0.0
        ewma = values[0]
        for val in values[1:]:
            ewma = alpha * val + (1 - alpha) * ewma
        return ewma

    @classmethod
    def detect_anomalies(cls, db: Session, service_id: str, current_metric: Metric) -> list[dict]:
        """
        Analyzes the latest metric entry for a service across all key fields.
        Returns a list of anomaly dictionaries if detected.
        """
        anomaly_events = []
        fields_to_check = [
            "cpu_usage", "memory_usage", "request_rate", "error_rate", "latency", 
            "active_connections", "db_pool_utilization"
        ]

        # Fetch recent historical values for EWMA calculations (last 20 entries)
        recent_metrics = db.query(Metric)\
            .filter(Metric.service_id == service_id)\
            .order_by(Metric.timestamp.desc())\
            .limit(20)\
            .all()
            
        recent_metrics.reverse()  # Chronological order

        for field in fields_to_check:
            val = getattr(current_metric, field)
            mean, std = calculate_baseline(db, service_id, field)
            
            # Z-Score check
            z = cls.calculate_z_score(val, mean, std)
            
            # EWMA check
            hist_vals = [getattr(m, field) for m in recent_metrics]
            ewma_val = cls.calculate_ewma(hist_vals)
            
            # Flag anomaly if Z-Score exceeds threshold (3.0 for standard metrics)
            is_anomaly = False
            severity = "LOW"
            anomaly_score = abs(z) / 3.0  # Scale z-score for simple score representation

            # Special baseline rules for error rates and db utilization
            if field == "error_rate" and val > 1.0:
                is_anomaly = True
                severity = "HIGH" if val > 20.0 else "MEDIUM"
                if val > 80.0:
                    severity = "CRITICAL"
            elif field == "db_pool_utilization" and val >= 0.95:
                is_anomaly = True
                severity = "CRITICAL"
            elif abs(z) > 3.0:
                is_anomaly = True
                if abs(z) > 5.0:
                    severity = "CRITICAL" if field in ["latency", "cpu_usage"] else "HIGH"
                else:
                    severity = "MEDIUM"

            if is_anomaly:
                trend = "increasing" if val > mean else "decreasing"
                anomaly_events.append({
                    "is_anomaly": True,
                    "anomaly_score": min(1.0, anomaly_score),
                    "affected_metric": field,
                    "service": service_id,
                    "severity": severity,
                    "baseline_value": mean,
                    "current_value": val,
                    "trend": trend,
                    "timestamp": current_metric.timestamp.isoformat()
                })

        # Run Isolation Forest for multivariate anomaly detection
        if len(recent_metrics) >= 15:
            try:
                X_train = []
                for m in recent_metrics:
                    X_train.append([
                        m.cpu_usage, m.memory_usage, m.request_rate, 
                        m.error_rate, m.latency, m.active_connections, m.db_pool_utilization
                    ])
                
                # contamination controls expected fraction of outliers (10%)
                clf = IsolationForest(contamination=0.1, random_state=42)
                clf.fit(X_train)
                
                curr_vec = [[
                    current_metric.cpu_usage, current_metric.memory_usage, current_metric.request_rate,
                    current_metric.error_rate, current_metric.latency, current_metric.active_connections,
                    current_metric.db_pool_utilization
                ]]
                
                prediction = clf.predict(curr_vec)[0]
                if prediction == -1:
                    logger.info(f"Multivariate Isolation Forest flagged anomaly on service {service_id}")
                    # If Z-score did not catch it, add a low/medium multivariate alert
                    if not anomaly_events:
                        anomaly_events.append({
                            "is_anomaly": True,
                            "anomaly_score": 0.80,
                            "affected_metric": "multivariate_signature",
                            "service": service_id,
                            "severity": "MEDIUM",
                            "baseline_value": 0.0,
                            "current_value": 1.0,
                            "trend": "abnormal_cluster",
                            "timestamp": current_metric.timestamp.isoformat()
                        })
            except Exception as e:
                logger.error(f"Error executing Isolation Forest: {e}")

        return anomaly_events
