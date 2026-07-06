from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.telemetry_service import TelemetryService
from app.schemas.metric import MetricResponse
from typing import List

router = APIRouter(prefix="/api/metrics", tags=["Metrics"])

@router.get("/live", response_model=List[MetricResponse])
def get_live_metrics(db: Session = Depends(get_db)):
    return TelemetryService.get_live_metrics(db)

@router.get("/history", response_model=List[MetricResponse])
def get_metric_history(
    service_id: str = Query(..., description="ID of the service"),
    minutes: int = Query(15, description="Lookback window in minutes"),
    db: Session = Depends(get_db)
):
    return TelemetryService.get_metric_history(db, service_id, minutes)
