"""
SentinelOps — Database Engine & Session Factory
================================================
Supports both SQLite (local dev) and PostgreSQL (Docker/production).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
from app.config import settings

# Build connection arguments based on the database backend
connect_args: dict = {}
engine_kwargs: dict = {}

if settings.DATABASE_URL.startswith("sqlite"):
    # SQLite requires check_same_thread=False for FastAPI's async workers
    connect_args["check_same_thread"] = False
else:
    # PostgreSQL: enable connection-pool health checks
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Register all ORM models so Base.metadata knows about them
from app.models.service import Service  # noqa: E402, F401
from app.models.metric import Metric, LogEvent  # noqa: E402, F401
from app.models.incident import (  # noqa: E402, F401
    User, Incident, IncidentEvent, Investigation, Hypothesis, IncidentReport,
)
from app.models.remediation import (  # noqa: E402, F401
    RemediationPlan, Approval, ExecutionRecord, VerificationResult,
)


def get_db():
    """FastAPI dependency that yields a database session and closes it after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
