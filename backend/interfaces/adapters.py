from collections.abc import Iterator
from typing import Protocol

from backend.schemas.corpus import Chunk, Document


class CorpusAdapter(Protocol):
    def load(self, source_path: str) -> Iterator[Document]:
        ...
    
    def chunk(self, document: Document) -> Iterator[Chunk]:
        ...
