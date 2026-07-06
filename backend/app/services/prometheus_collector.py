import logging
import httpx
from typing import Optional, Dict
from app.config import settings

logger = logging.getLogger("sentinelops.prometheus_collector")

class PrometheusCollector:
    @staticmethod
    async def fetch_metric_value(query: str) -> Optional[float]:
        """
        Sends query to Prometheus REST API and parses the first float result.
        Returns None if Prometheus is offline or query returns no results.
        """
        url = f"{settings.PROMETHEUS_URL.rstrip('/')}/api/v1/query"
        try:
            async with httpx.AsyncClient(timeout=1.5) as client:
                response = await client.get(url, params={"query": query})
                if response.status_code == 200:
                    data = response.json()
                    if data.get("status") == "success":
                        results = data.get("data", {}).get("result", [])
                        if results:
                            # Standard prometheus result format:
                            # "value": [timestamp, "value_string"]
                            val_str = results[0].get("value", [None, None])[1]
                            if val_str is not None:
                                return float(val_str)
        except httpx.RequestError as e:
            # Silently log warning on first connection refusal
            logger.warning(f"Connection to Prometheus failed: {e}. Falling back to simulation mode.")
        except Exception as e:
            logger.error(f"Error parsing Prometheus response for query '{query}': {e}")
        return None

    @classmethod
    async def get_service_metrics(cls, service_id: str) -> Dict[str, Optional[float]]:
        """
        Fetches core SRE metrics (cpu, memory, request rate, error rate, latency, etc.)
        for a specific service ID from Prometheus.
        """
        # Formulate standard node-exporter / cadvisor query schemas
        queries = {
            "cpu_usage": f'sum(rate(container_cpu_usage_seconds_total{{container=~".*{service_id}.*"}}[1m])) * 100',
            "memory_usage": f'sum(container_memory_working_set_bytes{{container=~".*{service_id}.*"}}) / 1024 / 1024', # MB
            "request_rate": f'sum(rate(http_requests_total{{service=~".*{service_id}.*"}}[1m]))',
            "error_rate": f'sum(rate(http_requests_total{{service=~".*{service_id}.*", status=~"5.."}}[1m])) / (sum(rate(http_requests_total{{service=~".*{service_id}.*"}}[1m])) + 0.001) * 100',
            "latency": f'histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{{service=~".*{service_id}.*"}}[5m])) by (le)) * 1000', # ms
            "active_connections": f'sum(http_active_connections{{service=~".*{service_id}.*"}})',
            "db_pool_utilization": f'database_pool_utilization{{service=~".*{service_id}.*"}}'
        }

        # Query all fields
        results = {}
        for key, q in queries.items():
            results[key] = await cls.fetch_metric_value(q)
            
        return results
