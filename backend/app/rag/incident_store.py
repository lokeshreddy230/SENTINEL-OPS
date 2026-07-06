import datetime
import numpy as np
import logging
import json
from typing import List, Dict, Any
from app.rag.embeddings import RAGEmbeddings

logger = logging.getLogger("sentinelops.rag.store")

# Seeding list of 10 realistic historical incidents
HISTORICAL_INCIDENTS = [
    {
        "incident_id": "inc_hist_001",
        "title": "database_service connection pool exhaustion",
        "service": "database_service",
        "environment": "production",
        "service_version": "v1.4.2",
        "symptoms": "Database queries timing out. Active connections hit pool limit (20/20). Downstream services backing up.",
        "metrics_summary": "cpu_usage=85.0%, db_pool_utilization=100.0%, latency=4800ms",
        "log_signatures": "WARN - connection pool utilized at 100%. Blocked thread waiting for connection.",
        "verified_root_cause": "database_service Connection Pool Exhaustion",
        "successful_runbook": "increase_demo_pool_limit",
        "failed_actions": ["restart_service"],
        "rollback_result": "N/A",
        "resolution_summary": "DB pool saturated under order checkout traffic load. Resolved by increasing pool limit parameter.",
        "timestamp": "2026-06-10T12:00:00Z"
    },
    {
        "incident_id": "inc_hist_002",
        "title": "payment_service memory leak",
        "service": "payment_service",
        "environment": "production",
        "service_version": "v2.0.4",
        "symptoms": "Monotonic growth of memory usage on Payment Service without traffic increase, followed by OutOfMemory errors.",
        "metrics_summary": "memory_usage=92.5%, cpu_usage=22.0%, error_rate=15.0%",
        "log_signatures": "ERROR - java.lang.OutOfMemoryError: GC overhead limit exceeded",
        "verified_root_cause": "payment_service Memory Leak",
        "successful_runbook": "rolling_restart",
        "failed_actions": ["scale_service"],
        "rollback_result": "Success",
        "resolution_summary": "Slow leak in connection wrapper heap allocations. Restored baseline by rolling restart. Fix code leaks in v2.0.5.",
        "timestamp": "2026-06-12T15:30:00Z"
    },
    {
        "incident_id": "inc_hist_003",
        "title": "database_service crashed due to out of file descriptors",
        "service": "database_service",
        "environment": "production",
        "service_version": "v1.4.2",
        "symptoms": "Database Service is completely unresponsive. Downstream connection refused exceptions propagated up to API gateway.",
        "metrics_summary": "cpu_usage=0.0%, error_rate=100.0%, latency=5000ms",
        "log_signatures": "CRITICAL - Database engine panicked: out of file descriptors",
        "verified_root_cause": "database_service Crash",
        "successful_runbook": "restart_service",
        "failed_actions": ["increase_demo_pool_limit"],
        "rollback_result": "N/A",
        "resolution_summary": "Database daemon ran out of system file descriptors. Recovered service operation via force restart runbook.",
        "timestamp": "2026-06-15T09:12:00Z"
    },
    {
        "incident_id": "inc_hist_004",
        "title": "Auth Service token verification high latency",
        "service": "auth_service",
        "environment": "production",
        "service_version": "v1.1.0",
        "symptoms": "Gateway reports high latency on all authenticated requests. Auth service CPU usage rises.",
        "metrics_summary": "cpu_usage=94.0%, latency=2800ms, error_rate=5.0%",
        "log_signatures": "WARN - Token decrypt thread pool saturated. Task queue backlog > 1000.",
        "verified_root_cause": "auth_service CPU Saturation",
        "successful_runbook": "scale_service",
        "failed_actions": ["restart_service"],
        "rollback_result": "Success",
        "resolution_summary": "CPU crypto operations bottlenecked under login peak load. Scale replica count dynamically to load balance.",
        "timestamp": "2026-06-18T18:45:00Z"
    },
    {
        "incident_id": "inc_hist_005",
        "title": "Order Service lock timeout under transaction contention",
        "service": "order_service",
        "environment": "staging",
        "service_version": "v3.0.1",
        "symptoms": "Order processing API threads backing up. Lock acquisition timeout errors in logs.",
        "metrics_summary": "latency=3100ms, error_rate=18.0%, active_connections=15.0",
        "log_signatures": "ERROR - Database lock timeout: could not acquire write lock on orders table",
        "verified_root_cause": "order_service Transaction Contention",
        "successful_runbook": "activate_circuit_breaker",
        "failed_actions": ["rolling_restart"],
        "rollback_result": "Success",
        "resolution_summary": "Contention on order inventory row lock. Activated circuit breaker at gateway to shed traffic load and allow locks to release.",
        "timestamp": "2026-06-20T11:22:00Z"
    },
    {
        "incident_id": "inc_hist_006",
        "title": "API Gateway TLS connection leak",
        "service": "gateway",
        "environment": "production",
        "service_version": "v2.2.0",
        "symptoms": "Gateway stops accepting new HTTPS connections. Existing sessions work, new handshakes drop.",
        "metrics_summary": "active_connections=500.0, error_rate=30.0%, latency=120ms",
        "log_signatures": "WARN - Max open connections reached (500). Dropping incoming SYN packet.",
        "verified_root_cause": "gateway Connection Leak",
        "successful_runbook": "restart_service",
        "failed_actions": ["scale_service"],
        "rollback_result": "N/A",
        "resolution_summary": "Keep-alive sockets leaked due to idle timeout handler bug. Forcibly restarted container to clear socket table.",
        "timestamp": "2026-06-22T04:10:00Z"
    },
    {
        "incident_id": "inc_hist_007",
        "title": "Payment gateway HTTP 502 third-party outage",
        "service": "payment_service",
        "environment": "production",
        "service_version": "v2.0.4",
        "symptoms": "All payment authorizations fail. API responses show bad gateway from upstream stripe processors.",
        "metrics_summary": "error_rate=100.0%, latency=800ms, request_rate=45.0",
        "log_signatures": "ERROR - Third-party API call failed: HTTP 502 Bad Gateway from api.stripe.com",
        "verified_root_cause": "payment_service Downstream Outage",
        "successful_runbook": "activate_circuit_breaker",
        "failed_actions": ["restart_service"],
        "rollback_result": "Success",
        "resolution_summary": "Stripe API experienced global outage. Activated payment gateway circuit breaker to fail-fast checkout requests.",
        "timestamp": "2026-06-24T14:15:00Z"
    },
    {
        "incident_id": "inc_hist_008",
        "title": "database_service index fragmentation slow queries",
        "service": "database_service",
        "environment": "production",
        "service_version": "v1.4.2",
        "symptoms": "Gateway reporting slow page loads. Database CPU usage high but connections normal.",
        "metrics_summary": "cpu_usage=90.0%, latency=1200ms, db_pool_utilization=15.0%",
        "log_signatures": "INFO - Slow query logged (1150ms): SELECT * FROM orders WHERE user_id = ...",
        "verified_root_cause": "database_service Index Fragmentation",
        "successful_runbook": "scale_service",
        "failed_actions": ["increase_demo_pool_limit"],
        "rollback_result": "Success",
        "resolution_summary": "Orders query table index fragmentation. Scaled replicas to share read traffic query load while index rebuilt.",
        "timestamp": "2026-06-26T21:40:00Z"
    },
    {
        "incident_id": "inc_hist_009",
        "title": "Auth Service cache sync replication delay",
        "service": "auth_service",
        "environment": "production",
        "service_version": "v1.1.0",
        "symptoms": "User token validation fails intermittently on API Gateway immediately after login.",
        "metrics_summary": "error_rate=4.0%, latency=12ms, request_rate=60.0",
        "log_signatures": "WARN - Cache replication queue delayed. Lag count: 485 items.",
        "verified_root_cause": "auth_service Redis Lag",
        "successful_runbook": "restart_service",
        "failed_actions": ["scale_service"],
        "rollback_result": "N/A",
        "resolution_summary": "Token replication lag inside auth cache container. Restarted cache instance to force full snapshot sync.",
        "timestamp": "2026-06-28T08:05:00Z"
    },
    {
        "incident_id": "inc_hist_010",
        "title": "Order Service container task CPU throttling",
        "service": "order_service",
        "environment": "production",
        "service_version": "v3.0.1",
        "symptoms": "Order processing latencies rising. Container CPU throttled metrics alert in dashboard.",
        "metrics_summary": "cpu_usage=100.0%, latency=1500ms, error_rate=2.0%",
        "log_signatures": "WARN - CPU throttle limit reached. Docker cgroups throttling task container.",
        "verified_root_cause": "order_service CPU Throttling",
        "successful_runbook": "scale_service",
        "failed_actions": ["rolling_restart"],
        "rollback_result": "Success",
        "resolution_summary": "Order creation CPU limits throttled under peak campaign traffic. Scaled task count to resolve.",
        "timestamp": "2026-06-30T17:15:00Z"
    }
]

class IncidentStore:
    def __init__(self):
        self.chroma_client = None
        self.collection = None
        self._initialized = False
        self._cached_embeddings = {}

        # Precompute embeddings for all historical incidents for rapid fallback comparisons
        for inc in HISTORICAL_INCIDENTS:
            text = f"{inc['title']} {inc['symptoms']} {inc['log_signatures']}"
            self._cached_embeddings[inc["incident_id"]] = RAGEmbeddings.get_embedding(text)

        # Attempt to set up ChromaDB persistent storage
        try:
            import chromadb
            # Use local persistent ChromaDB storage in the workspace
            self.chroma_client = chromadb.PersistentClient(path="./chroma_db_store")
            self.collection = self.chroma_client.get_or_create_collection("incident_history")
            
            # Populate ChromaDB if empty
            if self.collection.count() == 0:
                ids = []
                documents = []
                embeddings = []
                metadatas = []
                
                for inc in HISTORICAL_INCIDENTS:
                    text_content = f"{inc['title']} {inc['symptoms']} {inc['log_signatures']}"
                    ids.append(inc["incident_id"])
                    documents.append(text_content)
                    embeddings.append(self._cached_embeddings[inc["incident_id"]])
                    
                    # Convert list metadata elements to JSON string to fit ChromaDB standards
                    meta = {k: json.dumps(v) if isinstance(v, list) else v for k, v in inc.items()}
                    metadatas.append(meta)
                    
                self.collection.add(
                    ids=ids,
                    documents=documents,
                    embeddings=embeddings,
                    metadatas=metadatas
                )
                logger.info(f"ChromaDB initialized and seeded with {len(HISTORICAL_INCIDENTS)} incident logs.")
            self._initialized = True
        except Exception as e:
            logger.warning(f"ChromaDB local setup skipped or encountered error: {e}. RAG memory will use embedding fallback.")

    def search_similar(self, query_text: str, service_filter: str = None, limit: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieves similar incidents from RAG memory using vector distance.
        """
        logger.info(f"Querying RAG memory for similar incidents: '{query_text}' (Service filter: {service_filter})")
        query_vector = RAGEmbeddings.get_embedding(query_text)
        
        # Method 1: If ChromaDB is initialized, use it
        if self._initialized and self.collection:
            try:
                where_clause = {}
                if service_filter:
                    where_clause = {"service": service_filter}
                    
                results = self.collection.query(
                    query_embeddings=[query_vector],
                    n_results=limit,
                    where=where_clause if service_filter else None
                )
                
                matched = []
                if results and "metadatas" in results and results["metadatas"]:
                    for idx, meta in enumerate(results["metadatas"][0]):
                        # Restore list representations
                        restored = {}
                        for k, v in meta.items():
                            if k in ["failed_actions"] and isinstance(v, str):
                                import json
                                try:
                                    restored[k] = json.loads(v)
                                except:
                                    restored[k] = v
                            else:
                                restored[k] = v
                        matched.append(restored)
                return matched
            except Exception as e:
                logger.error(f"ChromaDB search failed: {e}. Falling back to Python matcher.")

        # Method 2: Pure Python Cosine Similarity fallback using precomputed embeddings
        matches = []
        for inc in HISTORICAL_INCIDENTS:
            if service_filter and inc["service"] != service_filter:
                continue
                
            inc_vector = self._cached_embeddings[inc["incident_id"]]
            
            # Compute cosine similarity
            dot_product = np.dot(query_vector, inc_vector)
            norm_a = np.linalg.norm(query_vector)
            norm_b = np.linalg.norm(inc_vector)
            
            similarity = float(dot_product / (norm_a * norm_b)) if norm_a > 0 and norm_b > 0 else 0.0
            
            matches.append((similarity, inc))
            
        # Sort by similarity descending
        matches.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in matches[:limit]]

# Global singleton RAG incident store
incident_store = IncidentStore()
