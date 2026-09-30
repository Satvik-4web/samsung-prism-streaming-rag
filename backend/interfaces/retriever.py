from typing import Protocol

from backend.schemas.evidence import Evidence


class Retriever(Protocol):
    async def retrieve(self, query: str, top_k: int = 5) -> list[Evidence]:
        ...
