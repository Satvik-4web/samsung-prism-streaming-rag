import os
import time
from abc import ABC, abstractmethod
from backend.telemetry.bus import telemetry_bus
from backend.schemas.telemetry import TelemetryEvent

class Embedder(ABC):
    @abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        pass

class DummyEmbedder(Embedder):
    def embed(self, texts: list[str]) -> list[list[float]]:
        # Deterministic lightweight development implementation
        return [[len(t) * 0.1, 0.5] for t in texts]

class SentenceTransformerEmbedder(Embedder):
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
            self.model_name = model_name
        except Exception as e:
            print(f"Failed to load SentenceTransformer: {e}. Falling back to DummyEmbedder.")
            self.model = None

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.model:
            return DummyEmbedder().embed(texts)
        start = time.perf_counter()
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        latency = (time.perf_counter() - start) * 1000
        
        telemetry_bus.emit(TelemetryEvent(
            event_type="embedding_computed",
            session_id="system",
            payload={
                "dense_provider": "sentence_transformer",
                "embedding_model": self.model_name,
                "embedding_dimension": len(embeddings[0]) if len(embeddings) > 0 else 0,
                "embedding_latency_ms": latency
            }
        ))
        return embeddings.tolist()

def get_embedder() -> Embedder:
    provider = os.getenv("DENSE_PROVIDER", "dummy").lower()
    if provider == "sentence_transformer":
        return SentenceTransformerEmbedder()
    return DummyEmbedder()
