# SentinelOps Architecture Decisions

## 1. Monorepo Structure
We selected a unified monorepo approach with separate `backend` (Python FastAPI) and `frontend` (Next.js) subdirectories to enable easy packaging, local run scripts, and single-container deployments using Docker Compose.

## 2. Server-Sent Events (SSE) for Real-Time Streaming
Rather than maintaining heavy bidirectional WebSockets, we chose Server-Sent Events (`sse-starlette`) for streaming real-time metrics, log signals, and agent execution events. SSE is highly resilient, supports automatic reconnects natively, and fits the telemetry feed format.

## 3. Database Layer & Fallbacks
We configured SQLAlchemy engine creation to support both Postgres (for production/Docker environments) and SQLite fallback (for quick local CLI development). All tables are mapped via declarative bases in `backend/app/database.py`.

## 4. Single-Page Tab-Based UI State
We implemented the frontend as a single-page app with tabs. This ensures that the active EventSource stream remains persistent as users toggle between the Topology, Metrics, and Incident Command Center views, preventing state loss or connection thrashing.
