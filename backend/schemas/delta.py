from typing import Any

from pydantic import BaseModel, Field

from backend.schemas.intents import Intent


class DeltaPlan(BaseModel):
    changed_constraints: list[dict[str, Any]] = Field(default_factory=list)
    affected_intents: list[Intent] = Field(default_factory=list)
    preserved_intents: list[Intent] = Field(default_factory=list)
    obsolete_intents: list[Intent] = Field(default_factory=list)
