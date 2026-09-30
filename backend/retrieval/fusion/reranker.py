from typing import Protocol

from backend.schemas.evidence import Evidence
from backend.schemas.intents import RetrievalQuery


class Reranker(Protocol):
    async def rerank(self, query: RetrievalQuery, candidates: list[Evidence]) -> list[Evidence]:
        ...
