"""
SentinelOps Backend — FastAPI Application Entry Point
=====================================================
Autonomous AI Agent for Incident Response and Self-Healing Infrastructure.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import Base, engine, SessionLocal
from app.models.service import Service
from app.api import services, metrics, incidents, approvals, reports, demo, stream, hardware
from app.services.telemetry_generator import telemetry_generator
from app.config import settings
import logging

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("sentinelops")

# Auto-create tables on startup (SQLite/PostgreSQL)
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables initialized successfully.")
except Exception as e:
    logger.error(f"Error initializing database tables: {e}")


# ---------------------------------------------------------------------------
# Lifespan — replaces deprecated @app.on_event("startup") / ("shutdown")
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on application startup and shutdown."""
    # --- Startup ---
    _seed_services()
    telemetry_generator.start()
    logger.info("SentinelOps backend started successfully.")
    yield
    # --- Shutdown ---
    logger.info("Stopping background tasks...")
    telemetry_generator.stop()


def _seed_services() -> None:
    """Seed the database with monitored microservices."""
    db = SessionLocal()
    try:
        if settings.TELEMETRY_SOURCE == "google_scale":
            services_to_seed = [
                {"id": "auth-service", "name": "Auth Service", "dependencies": []},
                {"id": "payment-service", "name": "Payment Service", "dependencies": ["auth-service"]},
                {"id": "notification-service", "name": "Notification Service", "dependencies": []},
                {"id": "search-service", "name": "Search Service", "dependencies": []},
                {"id": "recommendation-engine", "name": "Recommendation Engine", "dependencies": ["search-service", "user-profile"]},
                {"id": "user-profile", "name": "User Profile", "dependencies": []},
                {"id": "video-streaming", "name": "Video Streaming", "dependencies": ["cdn-edge", "auth-service"]},
                {"id": "analytics-pipeline", "name": "Analytics Pipeline", "dependencies": []},
                {"id": "cdn-edge", "name": "CDN Edge", "dependencies": []},
            ]
        else:
            services_to_seed = [
                {"id": "gateway", "name": "API Gateway", "dependencies": ["auth_service", "order_service"]},
                {"id": "auth_service", "name": "Auth Service", "dependencies": []},
                {"id": "order_service", "name": "Order Service", "dependencies": ["payment_service", "database_service"]},
                {"id": "payment_service", "name": "Payment Service", "dependencies": []},
                {"id": "database_service", "name": "Database Service", "dependencies": []},
            ]

        # Remove stale service records that no longer belong to the active set
        active_ids = [s["id"] for s in services_to_seed]
        db.query(Service).filter(~Service.id.in_(active_ids)).delete(synchronize_session=False)

        for s in services_to_seed:
            existing = db.query(Service).filter(Service.id == s["id"]).first()
            if not existing:
                db.add(Service(id=s["id"], name=s["name"], dependencies=s["dependencies"], status="healthy"))
                logger.info(f"Seeded service: {s['name']}")
        db.commit()
    except Exception as e:
        logger.error(f"Error seeding services on startup: {e}")
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Application factory
# ---------------------------------------------------------------------------
app = FastAPI(
    title="SentinelOps API",
    description="Autonomous AI Agent for Incident Response and Self-Healing Infrastructure",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow all origins for local/demo usage
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Health check
@app.get("/api/health", tags=["Health"])
def health_check():
    return {
        "status": "healthy",
        "database": "connected",
        "telemetry_source": settings.TELEMETRY_SOURCE,
        "version": "1.0.0",
    }


# Register API routers
app.include_router(services.router)
app.include_router(metrics.router)
app.include_router(incidents.router)
app.include_router(approvals.router)
app.include_router(reports.router)
app.include_router(demo.router)
app.include_router(stream.router)
app.include_router(hardware.router)
