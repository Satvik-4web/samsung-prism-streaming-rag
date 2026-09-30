from typing import Any

from pydantic import BaseModel, Field


class Section(BaseModel):
    section_id: str
    title: str | None = None
    content: str = ""
    level: int = 1

class Document(BaseModel):
    document_id: str
    title: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    sections: list[Section] = Field(default_factory=list)

class Chunk(BaseModel):
    chunk_id: str
    document_id: str
    section_id: str
    text: str
    content_hash: str
    token_count: int
    prev_chunk_id: str | None = None
    next_chunk_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

class Citation(BaseModel):
    document_id: str
    section_id: str
    chunk_id: str
    display: str

    @classmethod
    def from_ids(cls, document_id: str, section_id: str, chunk_id: str) -> "Citation":
        """Build the only citation display form accepted by the renderer."""
        return cls(
            document_id=document_id,
            section_id=section_id,
            chunk_id=chunk_id,
            display=f"[{document_id} §{section_id}]",
        )

class CorpusManifest(BaseModel):
    corpus_id: str
    total_documents: int
    total_chunks: int
    document_hashes: dict[str, str]
    chunk_metadata: dict[str, dict[str, Any]] = Field(default_factory=dict)
