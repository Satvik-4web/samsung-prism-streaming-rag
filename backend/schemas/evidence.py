from pydantic import BaseModel, Field


class Evidence(BaseModel):
    evidence_id: str
    chunk_id: str
    document_id: str
    section_id: str
    text: str
    intent_ids: list[str] = Field(default_factory=list)
    scores: dict[str, float] = Field(default_factory=dict)
    retrieval_source: str = ""
    citation_reference: str = ""
    retrieved_at_version: int = 1
    status: str = "active"
