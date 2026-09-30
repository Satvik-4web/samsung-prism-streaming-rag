from backend.generation import AnswerVersionStore, DeterministicAnswerGenerator
from backend.schemas.evidence import Evidence
from backend.schemas.generation import Claim, ClaimStatus, VerifiedCitation


def ev(evidence_id: str, text: str) -> Evidence:
    return Evidence(
        evidence_id=evidence_id,
        chunk_id=evidence_id,
        document_id="doc",
        section_id="policy",
        text=text,
    )


def grounded_claim(claim_id: str, text: str, chunk_id: str) -> Claim:
    citation = VerifiedCitation.from_ids("doc", "policy", chunk_id)
    citation.verified = True
    return Claim(
        claim_id=claim_id,
        text=text,
        intent_id="intent",
        citations=[citation],
        status=ClaimStatus.SUPPORTED,
    )


def test_deterministic_generator_renders_only_citations_and_uncertainty() -> None:
    evidence = [ev("c1", "The policy says yes.")]
    supported = grounded_claim("a", "The policy says yes.", "c1")
    uncertain = Claim(
        claim_id="b",
        text="An ungrounded assertion",
        intent_id="intent",
        status=ClaimStatus.UNCERTAIN,
        uncertainty="The corpus does not establish this.",
    )

    answer = DeterministicAnswerGenerator().generate([supported, uncertain], evidence, session_id="s")

    assert "The policy says yes." in answer.rendered_answer
    assert "[doc §policy]" in answer.rendered_answer
    assert "An ungrounded assertion" not in answer.rendered_answer
    assert "The corpus does not establish this." in answer.rendered_answer
    assert answer.evidence_ids == ["c1"]


def test_answer_versions_are_chained_without_mutating_parent() -> None:
    store = AnswerVersionStore()
    evidence = [ev("c1", "A"), ev("c2", "B")]
    first_claim = grounded_claim("keep", "A", "c1")
    first = store.create("s", "r1", [first_claim], evidence[:1])

    second_claim = grounded_claim("keep", "A changed", "c2")
    second = store.create("s", "r2", [second_claim], evidence, {"changed": "keep"})

    assert first.version == 1
    assert second.version == 2
    assert second.parent_version == 1
    assert second.parent_version_id == first.version_id
    assert second.claim_diffs == {"keep": "changed"}
    assert first.claims[0].text == "A"
    assert first.evidence_ids == ["c1"]
