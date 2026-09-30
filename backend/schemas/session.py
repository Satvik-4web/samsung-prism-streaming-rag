
from pydantic import BaseModel, Field

from backend.schemas.evidence import Evidence
from backend.schemas.intents import Intent


class SessionState(BaseModel):
    session_id: str
    current_version: int = 1
    evidence: list[Evidence] = Field(default_factory=list)
    intents: list[Intent] = Field(default_factory=list)
    history: list[dict[str, str]] = Field(default_factory=list)
