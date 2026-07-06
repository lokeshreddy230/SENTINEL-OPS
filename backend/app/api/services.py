from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.service import Service
from app.schemas.service import ServiceResponse
from typing import List

router = APIRouter(prefix="/api/services", tags=["Services"])

@router.get("", response_model=List[ServiceResponse])
def list_services(db: Session = Depends(get_db)):
    return db.query(Service).all()

@router.get("/{service_id}", response_model=ServiceResponse)
def get_service(service_id: str, db: Session = Depends(get_db)):
    service = db.query(Service).filter(Service.id == service_id).first()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")
    return service
