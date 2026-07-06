from typing import List, Dict, Any
from app.rag.incident_store import incident_store

class IncidentRetriever:
    @staticmethod
    def get_similar_incidents(symptoms: str, service_id: str = None, limit: int = 2) -> List[Dict[str, Any]]:
        """
        Retrieves similar historical incidents based on symptom queries and service filters.
        """
        return incident_store.search_similar(symptoms, service_filter=service_id, limit=limit)
