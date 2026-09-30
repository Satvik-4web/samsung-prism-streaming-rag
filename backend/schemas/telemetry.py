import uuid
from typing import Any

from pydantic import BaseModel, Field


class TelemetryEvent(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    event_type: str
    session_id: str
    request_id: str | None = None
    seq: int | None = None
    ts: str = ""  # ISO format
    t_stream_ms: int = 0
    latency_ms: float | None = None
    payload: dict[str, Any] = Field(default_factory=dict)
