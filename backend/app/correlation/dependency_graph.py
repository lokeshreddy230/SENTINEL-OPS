from sqlalchemy.orm import Session
from app.models.service import Service
from typing import Dict, List

class DependencyGraph:
    @staticmethod
    def get_dependencies(db: Session) -> Dict[str, List[str]]:
        """
        Returns a dictionary mapping service_id to its list of downstream service dependencies.
        """
        services = db.query(Service).all()
        return {s.id: s.dependencies for s in services}

    @staticmethod
    def is_dependent_or_related(db: Session, service_a: str, service_b: str) -> bool:
        """
        Returns True if there is a direct upstream/downstream relationship between service_a and service_b.
        """
        if service_a == service_b:
            return True
            
        deps = DependencyGraph.get_dependencies(db)
        
        # Check if service_a calls service_b
        if service_b in deps.get(service_a, []):
            return True
            
        # Check if service_b calls service_a
        if service_a in deps.get(service_b, []):
            return True
            
        return False
