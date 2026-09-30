from typing import Any
from enum import Enum
from pydantic import BaseModel, Field
from backend.schemas.intents import Intent

class DeltaType(str, Enum):
    ADDED = "ADDED"
    REMOVED = "REMOVED"
    CHANGED = "CHANGED"
    UNCHANGED = "UNCHANGED"

class DeltaPlan(BaseModel):
    changed_constraints: list[dict[str, Any]] = Field(default_factory=list)
    affected_intents: list[Intent] = Field(default_factory=list)
    preserved_intents: list[Intent] = Field(default_factory=list)
    obsolete_intents: list[Intent] = Field(default_factory=list)
    delta_states: dict[str, DeltaType] = Field(default_factory=dict)
