from backend.grounding.verify import GroundingVerifier
from backend.schemas.evidence import Evidence
from backend.schemas.generation import Claim, ClaimStatus


def evidence(chunk_id: str, document_id: str, text: str) -> Evidence:
    return Evidence(
        evidence_id=chunk_id,
        chunk_id=chunk_id,
        document_id=document_id,
        section_id="policy",
        text=text,
    )


def test_valid_and_fabricated_citations_are_gated() -> None:
    ev = evidence("D1::policy::1", "D1", "Cancellation is allowed within 30 days.")
    valid = Claim(claim_id="valid", text="Cancellation is allowed within 30 days.", intent_id="i", supported_by_chunk_ids=[ev.chunk_id])
    fabricated = Claim(claim_id="fake", text="Cancellation is allowed within 30 days.", intent_id="i", supported_by_chunk_ids=["D999::policy::1"])

    result = GroundingVerifier(bus=None).verify([valid, fabricated], [ev])
    assert result[0].status is ClaimStatus.SUPPORTED
    assert result[0].citations[0].verified
    assert result[1].status is ClaimStatus.UNSUPPORTED
    assert not result[1].citations


def test_partial_support_and_numeric_mismatch_are_uncertain() -> None:
    ev = evidence("D1::policy::1", "D1", "Cancellation is allowed within 30 days.")
    partial = Claim(claim_id="partial", text="Cancellation is allowed within 90 days.", intent_id="i", supported_by_chunk_ids=[ev.chunk_id])
    result = GroundingVerifier(bus=None).verify([partial], [ev])[0]
    assert result.status is ClaimStatus.UNCERTAIN
    assert result.uncertainty


def test_conflicting_numeric_evidence_is_explicit() -> None:
    first = evidence("D1::policy::1", "D1", "Cancellation is allowed within 30 days.")
    second = evidence("D2::policy::1", "D2", "Cancellation is allowed within 60 days.")
    claim = Claim(claim_id="conflict", text="Cancellation is allowed within 30 days.", intent_id="i", supported_by_chunk_ids=[first.chunk_id, second.chunk_id])
    result = GroundingVerifier(bus=None).verify([claim], [first, second])[0]
    assert result.status is ClaimStatus.CONFLICTING
