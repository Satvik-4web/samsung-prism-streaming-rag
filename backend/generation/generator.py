"""Deterministic, evidence-only answer rendering.

This module deliberately has no retriever or browser dependency.  Claims are
expected to have already passed the grounding verifier; the renderer only
prints claims with verified supporting citations and labels uncertainty.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from backend.schemas.evidence import Evidence
from backend.schemas.generation import AnswerVersion, Claim, ClaimStatus
from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import telemetry_bus


class AnswerGenerator(Protocol):
    def generate(
        self,
        claims: Sequence[Claim],
        evidence: Sequence[Evidence],
        *,
        session_id: str = "",
        request_id: str = "",
        version: int = 1,
        parent: AnswerVersion | None = None,
        trigger_delta: dict[str, object] | None = None,
    ) -> AnswerVersion: ...


class DeterministicAnswerGenerator:
    """Render grounded claims in input order with stable citations."""

    def generate(
        self,
        claims: Sequence[Claim],
        evidence: Sequence[Evidence],
        *,
        session_id: str = "",
        request_id: str = "",
        version: int = 1,
        parent: AnswerVersion | None = None,
        trigger_delta: dict[str, object] | None = None,
    ) -> AnswerVersion:
        telemetry_bus.emit(TelemetryEvent(
            event_type="answer_generation_started",
            session_id=session_id,
            request_id=request_id,
            payload={"claims": len(claims), "evidence": len(evidence)},
        ))
        evidence_by_chunk = {item.chunk_id: item for item in evidence}
        rendered: list[str] = []
        grounded_claims: list[Claim] = []
        for claim in claims:
            checked = claim.model_copy(deep=True)
            valid_citations = [
                citation
                for citation in checked.citations
                if citation.verified and citation.chunk_id in evidence_by_chunk
            ]
            checked.citations = valid_citations
            checked.supported_by_chunk_ids = [item.chunk_id for item in valid_citations]
            if checked.status is ClaimStatus.SUPPORTED and valid_citations:
                citations = " ".join(c.display for c in valid_citations)
                rendered.append(f"{checked.text} {citations}".strip())
            elif checked.status is ClaimStatus.CONFLICTING:
                rendered.append(f"Uncertainty: conflicting evidence for {checked.text}")
            elif checked.status in (ClaimStatus.UNCERTAIN, ClaimStatus.UNSUPPORTED) or not valid_citations:
                notice = checked.uncertainty or "No verified evidence supports this claim."
                rendered.append(f"Uncertainty: {notice}")
            grounded_claims.append(checked)

        claim_diffs = _claim_diffs(parent.claims if parent else (), grounded_claims)
        referenced_chunks = {
            chunk_id
            for claim in grounded_claims
            for chunk_id in claim.supported_by_chunk_ids
        }
        evidence_ids = sorted(
            item.evidence_id
            for item in evidence
            if item.chunk_id in referenced_chunks
        )
        version_id = f"{session_id}:v{version}" if session_id else f"v{version}"
        answer = AnswerVersion(
            version=version,
            session_id=session_id,
            request_id=request_id,
            claims=grounded_claims,
            delta_summary={key: str(value) for key, value in (trigger_delta or {}).items()},
            version_id=version_id,
            parent_version=parent.version if parent else None,
            parent_version_id=parent.version_id if parent else None,
            evidence_ids=evidence_ids,
            trigger_delta=dict(trigger_delta or {}),
            claim_diffs=claim_diffs,
            rendered_answer="\n".join(rendered),
        )
        telemetry_bus.emit(TelemetryEvent(
            event_type="answer_generated",
            session_id=session_id,
            request_id=request_id,
            payload={"version": answer.version, "supported_claims": sum(c.status is ClaimStatus.SUPPORTED for c in grounded_claims)},
        ))
        return answer


def _claim_diffs(previous: Sequence[Claim], current: Sequence[Claim]) -> dict[str, str]:
    old = {claim.claim_id: claim for claim in previous}
    new = {claim.claim_id: claim for claim in current}
    result: dict[str, str] = {}
    for claim_id in sorted(set(old) | set(new)):
        if claim_id not in old:
            result[claim_id] = "added"
        elif claim_id not in new:
            result[claim_id] = "removed"
        elif old[claim_id].model_dump() == new[claim_id].model_dump():
            result[claim_id] = "preserved"
        else:
            result[claim_id] = "changed"
    return result


__all__ = ["AnswerGenerator", "DeterministicAnswerGenerator"]
