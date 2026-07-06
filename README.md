<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Node.js-18+-339933?logo=node.js&logoColor=white" alt="Node.js" />
  <img src="https://img.shields.io/badge/FastAPI-0.109+-009688?logo=fastapi&logoColor=white" alt="FastAPI" />
  <img src="https://img.shields.io/badge/Next.js-15+-000000?logo=next.js&logoColor=white" alt="Next.js" />
  <img src="https://img.shields.io/badge/Docker-Ready-2496ED?logo=docker&logoColor=white" alt="Docker" />
  <img src="https://img.shields.io/badge/License-MIT-yellow" alt="License" />
</p>

# 🛡️ SentinelOps

### Autonomous AI Agent for Incident Response & Self-Healing Infrastructure

SentinelOps is a production-grade SRE command center that monitors Google-scale microservices in real time, detects anomalies using ML (Z-Score + Isolation Forest), correlates alerts via topological dependency matching, runs multi-agent investigation workflows via **LangGraph**, proposes & executes runbooks with safety policies, verifies recovery, and compiles automated post-mortem reports.

---

## ⚡ Quick Start

### Option A — Docker Compose (Recommended)

```bash
git clone https://github.com/lokeshreddy230/SENTINEL-OPS.git
cd SENTINEL-OPS

# Spin up Postgres, Redis, Backend, and Frontend
docker-compose up --build -d
```

| Interface | URL |
|---|---|
| 🖥️ Operations Dashboard | `http://localhost:3000` |
| 📚 API Swagger Docs | `http://localhost:8000/docs` |
| 📡 SSE Event Stream | `http://localhost:8000/api/events/stream` |

### Option B — Local Development (No Docker)

```bash
# 1. Clone
git clone https://github.com/lokeshreddy230/SENTINEL-OPS.git
cd SENTINEL-OPS

# 2. Setup environment
cp .env.example backend/.env

# 3. Backend
cd backend
pip install -r requirements.txt
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# 4. Frontend (new terminal)
cd frontend
npm install
npm run dev
```

> **Note:** Local mode uses SQLite by default — no PostgreSQL or Redis required.

---

## 🏗️ Architecture

```
Simulated Infrastructure (Google-Scale 9-Service Mesh)
        ↓
Metrics + Logs Ingestion (2s intervals)
        ↓
Anomaly Detection (Z-Score + Isolation Forest + EWMA)
        ↓
Event Correlation (Topological Dependency Matching)
        ↓
Incident Dispatch
        ↓
AI Multi-Agent Graph (LangGraph: Investigator → Remediator → Policy)
        ↓
RAG Similar-Incident Memory Search (ChromaDB)
        ↓
Runbook Proposal & Parameter Validation
        ↓
Operator Authorization Await / Auto-execution
        ↓
Runbook Execution & Verification (Before/After Telemetry Check)
        ↓
Automatic Rollback (If Verification Fails)
        ↓
Reporter Agent Post-Mortem Generation
```

---

## 🛠️ Technology Stack

| Layer | Technologies |
|---|---|
| **Backend** | Python 3.11+, FastAPI, SQLAlchemy, SQLite/PostgreSQL, scikit-learn, ChromaDB, LangGraph, LangChain |
| **Frontend** | Next.js 15+, TypeScript, React 19, Tailwind CSS v4, Recharts, Lucide Icons |
| **ML/AI** | Z-Score Anomaly Detection, Isolation Forest, EWMA Trends, RAG Memory Search |
| **Infrastructure** | Docker, Docker Compose, SSE Real-Time Streaming |

---

## 📁 Project Structure

```
SENTINEL-OPS/
├── backend/
│   ├── app/
│   │   ├── agents/           # LangGraph multi-agent orchestration
│   │   │   ├── orchestrator.py
│   │   │   ├── investigator.py
│   │   │   └── remediator.py
│   │   ├── api/              # FastAPI route handlers
│   │   │   ├── incidents.py
│   │   │   ├── approvals.py
│   │   │   ├── reports.py
│   │   │   ├── metrics.py
│   │   │   ├── stream.py     # SSE event stream
│   │   │   └── demo.py       # Failure scenario injection
│   │   ├── ml/               # Machine learning pipeline
│   │   │   ├── anomaly_detector.py
│   │   │   └── baseline.py
│   │   ├── correlation/      # Alert correlation engine
│   │   ├── models/           # SQLAlchemy ORM models
│   │   ├── remediation/      # Executor, verifier, rollback
│   │   ├── rag/              # ChromaDB vector memory
│   │   ├── services/         # Telemetry generator, AI service
│   │   ├── config.py
│   │   ├── database.py
│   │   └── main.py           # FastAPI application entry
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── page.tsx          # Main dashboard (all tabs)
│   │   ├── layout.tsx
│   │   └── globals.css
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## 🔌 API Reference

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Service health & telemetry source |
| `GET` | `/api/services` | Lists all monitored microservices |
| `GET` | `/api/metrics/live` | Latest telemetry snapshot |
| `GET` | `/api/metrics/history` | Historical metrics for charts |
| `GET` | `/api/incidents` | All active and resolved incidents |
| `POST` | `/api/demo/scenario/{id}` | Inject failure scenario (1–6, reset) |
| `POST` | `/api/incidents/{id}/investigate` | Trigger LangGraph multi-agent analysis |
| `POST` | `/api/incidents/{id}/approve` | Approve proposed runbook execution |
| `POST` | `/api/incidents/{id}/reject` | Reject proposed runbook |
| `POST` | `/api/incidents/{id}/remediate` | Manually fire remediation |
| `GET` | `/api/approvals` | Pending remediation approvals |
| `GET` | `/api/reports` | Generated post-mortem reports |
| `GET` | `/api/events/stream` | Server-Sent Events real-time feed |

---

## 🎯 Demo Scenarios

Use the **Scenario Failure Injector** in the Overview tab, or call the API:
```bash
curl -X POST http://localhost:8000/api/demo/scenario/1
```

| ID | Scenario | Target Service | Runbook |
|---|---|---|---|
| 1 | DB Connection Pool Exhaustion | payment-service | `increase_demo_pool_limit` |
| 2 | Memory Leak | search-service | `rolling_restart` |
| 3 | Cascading Failure | video-streaming | `restart_service` |
| 4 | API Gateway Crash Loop | cdn-edge | `rollback_configuration` |
| 5 | Bot Management DB Outage | auth-service | `rollback_configuration` |
| 6 | DynamoDB DNS Failure | search-service | `flush_dns_cache` |

### Full Self-Healing Loop

1. **Inject** → Scenario triggers anomalous metrics on target service
2. **Detect** → Z-Score & Isolation Forest flag deviations
3. **Correlate** → Dependency graph groups related alerts into one incident
4. **Investigate** → LangGraph Investigator Agent analyzes logs + RAG memory
5. **Propose** → Remediator Agent maps root cause to approved runbook
6. **Approve** → Operator clicks "Approve" (or auto-approve for LOW risk)
7. **Execute** → RunbookExecutor runs the remediation in sandbox
8. **Verify** → TelemetryVerifier checks before/after metrics
9. **Report** → Reporter Agent compiles post-mortem with MTTD/MTTR

---

## 🔒 Safety Architecture

1. **No Arbitrary Execution** — Runbook actions are bound to a static allowlist (`RunbookRegistry`). The agent cannot generate shell commands.
2. **Risk-Based Policies** — `PolicyEngine` auto-approves LOW risk, halts MEDIUM/HIGH/CRITICAL for human authorization.
3. **Automated Rollback** — If `TelemetryVerifier` flags metrics as still failing after execution, `RollbackExecutor` reverts the change immediately.
4. **Secrets Filtering** — Log captures pass through `redact_secrets` regex sanitizer before database storage.

---

## ⚙️ Environment Variables

| Variable | Default | Description |
|---|---|---|
| `DATABASE_URL` | `sqlite:///./sentinelops.db` | Database connection string |
| `TELEMETRY_SOURCE` | `google_scale` | `google_scale` or `simulation` |
| `LLM_PROVIDER` | `demo` | `demo`, `openai`, `anthropic`, `groq` |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection (optional for SQLite mode) |
| `JWT_SECRET` | `change-me-in-production` | JWT signing key |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
