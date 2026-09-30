"""Append-only answer version storage."""

from __future__ import annotations

from collections.abc import Sequence

from backend.generation.generator import AnswerGenerator, DeterministicAnswerGenerator
from backend.schemas.evidence import Evidence
from backend.schemas.generation import AnswerVersion, Claim
from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import telemetry_bus


class AnswerVersionStore:
    """Create versions without ever modifying a previously stored version."""

    def __init__(self, generator: AnswerGenerator | None = None) -> None:
        self._versions: dict[str, list[AnswerVersion]] = {}
        self.generator = generator or DeterministicAnswerGenerator()

    def create(
        self,
        session_id: str,
        request_id: str,
        claims: Sequence[Claim],
        evidence: Sequence[Evidence],
        trigger_delta: dict[str, object] | None = None,
    ) -> AnswerVersion:
        previous = self._versions.get(session_id, [])
        parent = previous[-1] if previous else None
        answer = self.generator.generate(
            claims,
            evidence,
            session_id=session_id,
            request_id=request_id,
            version=len(previous) + 1,
            parent=parent,
            trigger_delta=trigger_delta,
        )
        stored = answer.model_copy(deep=True)
        self._versions.setdefault(session_id, []).append(stored)
        telemetry_bus.emit(TelemetryEvent(
            event_type="answer_version_created",
            session_id=session_id,
            request_id=request_id,
            payload={"version": answer.version, "parent_version": answer.parent_version, "claim_diffs": answer.claim_diffs},
        ))
        return answer.model_copy(deep=True)

    def list(self, session_id: str) -> list[AnswerVersion]:
        return [item.model_copy(deep=True) for item in self._versions.get(session_id, [])]

    def latest(self, session_id: str) -> AnswerVersion | None:
        versions = self._versions.get(session_id, [])
        return versions[-1].model_copy(deep=True) if versions else None


__all__ = ["AnswerVersionStore"]
