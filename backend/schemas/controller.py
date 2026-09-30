
from pydantic import BaseModel, Field


class ControllerFeatures(BaseModel):
    stability: float = 0.0
    completeness: float = 0.0
    query_type: str = "information_seeking"
    new_content_tokens: int = 0
    retrieved_before: bool = False
    cooldown_ok: bool = True
    dangling_tail: bool = False
    utterance_end: bool = False

class ControllerDecision(BaseModel):
    decision: str  # WAIT, RETRIEVE, NO_RETRIEVE
    trigger: str | None = None
    confidence: float = 0.0
    reason: str = ""
    features: ControllerFeatures = Field(default_factory=ControllerFeatures)
    retrieval_required: bool = False
