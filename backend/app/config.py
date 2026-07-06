"""
SentinelOps — Application Configuration
========================================
Uses pydantic-settings to load configuration from environment variables
and `.env` files with sensible defaults for local development.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database — defaults to SQLite for zero-dependency local runs
    DATABASE_URL: str = "sqlite:///./sentinelops.db"

    # Telemetry source: "google_scale" | "simulation"
    TELEMETRY_SOURCE: str = "google_scale"

    # Redis (optional — not required for SQLite/demo mode)
    REDIS_URL: str = "redis://localhost:6379/0"

    # LLM provider: "demo" | "openai" | "anthropic" | "groq"
    LLM_PROVIDER: str = "demo"
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None

    # Security
    JWT_SECRET: str = "change-me-in-production"

    # Prometheus (optional)
    PROMETHEUS_URL: str = "http://localhost:9090"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = Settings()
