import json
import logging
from typing import Dict, Any, List
from app.config import settings

logger = logging.getLogger("sentinelops.ai_service")

class AIService:
    @staticmethod
    def is_llm_configured() -> bool:
        provider = settings.LLM_PROVIDER.lower()
        if provider == "openai" and settings.OPENAI_API_KEY:
            return True
        if provider == "anthropic" and settings.ANTHROPIC_API_KEY:
            return True
        if provider == "groq" and settings.GROQ_API_KEY:
            return True
        return False

    @classmethod
    def analyze_incident(cls, incident_title: str, affected_service: str, logs: List[Dict[str, Any]], metrics: List[Dict[str, Any]], similar_incidents: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Orchestrates LLM query or fallback Demo Mode analysis.
        Returns a structured JSON response matching the Investigator Agent specification.
        """
        similar_incidents = similar_incidents or []
        
        if not cls.is_llm_configured():
            logger.info("LLM is not configured or set to demo. Using deterministic DEMO MODE.")
            return cls._get_demo_analysis(incident_title, affected_service, similar_incidents)
            
        provider = settings.LLM_PROVIDER.lower()
        prompt = cls._build_investigation_prompt(incident_title, affected_service, logs, metrics, similar_incidents)
        
        try:
            if provider == "openai":
                return cls._call_openai(prompt)
            elif provider == "anthropic":
                return cls._call_anthropic(prompt)
            elif provider == "groq":
                return cls._call_groq(prompt)
        except Exception as e:
            logger.error(f"LLM call failed with error: {e}. Falling back to DEMO MODE.")
            
        return cls._get_demo_analysis(incident_title, affected_service, similar_incidents)

    @classmethod
    def generate_report(cls, incident_id: str, title: str, timeline: List[Dict[str, Any]], root_cause: str, evidence: List[str], actions: List[Dict[str, Any]]) -> str:
        """
        Generates incident post-mortem report using LLM or demo fallback.
        """
        if not cls.is_llm_configured():
            return cls._get_demo_report(incident_id, title, timeline, root_cause, evidence, actions)
            
        provider = settings.LLM_PROVIDER.lower()
        prompt = f"""
        Generate a professional SRE post-mortem report for the following incident:
        Incident ID: {incident_id}
        Title: {title}
        Root Cause: {root_cause}
        Timeline: {json.dumps(timeline, indent=2)}
        Evidence: {json.dumps(evidence, indent=2)}
        Actions Executed: {json.dumps(actions, indent=2)}
        
        Provide the output in standard Markdown format. Include sections: Incident Overview, Detection & Timeline, Root Cause Analysis, Actions Taken, and Prevention Recommendations.
        """
        try:
            if provider == "openai":
                return cls._call_openai_text(prompt)
            elif provider == "anthropic":
                return cls._call_anthropic_text(prompt)
            elif provider == "groq":
                return cls._call_groq_text(prompt)
        except Exception as e:
            logger.error(f"LLM call for report failed: {e}. Using demo report.")
            
        return cls._get_demo_report(incident_id, title, timeline, root_cause, evidence, actions)

    @classmethod
    def _build_investigation_prompt(cls, incident_title: str, affected_service: str, logs: List[Dict[str, Any]], metrics: List[Dict[str, Any]], similar_incidents: List[Dict[str, Any]]) -> str:
        return f"""
        You are the SentinelOps SRE Incident Investigator.
        Investigate this incident: "{incident_title}" on service "{affected_service}".
        
        Here are the recent system metrics:
        {json.dumps(metrics, indent=2)}
        
        Here are the recent service logs:
        {json.dumps(logs, indent=2)}
        
        Here are similar historical incidents from RAG memory:
        {json.dumps(similar_incidents, indent=2)}
        
        You must output structured JSON ONLY. Do not include any explanation outside the JSON.
        The JSON structure MUST be:
        {{
          "summary": "High-level summary of the incident investigation.",
          "hypotheses": [
            {{
              "root_cause": "The root cause name (e.g. database connection pool exhaustion)",
              "confidence": 0.91,
              "evidence": ["Evidence point 1", "Evidence point 2"],
              "contradicting_evidence": []
            }}
          ],
          "recommended_hypothesis": "The most likely root cause from the hypotheses.",
          "similar_incidents": ["inc_similar_1", "inc_similar_2"]
        }}
        """

    @classmethod
    def _call_openai(cls, prompt: str) -> Dict[str, Any]:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    @classmethod
    def _call_openai_text(cls, prompt: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    @classmethod
    def _call_anthropic(cls, prompt: str) -> Dict[str, Any]:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        # Parse JSON from markdown response if present
        text = response.content[0].text
        return json.loads(text[text.find("{"):text.rfind("}")+1])

    @classmethod
    def _call_anthropic_text(cls, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        response = client.messages.create(
            model="claude-3-5-sonnet-20241022",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text

    @classmethod
    def _call_groq(cls, prompt: str) -> Dict[str, Any]:
        from openai import OpenAI
        client = OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)

    @classmethod
    def _call_groq_text(cls, prompt: str) -> str:
        from openai import OpenAI
        client = OpenAI(api_key=settings.GROQ_API_KEY, base_url="https://api.groq.com/openai/v1")
        response = client.chat.completions.create(
            model="mixtral-8x7b-32768",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content

    @classmethod
    def _get_demo_analysis(cls, incident_title: str, affected_service: str, similar_incidents: List[Dict[str, Any]]) -> Dict[str, Any]:
        title_lower = incident_title.lower()
        similar_ids = [item.get("incident_id", "inc_hist_001") for item in similar_incidents]
        
        if "pool" in title_lower or "connection" in title_lower or "database_service" in title_lower:
            return {
                "summary": "DEMO MODE: Analysis of telemetry shows API Gateway and Order Service backing up due to Payment Service timeouts, which trace back to database connection pool saturation on database_service.",
                "hypotheses": [
                    {
                        "root_cause": "database_service Connection Pool Exhaustion",
                        "confidence": 0.91,
                        "evidence": [
                            "database_service active_connections reached maximum pool size (20/20)",
                            "Database pool utilization is at 100.0%",
                            "Order Service database queries began timing out first",
                            "Upstream services (Gateway) followed with high latency within 4 seconds"
                        ],
                        "contradicting_evidence": []
                    },
                    {
                        "root_cause": "API Gateway Request Flood",
                        "confidence": 0.25,
                        "evidence": [
                            "Slight request rate spike at gateway"
                        ],
                        "contradicting_evidence": [
                            "DB pool saturated before request rate rose significantly"
                        ]
                    }
                ],
                "recommended_hypothesis": "database_service Connection Pool Exhaustion",
                "similar_incidents": similar_ids if similar_ids else ["inc_hist_001", "inc_hist_004"]
            }
            
        elif "leak" in title_lower or "memory" in title_lower:
            return {
                "summary": "DEMO MODE: The Payment Service memory usage exhibits monotonic EWMA growth without a corresponding traffic increase, indicating a slow heap memory leak.",
                "hypotheses": [
                    {
                        "root_cause": "payment_service Memory Leak",
                        "confidence": 0.88,
                        "evidence": [
                            "payment_service memory usage grew from 150MB to 980MB over 10 minutes",
                            "EWMA growth trend is highly positive (slope > 0.05)",
                            "Request rate remains flat at 45 req/sec"
                        ],
                        "contradicting_evidence": []
                    },
                    {
                        "root_cause": "Payment Service Traffic Spike",
                        "confidence": 0.10,
                        "evidence": [],
                        "contradicting_evidence": [
                            "Request rate is perfectly stable"
                        ]
                    }
                ],
                "recommended_hypothesis": "payment_service Memory Leak",
                "similar_incidents": similar_ids if similar_ids else ["inc_hist_002"]
            }
            
        elif "google" in title_lower or "servicecontrol" in title_lower or "api gateway crash loop" in title_lower:
            return {
                "summary": "DEMO MODE: Investigation reveals Google's API management system change rollout triggered an infinite crash loop in the ServiceControl component, preventing all ingress traffic at regional API Gateways.",
                "hypotheses": [
                    {
                        "root_cause": "Google Cloud API Gateway Crash Loop",
                        "confidence": 0.95,
                        "evidence": [
                            "ServiceControl component crash loop logged",
                            "Gateway request rate dropped to 0 req/sec",
                            "Incorrect API configuration rollout commit hash 'fc83a21' detected"
                        ],
                        "contradicting_evidence": []
                    }
                ],
                "recommended_hypothesis": "Google Cloud API Gateway Crash Loop",
                "similar_incidents": similar_ids if similar_ids else ["inc_hist_006"]
            }

        elif "cloudflare" in title_lower or "bot" in title_lower or "permission" in title_lower:
            return {
                "summary": "DEMO MODE: An unexpected database permission change triggered an automated feature file update for Bot Management, causing the file size to exceed system limits. Routing software on edge servers subsequently crashed.",
                "hypotheses": [
                    {
                        "root_cause": "Cloudflare Bot Management Database Outage",
                        "confidence": 0.93,
                        "evidence": [
                            "Bot Management feature file exceeds 50MB size limit",
                            "Auth Service error rate spiked to 65%",
                            "Database permission update failed to validate feature file thresholds"
                        ],
                        "contradicting_evidence": []
                    }
                ],
                "recommended_hypothesis": "Cloudflare Bot Management Database Outage",
                "similar_incidents": similar_ids if similar_ids else ["inc_hist_009"]
            }

        elif "aws" in title_lower or "dns" in title_lower or "dynamodb" in title_lower:
            return {
                "summary": "DEMO MODE: Automated DNS record updates failed for DynamoDB databases in region US-EAST-1, causing resolver cache corruption. Downstream applications failed to lookup database endpoints, leading to cascading transaction failures.",
                "hypotheses": [
                    {
                        "root_cause": "AWS DynamoDB DNS Cascading Failure",
                        "confidence": 0.94,
                        "evidence": [
                            "DNS lookup query failed for DynamoDB endpoints",
                            "Database Service reports 90% connection timeouts",
                            "Cascading timeouts propagated to Order Service and API Gateway"
                        ],
                        "contradicting_evidence": []
                    }
                ],
                "recommended_hypothesis": "AWS DynamoDB DNS Cascading Failure",
                "similar_incidents": similar_ids if similar_ids else ["inc_hist_003"]
            }

        else: # Cascading failure / other
            return {
                "summary": "DEMO MODE: Database Service crash has triggered connection failures at Order Service, which propagate upstream as timeout errors at the API Gateway.",
                "hypotheses": [
                    {
                        "root_cause": "database_service Crash",
                        "confidence": 0.95,
                        "evidence": [
                            "database_service health status changed to DOWN",
                            "Order Service logs indicate DB connection timeouts (100% fail)",
                            "Gateway response latency spike at 5000ms"
                        ],
                        "contradicting_evidence": []
                    }
                ],
                "recommended_hypothesis": "database_service Crash",
                "similar_incidents": similar_ids if similar_ids else ["inc_hist_003"]
            }

    @classmethod
    def _get_demo_report(cls, incident_id: str, title: str, timeline: List[Dict[str, Any]], root_cause: str, evidence: List[str], actions: List[Dict[str, Any]]) -> str:
        timeline_str = "\n".join([f"- **{evt.get('timestamp', '')}** [{evt.get('sender', '')}]: {evt.get('message', '')}" for evt in timeline])
        evidence_str = "\n".join([f"- {ev}" for ev in evidence])
        actions_str = "\n".join([f"- Executed runbook **{act.get('runbook', '')}** on **{act.get('target', '')}** (Status: {act.get('status', '')})" for act in actions])
        
        return f"""# SentinelOps Post-Mortem Report

**Incident ID**: `{incident_id}`  
**Title**: {title}  
**Root Cause**: `{root_cause}`  

---

## 1. Incident Overview
A system anomaly was detected by SentinelOps monitoring, culminating in a root-cause classification of `{root_cause}`. 
The system autonomously investigated and proposed remediation plans under safety constraints.

## 2. Detection & Timeline
{timeline_str}

## 3. Root Cause Analysis & Evidence
The AI Investigator agent correlated upstream delays and downstream error traces.
The primary indicators included:
{evidence_str}

## 4. Remediation Actions Taken
{actions_str}

## 5. Prevention Recommendations
1. Scale the database pool size limits or verify query index strategies to avoid query queuing.
2. Implement auto-circuit breaking at the Order Service to fail-fast and avoid thread-pool starvation.
3. Configure persistent health alerts with tighter EWMA variance thresholds for faster early warning.
"""
