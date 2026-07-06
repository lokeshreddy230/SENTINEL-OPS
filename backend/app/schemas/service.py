from pydantic import BaseModel
from typing import List

class ServiceBase(BaseModel):
    id: str
    name: str
    status: str
    dependencies: List[str] = []

    class Config:
        from_attributes = True

class ServiceCreate(ServiceBase):
    pass

class ServiceResponse(ServiceBase):
    pass
