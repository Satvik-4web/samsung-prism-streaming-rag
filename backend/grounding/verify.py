"""Closed-corpus citation verification and deterministic claim grounding."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from backend.grounding.claims import check_support, find_conflicts
from backend.schemas.evidence import Evidence
from backend.schemas.generation import Claim, ClaimStatus, VerifiedCitation
from backend.schemas.telemetry import TelemetryEvent
from backend.telemetry.bus import TelemetryBus, telemetry_bus


def citation_key(document_id: str, section_id: str, chunk_id: str) -> tuple[str, str, str]:
    return document_id, section_id, chunk_id


def citation_exists(citation: VerifiedCitation, evidence: Mapping[str, Evidence]) -> bool:
    """Hard existence/mapping gate: all three IDs must map to one chunk."""
    item = evidence.get(citation.chunk_id)
    return bool(item and citation_key(item.document_id, item.section_id, item.chunk_id) == citation_key(citation.document_id, citation.section_id, citation.chunk_id))


def map_citation(citation: VerifiedCitation, evidence: Mapping[str, Evidence]) -> Evidence | None:
    """Return the session evidence mapped by a citation, or ``None``."""
    return evidence.get(citation.chunk_id) if citation_exists(citation, evidence) else None


class GroundingVerifier:
    def __init__(self, bus: TelemetryBus | None = telemetry_bus) -> None:
        self.bus = bus

    def verify_citation(self, citation: VerifiedCitation, evidence: Mapping[str, Evidence]) -> VerifiedCitation:
        ev = map_citation(citation, evidence)
        valid = ev is not None
        if not valid:
            citation.verified = False
            citation.invalid_reason = "citation_not_in_session_evidence"
            return citation
        citation.verified = True
        citation.invalid_reason = None
        citation.display = f"[{ev.document_id} §{ev.section_id}]"
        citation.quoted_span = ev.text[:240]
        return citation

    def verify_claim(self, claim: Claim, evidence: Sequence[Evidence], session_id: str = "grounding") -> Claim:
        by_id = {item.chunk_id: item for item in evidence}
        citations = list(claim.citations)
        # Preserve the legacy structured ID API by materializing citations.
        for chunk_id in claim.supported_by_chunk_ids:
            if chunk_id in by_id and not any(c.chunk_id == chunk_id for c in citations):
                ev = by_id[chunk_id]
                citations.append(VerifiedCitation.from_ids(ev.document_id, ev.section_id, ev.chunk_id))
        verified: list[VerifiedCitation] = []
        relevant_texts: list[str] = []
        for citation in citations:
            checked = self.verify_citation(citation, by_id)
            if checked.verified:
                relevant_texts.append(by_id[checked.chunk_id].text)
                _ok, score = check_support(claim.text, by_id[checked.chunk_id].text)
                checked.support_score = score
                verified.append(checked)
                if self.bus:
                    self.bus.emit(TelemetryEvent(
                        event_type="citation_verified",
                        session_id=session_id,
                        payload={"claim_id": claim.claim_id, "chunk_id": checked.chunk_id, "support_score": score},
                    ))
            elif self.bus:
                self.bus.emit(TelemetryEvent(event_type="citation_invalid", session_id=session_id, payload={"claim_id": claim.claim_id, "chunk_id": citation.chunk_id, "reason": checked.invalid_reason}))
        claim.citations = verified
        claim.supported_by_chunk_ids = [c.chunk_id for c in verified if c.support_score >= 0.60]
        if find_conflicts(claim.text, relevant_texts):
            claim.status = ClaimStatus.CONFLICTING
            claim.uncertainty = 'Sources disagree.'
            claim.verification_reason = 'Multiple evidence chunks disagree.'
        elif claim.supported_by_chunk_ids:
            claim.status = ClaimStatus.SUPPORTED
            claim.verification_reason = 'Entity and numeric constraints successfully verified against corpus.'
        elif verified:
            claim.status = ClaimStatus.UNCERTAIN
            claim.uncertainty = 'The cited evidence only partially supports this claim.'
            claim.verification_reason = 'Insufficient evidence to establish the claim fully.'
        else:
            claim.status = ClaimStatus.UNSUPPORTED
            claim.uncertainty = 'No verified citation supports this claim.'
            claim.verification_reason = 'No matching evidence found in valid citations.'
        if self.bus:
            event_type = {
                ClaimStatus.SUPPORTED: "claim_verified",
                ClaimStatus.CONFLICTING: "claim_conflict",
                ClaimStatus.UNSUPPORTED: "claim_unsupported",
                ClaimStatus.UNCERTAIN: "claim_uncertain",
            }[claim.status]
            self.bus.emit(TelemetryEvent(
                event_type=event_type,
                session_id=session_id,
                payload={"claim_id": claim.claim_id, "status": claim.status.value},
            ))
        return claim

    def verify(self, claims: Sequence[Claim], evidence: Sequence[Evidence], session_id: str = "grounding") -> list[Claim]:
        if self.bus:
            self.bus.emit(TelemetryEvent(event_type="grounding_started", session_id=session_id, payload={"claims": len(claims), "evidence": len(evidence)}))
        original_citation_count = sum(
            len(claim.citations)
            + sum(1 for chunk_id in claim.supported_by_chunk_ids if not any(c.chunk_id == chunk_id for c in claim.citations))
            for claim in claims
        )
        result = [self.verify_claim(claim, evidence, session_id) for claim in claims]
        invalid_citation_count = max(0, original_citation_count - sum(len(claim.citations) for claim in result))
        if self.bus:
            self.bus.emit(TelemetryEvent(event_type="grounding_completed", session_id=session_id, payload={"statuses": {status.value: sum(c.status == status for c in result) for status in ClaimStatus}, "invalid_citations": invalid_citation_count}))
        return result


def verify_claims(claims: Sequence[Claim], evidence: Sequence[Evidence], session_id: str = "grounding", bus: TelemetryBus | None = telemetry_bus) -> list[Claim]:
    return GroundingVerifier(bus).verify(claims, evidence, session_id)


__all__ = ["GroundingVerifier", "citation_exists", "citation_key", "map_citation", "verify_claims"]


