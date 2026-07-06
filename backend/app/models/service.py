from sqlalchemy import Column, String, JSON
from app.database import Base

class Service(Base):
    __tablename__ = "services"

    id = Column(String, primary_key=True, index=True)  # e.g., gateway, auth_service
    name = Column(String, nullable=False)
    status = Column(String, default="healthy")  # healthy, warning, critical, recovering
    dependencies = Column(JSON, default=list)  # List of service IDs this service depends on
