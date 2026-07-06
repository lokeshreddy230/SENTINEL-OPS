import numpy as np
import logging
from app.config import settings

logger = logging.getLogger("sentinelops.rag.embeddings")

class RAGEmbeddings:
    @staticmethod
    def get_embedding(text: str) -> list[float]:
        """
        Generates a 1536-dimensional embedding vector.
        Uses OpenAI Embeddings if configured, or falls back to a deterministic local hashing vectorizer.
        """
        if settings.LLM_PROVIDER.lower() == "openai" and settings.OPENAI_API_KEY:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=settings.OPENAI_API_KEY)
                response = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=text
                )
                return response.data[0].embedding
            except Exception as e:
                logger.error(f"Failed to fetch OpenAI embedding: {e}. Falling back to local vectorizer.")
                
        # Fallback: Deterministic vector generation using text hash seed
        np.random.seed(hash(text) % (2**32 - 1))
        vector = np.random.normal(0.0, 1.0, 1536)
        # Normalize vector
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector = vector / norm
        return vector.tolist()
