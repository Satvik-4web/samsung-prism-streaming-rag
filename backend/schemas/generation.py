
from enum import Enum

from pydantic import BaseModel, Field

from backend.schemas.corpus import Citation


class ClaimStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONFLICTING = "CONFLICTING"
    UNCERTAIN = "UNCERTAIN"


class VerifiedCitation(Citation):
    """A citation after the grounding existence and support gates."""

    verified: bool = False
    support_score: float = 0.0
    quoted_span: str = ""
    invalid_reason: str | None = None


class Claim(BaseModel):
    claim_id: str
    text: str
    intent_id: str
    supported_by_chunk_ids: list[str] = Field(default_factory=list)
    citations: list[VerifiedCitation] = Field(default_factory=list)
    status: ClaimStatus = ClaimStatus.UNCERTAIN
    uncertainty: str | None = None

class AnswerVersion(BaseModel):
    version: int
    session_id: str
    request_id: str
    claims: list[Claim] = Field(default_factory=list)
    delta_summary: dict[str, str] = Field(default_factory=dict)
    # Version-chain metadata is optional so existing callers can continue to
    # construct the original, small model.
    version_id: str = ""
    parent_version: int | None = None
    parent_version_id: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)
    trigger_delta: dict[str, object] = Field(default_factory=dict)
    claim_diffs: dict[str, str] = Field(default_factory=dict)
    rendered_answer: str = ""
