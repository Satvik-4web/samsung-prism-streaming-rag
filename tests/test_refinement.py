from backend.generation import AnswerVersionStore
from backend.schemas.evidence import Evidence
from backend.schemas.generation import Claim, ClaimStatus, VerifiedCitation
from backend.session.refinement import assert_preserved_claims_unchanged, preserved_claim_ids


def test_unaffected_claim_is_preserved_across_versions() -> None:
    evidence = [
        Evidence(evidence_id="a", chunk_id="a", document_id="d", section_id="s", text="A"),
        Evidence(evidence_id="b", chunk_id="b", document_id="d", section_id="s", text="B"),
    ]

    def claim(claim_id: str, text: str, chunk_id: str) -> Claim:
        citation = VerifiedCitation.from_ids("d", "s", chunk_id)
        citation.verified = True
        return Claim(claim_id=claim_id, text=text, intent_id=claim_id, citations=[citation], status=ClaimStatus.SUPPORTED)

    store = AnswerVersionStore()
    first = store.create("s", "r1", [claim("a", "A", "a"), claim("b", "B", "b")], evidence)
    second = store.create("s", "r2", [claim("a", "A2", "a"), claim("b", "B", "b")], evidence, {"intent": "a"})

    assert preserved_claim_ids(first, second) == {"b"}
    assert_preserved_claims_unchanged(first, second, {"b"})
