import asyncio
import random
import datetime
import logging
import math
import json
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.websocket.manager import event_publisher
from app.services.scenario_state import scenario_state
from app.models.service import Service
from app.models.metric import Metric, LogEvent
from app.models.incident import Incident
from app.ml.anomaly_detector import AnomalyDetector
from app.correlation.event_correlator import EventCorrelator
from app.config import settings
from app.services.incident_service import IncidentService

logger = logging.getLogger("sentinelops.telemetry_generator")

# Target baseline metrics for healthy operation (including baseline temperature "temp" in °C)
HEALTHY_PROFILES = {
    "gateway": {"cpu": 15.0, "mem": 25.0, "req": 60.0, "err": 0.0, "lat": 45.0, "conn": 10.0, "db": 0.0, "temp": 38.0},
    "auth_service": {"cpu": 10.0, "mem": 20.0, "req": 60.0, "err": 0.0, "lat": 8.0, "conn": 5.0, "db": 0.0, "temp": 36.0},
    "order_service": {"cpu": 18.0, "mem": 24.0, "req": 60.0, "err": 0.0, "lat": 30.0, "conn": 8.0, "db": 0.0, "temp": 40.0},
    "payment_service": {"cpu": 12.0, "mem": 22.0, "req": 60.0, "err": 0.0, "lat": 15.0, "conn": 5.0, "db": 0.0, "temp": 38.0},
    "database_service": {"cpu": 8.0, "mem": 35.0, "req": 120.0, "err": 0.0, "lat": 3.0, "conn": 10.0, "db": 0.10, "temp": 45.0},
}

class TelemetryGenerator:
    def __init__(self):
        self._running = False
        self._task = None
        self._cooling_alert_sent = False

    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._loop())
            logger.info("Telemetry Generator background task started.")

    def stop(self):
        if self._running:
            self._running = False
            if self._task:
                self._task.cancel()
            logger.info("Telemetry Generator background task stopped.")

    async def _loop(self):
        while self._running:
            try:
                await self.generate_tick()
            except Exception as e:
                logger.error(f"Error in telemetry generation tick: {e}")
            await asyncio.sleep(2.0)

    async def generate_tick(self):
        db = SessionLocal()
        try:
            # Handle Google-Scale Real-Time Data Simulator datasource
            if settings.TELEMETRY_SOURCE == "google_scale":
                from app.services.google_scale_simulator import simulator
                
                # Check scenario recovery status to restore healthy baselines
                if scenario_state.is_recovering:
                    simulator._initialize_state()
                    scenario_state.reset()
                # Map demo scenarios to simulator anomalies
                elif scenario_state.active_scenario == "1":
                    simulator.inject_anomaly(service="payment-service", severity="high")
                elif scenario_state.active_scenario == "2":
                    simulator.inject_anomaly(service="search-service", severity="high")
                elif scenario_state.active_scenario == "3":
                    simulator.inject_anomaly(service="video-streaming", severity="high")

                update = simulator.generate_realtime_update()
                
                # Aggregate metrics per service across active regions
                metrics_by_service = {}
                for m in update["metrics"]:
                    s_id = m["service"]
                    if s_id not in metrics_by_service:
                        metrics_by_service[s_id] = []
                    metrics_by_service[s_id].append(m)
                
                for service_id, items in metrics_by_service.items():
                    avg_cpu = sum(item["cpu"] for item in items) / len(items)
                    avg_mem = sum(item["memory"] for item in items) / len(items)
                    sum_req = sum(item["request_rate"] for item in items)
                    avg_err = sum(item["error_rate"] for item in items) / len(items)
                    max_lat = max(item["latency_p99"] for item in items)
                    
                    # Update status in DB
                    db_service = db.query(Service).filter(Service.id == service_id).first()
                    if db_service:
                        status_list = [item["status"] for item in items]
                        if "critical" in status_list:
                            db_service.status = "critical"
                        elif "warning" in status_list:
                            db_service.status = "warning"
                        else:
                            db_service.status = "healthy"
                    
                    # Record Metric
                    db_metric = Metric(
                        service_id=service_id,
                        cpu_usage=round(avg_cpu, 2),
                        memory_usage=round(avg_mem, 2),
                        request_rate=sum_req,
                        error_rate=round(avg_err, 2),
                        latency=max_lat,
                        active_connections=len(items) * 5.0,
                        db_pool_utilization=0.15,
                        temperature=38.0,
                        timestamp=datetime.datetime.utcnow()
                    )
                    db.add(db_metric)
                
                # Ingest raw logs
                for log in update["logs"]:
                    db_log = LogEvent(
                        service_id=log["service"],
                        level=log["level"],
                        event_type="general",
                        trace_id=log["trace_id"],
                        message=f"[{log['region']}] {log['message']}",
                        log_metadata={"region": log["region"]},
                        timestamp=datetime.datetime.fromisoformat(log["timestamp"])
                    )
                    db.add(db_log)
                
                db.commit()
                
                # Run AI anomaly detection and SRE incident correlation pipeline
                for service_id in metrics_by_service.keys():
                    m = db.query(Metric).filter(Metric.service_id == service_id).order_by(Metric.timestamp.desc()).first()
                    if m:
                        anomalies = AnomalyDetector.detect_anomalies(db, service_id, m)
                        for anomaly in anomalies:
                            await event_publisher.publish("anomaly_detected", anomaly)
                            await EventCorrelator.correlate_anomaly(db, anomaly)
                
                # Publish individual service metric updates over standard SSE channel
                for service_id in metrics_by_service.keys():
                    m = db.query(Metric).filter(Metric.service_id == service_id).order_by(Metric.timestamp.desc()).first()
                    if m:
                        await event_publisher.publish("telemetry", {
                            "service_id": m.service_id,
                            "cpu_usage": m.cpu_usage,
                            "memory_usage": m.memory_usage,
                            "request_rate": m.request_rate,
                            "error_rate": m.error_rate,
                            "latency": m.latency,
                            "active_connections": m.active_connections,
                            "db_pool_utilization": m.db_pool_utilization,
                            "temperature": m.temperature,
                            "timestamp": m.timestamp.isoformat()
                        })
                return

            # Fluctuate state based on current scenario
            self._process_scenarios(db)

            # Generate random correlated trace_id for request flows in this tick
            trace_id = f"trace_{random.randint(100000, 999999)}"

            # Calculate time-of-day traffic factor simulating diurnal cycles (Google Cluster Traces)
            hour = datetime.datetime.utcnow().hour
            diurnal_factor = 1.0 + 0.3 * math.sin((hour - 8) * math.pi / 12)

            for service_id, profile in HEALTHY_PROFILES.items():
                # Read dynamic service status from DB
                db_service = db.query(Service).filter(Service.id == service_id).first()
                if not db_service:
                    continue

                # Fetch live metrics from Prometheus if configured
                prom_metrics = {}
                if settings.TELEMETRY_SOURCE == "prometheus":
                    try:
                        from app.services.prometheus_collector import PrometheusCollector
                        prom_metrics = await PrometheusCollector.get_service_metrics(service_id)
                    except Exception as e:
                        logger.error(f"Error querying Prometheus metrics for {service_id}: {e}")

                # Calculate metrics with diurnal cycle fluctuations, falling back to simulation if no value returned
                cpu = prom_metrics.get("cpu_usage")
                if cpu is None:
                    cpu = (profile["cpu"] * diurnal_factor) + random.uniform(-1.0, 1.0)

                mem = prom_metrics.get("memory_usage")
                if mem is None:
                    mem = profile["mem"] + random.uniform(-0.5, 0.5)

                req = prom_metrics.get("request_rate")
                if req is None:
                    req = (profile["req"] * diurnal_factor) + random.uniform(-2.0, 2.0)

                err = prom_metrics.get("error_rate")
                if err is None:
                    err = profile["err"]

                lat = prom_metrics.get("latency")
                if lat is None:
                    lat = profile["lat"] + random.uniform(-1.5, 1.5)

                conn = prom_metrics.get("active_connections")
                if conn is None:
                    conn = int(profile["conn"] * diurnal_factor) + random.randint(-1, 1)
                else:
                    conn = int(conn)

                db_util = prom_metrics.get("db_pool_utilization")
                if db_util is None:
                    db_util = profile["db"]

                temp = profile["temp"] + random.uniform(-0.8, 0.8)

                # Apply Scenario 1 (DB Connection Pool Exhaustion)
                if scenario_state.active_scenario == "1":
                    if not scenario_state.is_recovering:
                        # Escalating failure
                        scenario_state.db_pool_utilization = min(1.0, scenario_state.db_pool_utilization + 0.15)
                        
                        if service_id == "database_service":
                            db_util = scenario_state.db_pool_utilization
                            if db_util >= 0.8:
                                lat = 4500.0 + random.uniform(-200.0, 200.0)
                                cpu = 95.0 + random.uniform(-2.0, 2.0)
                                err = 10.0
                                # Heat spikes as database CPU utilization maxes out
                                temp = 45.0 + (scenario_state.db_pool_utilization * 42.0) + random.uniform(-1.0, 1.0)
                        elif service_id in ["order_service"]:
                            if scenario_state.db_pool_utilization >= 0.6:
                                lat = 4000.0 + random.uniform(-200.0, 200.0)
                                err = 25.0
                        elif service_id == "gateway":
                            if scenario_state.db_pool_utilization >= 0.8:
                                lat = 5000.0 + random.uniform(-100.0, 100.0)
                                err = 45.0
                    else:
                        # Resolving
                        time_since_rec = (datetime.datetime.utcnow() - scenario_state.recovery_started_at).total_seconds()
                        if time_since_rec > 6.0:
                            scenario_state.recovered = True
                            scenario_state.db_pool_utilization = 0.10
                            db_service.status = "healthy"
                            db.commit()
                            self._cooling_alert_sent = False

                # Apply Scenario 2 (Memory Leak)
                elif scenario_state.active_scenario == "2":
                    if not scenario_state.is_recovering:
                        scenario_state.memory_leak_growth += 6.5
                        if service_id == "payment_service":
                            mem = profile["mem"] + scenario_state.memory_leak_growth
                            if mem > 85.0:
                                # Start failing once memory is too high
                                err = min(90.0, (mem - 85.0) * 4)
                                lat = profile["lat"] * 3
                    else:
                        # Resolving
                        time_since_rec = (datetime.datetime.utcnow() - scenario_state.recovery_started_at).total_seconds()
                        if time_since_rec > 6.0:
                            scenario_state.recovered = True
                            scenario_state.memory_leak_growth = 0.0
                            db_service.status = "healthy"
                            db.commit()

                # Apply Scenario 3 (Cascading Failure)
                elif scenario_state.active_scenario == "3":
                    if not scenario_state.is_recovering:
                        if service_id == "database_service":
                            db_service.status = "critical"
                            cpu, mem, req, err, lat, conn, db_util = 0.0, 0.0, 0.0, 100.0, 0.0, 0, 0.0
                            temp = 20.0 # system cooled down due to crash/power off
                        elif service_id == "order_service":
                            err = 100.0
                            lat = 5000.0
                        elif service_id == "gateway":
                            err = 95.0
                            lat = 5000.0
                    else:
                        # Resolving
                        time_since_rec = (datetime.datetime.utcnow() - scenario_state.recovery_started_at).total_seconds()
                        if time_since_rec > 6.0:
                            scenario_state.recovered = True
                            db_service.status = "healthy"
                            db.commit()

                # Apply Scenario 4 (Google Cloud API Gateway Crash Loop - June 12, 2025)
                elif scenario_state.active_scenario == "4":
                    if not scenario_state.is_recovering:
                        if service_id == "gateway":
                            cpu = 98.0 + random.uniform(-1.0, 1.0)
                            req = 0.0
                            err = 100.0
                            lat = 5000.0
                            temp = 65.0
                    else:
                        # Resolving
                        time_since_rec = (datetime.datetime.utcnow() - scenario_state.recovery_started_at).total_seconds()
                        if time_since_rec > 6.0:
                            scenario_state.recovered = True
                            db_service.status = "healthy"
                            db.commit()

                # Apply Scenario 5 (Cloudflare Bot Management DB Permission Outage - November 18, 2025)
                elif scenario_state.active_scenario == "5":
                    if not scenario_state.is_recovering:
                        if service_id == "auth_service":
                            cpu = 92.0 + random.uniform(-1.0, 1.0)
                            err = 65.0
                            lat = 3200.0
                        elif service_id == "gateway":
                            err = 30.0
                            lat = 1200.0
                    else:
                        # Resolving
                        time_since_rec = (datetime.datetime.utcnow() - scenario_state.recovery_started_at).total_seconds()
                        if time_since_rec > 6.0:
                            scenario_state.recovered = True
                            db_service.status = "healthy"
                            db.commit()

                # Apply Scenario 6 (AWS DynamoDB DNS Cascading Failure - October 20, 2025)
                elif scenario_state.active_scenario == "6":
                    if not scenario_state.is_recovering:
                        if service_id == "database_service":
                            err = 90.0
                            lat = 5000.0
                        elif service_id == "order_service":
                            err = 80.0
                            lat = 4500.0
                        elif service_id == "gateway":
                            err = 40.0
                            lat = 3000.0
                    else:
                        # Resolving
                        time_since_rec = (datetime.datetime.utcnow() - scenario_state.recovery_started_at).total_seconds()
                        if time_since_rec > 6.0:
                            scenario_state.recovered = True
                            db_service.status = "healthy"
                            db.commit()

                # Save metrics to DB (with new temperature metric)
                metric_entry = Metric(
                    service_id=service_id,
                    cpu_usage=max(0.0, cpu),
                    memory_usage=max(0.0, mem),
                    request_rate=max(0.0, req),
                    error_rate=max(0.0, min(100.0, err)),
                    latency=max(0.0, lat),
                    active_connections=max(0, conn),
                    db_pool_utilization=max(0.0, min(1.0, db_util)),
                    temperature=max(0.0, temp),
                    timestamp=datetime.datetime.utcnow()
                )
                db.add(metric_entry)

                # Broadcast live telemetry over SSE (including temperature)
                await event_publisher.publish("telemetry", {
                    "service_id": service_id,
                    "cpu_usage": metric_entry.cpu_usage,
                    "memory_usage": metric_entry.memory_usage,
                    "request_rate": metric_entry.request_rate,
                    "error_rate": metric_entry.error_rate,
                    "latency": metric_entry.latency,
                    "active_connections": metric_entry.active_connections,
                    "db_pool_utilization": metric_entry.db_pool_utilization,
                    "temperature": metric_entry.temperature,
                    "timestamp": metric_entry.timestamp.isoformat()
                })

                # Watch database temperature and send alerts if overheating (>80°C)
                if service_id == "database_service" and temp > 80.0:
                    if not self._cooling_alert_sent:
                        self._cooling_alert_sent = True
                        active_inc = db.query(Incident).filter(
                            Incident.service_id == "database_service", 
                            Incident.status != "resolved"
                        ).order_by(Incident.detected_at.desc()).first()
                        
                        thermal_msg = f"Thermal Alert: database_service temperature critical ({temp:.1f}°C). Main cooler overloaded. Deploying liquid backup grids!"
                        
                        if active_inc:
                            IncidentService.add_event(
                                db,
                                incident_id=active_inc.id,
                                sender="CoolingSystem",
                                message=thermal_msg
                            )
                            # Broadcast over SSE as an incident timeline event
                            await event_publisher.publish("incident_event", {
                                "incident_id": active_inc.id,
                                "sender": "CoolingSystem",
                                "message": thermal_msg,
                                "type": "incident_update"
                            })
                        else:
                            await event_publisher.publish("incident_event", {
                                "incident_id": "thermal_warning",
                                "sender": "CoolingSystem",
                                "message": thermal_msg,
                                "type": "incident_update"
                            })

                # Generate logs
                self._generate_logs_for_service(db, service_id, err, trace_id)

                # Run anomaly detection pipeline
                anomalies = AnomalyDetector.detect_anomalies(db, service_id, metric_entry)
                for anomaly in anomalies:
                    # Broadcast anomaly over SSE
                    await event_publisher.publish("anomaly_detected", anomaly)
                    # Correlate anomaly to existing incident or create a new one
                    await EventCorrelator.correlate_anomaly(db, anomaly)

            # Calculate global Datacenter telemetry (Google cluster trace standards)
            # Find max service temperature for cooling regulation
            temps = [profile["temp"] for profile in HEALTHY_PROFILES.values()]
            max_temp = max(temps)
            if scenario_state.active_scenario == "1" and not scenario_state.is_recovering:
                max_temp = 45.0 + (scenario_state.db_pool_utilization * 42.0)
            
            # Base IT Power is roughly proportional to sum of CPU usages
            it_power_kw = 120.0 * diurnal_factor + random.uniform(-5.0, 5.0)
            if scenario_state.active_scenario == "1" and not scenario_state.is_recovering:
                it_power_kw += 65.0 # extra power from database stress loop
            
            # PUE calculation: cooling overhead grows with higher max_temp
            # Google average baseline PUE is ~1.10. Under overheat scenario, we scale to ~1.19
            temp_overhead = max(0.0, (max_temp - 40.0) * 0.0025)
            pue = 1.09 + temp_overhead + random.uniform(-0.005, 0.005)
            cooling_power_kw = it_power_kw * (pue - 1.0)

            # Broadcast datacenter metrics
            await event_publisher.publish("telemetry", {
                "service_id": "datacenter",
                "cpu_usage": 0.0,
                "memory_usage": 0.0,
                "request_rate": 0.0,
                "error_rate": 0.0,
                "latency": 0.0,
                "active_connections": 0,
                "db_pool_utilization": 0.0,
                "temperature": max_temp,
                "timestamp": datetime.datetime.utcnow().isoformat(),
                "pue": pue,
                "cooling_power_kw": cooling_power_kw,
                "it_power_kw": it_power_kw,
                "diurnal_factor": diurnal_factor,
            })

            db.commit()
        finally:
            db.close()

    def _process_scenarios(self, db: Session):
        """
        Adjust service status fields dynamically in response to scenario activations.
        """
        if scenario_state.active_scenario == "1":
            db_db = db.query(Service).filter(Service.id == "database_service").first()
            db_order = db.query(Service).filter(Service.id == "order_service").first()
            db_gw = db.query(Service).filter(Service.id == "gateway").first()
            
            if scenario_state.db_pool_utilization >= 0.95 and not scenario_state.is_recovering:
                if db_db and db_db.status != "critical":
                    db_db.status = "critical"
                    db_order.status = "warning"
                    db_gw.status = "warning"
                    db.commit()
                    
        elif scenario_state.active_scenario == "2":
            db_pay = db.query(Service).filter(Service.id == "payment_service").first()
            if db_pay and not scenario_state.is_recovering:
                current_mem = HEALTHY_PROFILES["payment_service"]["mem"] + scenario_state.memory_leak_growth
                if current_mem >= 75.0 and db_pay.status != "critical":
                    db_pay.status = "critical"
                    db.commit()
                elif current_mem >= 50.0 and db_pay.status == "healthy":
                    db_pay.status = "warning"
                    db.commit()

        elif scenario_state.active_scenario == "3":
            db_db = db.query(Service).filter(Service.id == "database_service").first()
            db_order = db.query(Service).filter(Service.id == "order_service").first()
            db_gw = db.query(Service).filter(Service.id == "gateway").first()
            
            if not scenario_state.is_recovering:
                if db_db and db_db.status != "critical":
                    db_db.status = "critical"
                if db_order and db_order.status != "critical":
                    db_order.status = "critical"
                if db_gw and db_gw.status != "warning":
                    db_gw.status = "warning"
                db.commit()

        elif scenario_state.active_scenario == "4":
            db_gw = db.query(Service).filter(Service.id == "gateway").first()
            if db_gw and not scenario_state.is_recovering:
                if db_gw.status != "critical":
                    db_gw.status = "critical"
                    db.commit()

        elif scenario_state.active_scenario == "5":
            db_auth = db.query(Service).filter(Service.id == "auth_service").first()
            db_gw = db.query(Service).filter(Service.id == "gateway").first()
            if not scenario_state.is_recovering:
                if db_auth and db_auth.status != "critical":
                    db_auth.status = "critical"
                if db_gw and db_gw.status != "warning":
                    db_gw.status = "warning"
                db.commit()

        elif scenario_state.active_scenario == "6":
            db_db = db.query(Service).filter(Service.id == "database_service").first()
            db_order = db.query(Service).filter(Service.id == "order_service").first()
            db_gw = db.query(Service).filter(Service.id == "gateway").first()
            if not scenario_state.is_recovering:
                if db_db and db_db.status != "critical":
                    db_db.status = "critical"
                if db_order and db_order.status != "critical":
                    db_order.status = "critical"
                if db_gw and db_gw.status != "warning":
                    db_gw.status = "warning"
                db.commit()

    def _generate_logs_for_service(self, db: Session, service_id: str, error_rate: float, trace_id: str):
        from app.services.redaction import redact_secrets
        levels = ["INFO", "INFO", "INFO", "INFO", "INFO"]
        msg = f"Request processed successfully - trace_id={trace_id}"
        event_type = "request_processed"

        # Under failure
        if error_rate > 0.0:
            if random.random() < (error_rate / 100.0):
                levels = ["ERROR"]
                event_type = "request_failed"
                if scenario_state.active_scenario == "1":
                    msg = f"Database query failed: Connection pool exhausted - trace_id={trace_id}"
                elif scenario_state.active_scenario == "2":
                    msg = f"Payment processing failed: OutOfMemoryError in garbage collector - trace_id={trace_id}"
                elif scenario_state.active_scenario == "3":
                    msg = f"Database unavailable: Connection refused by database_service:5432 - trace_id={trace_id}"
                elif scenario_state.active_scenario == "4":
                    levels = ["CRITICAL"]
                    msg = f"CRITICAL - ServiceControl error: crash loop detected due to incorrect API configuration rollout - trace_id={trace_id}"
                    event_type = "crash_loop"
                elif scenario_state.active_scenario == "5":
                    msg = f"ERROR - Bot Management config load failed: feature file exceeds 50MB limit after DB permission change - trace_id={trace_id}"
                    event_type = "config_error"
                elif scenario_state.active_scenario == "6":
                    msg = f"ERROR - DNS lookup failed for DynamoDB: host not found - trace_id={trace_id}"
                    event_type = "dns_error"
                else:
                    msg = f"Internal system timeout error - trace_id={trace_id}"

        level = random.choice(levels)
        log_entry = LogEvent(
            service_id=service_id,
            level=level,
            event_type=event_type,
            trace_id=trace_id,
            message=redact_secrets(msg),
            log_metadata={"latency_ms": random.uniform(5.0, 15.0), "error_rate": error_rate},
            timestamp=datetime.datetime.utcnow()
        )
        db.add(log_entry)

# Global singleton
telemetry_generator = TelemetryGenerator()
