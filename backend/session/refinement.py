"""Small deterministic helpers for checking answer refinement invariants."""

from __future__ import annotations

from collections.abc import Iterable

from backend.schemas.generation import AnswerVersion


def preserved_claim_ids(parent: AnswerVersion, child: AnswerVersion) -> set[str]:
    """Return claim IDs explicitly marked preserved by the version diff."""
    return {claim_id for claim_id, change in child.claim_diffs.items() if change == "preserved" and claim_id in {c.claim_id for c in parent.claims}}


def assert_preserved_claims_unchanged(parent: AnswerVersion, child: AnswerVersion, claim_ids: Iterable[str]) -> None:
    """Raise AssertionError if a supposedly unaffected claim changed."""
    old = {claim.claim_id: claim for claim in parent.claims}
    new = {claim.claim_id: claim for claim in child.claims}
    for claim_id in claim_ids:
        if claim_id not in old or claim_id not in new or old[claim_id].model_dump() != new[claim_id].model_dump():
            raise AssertionError(f"refinement changed preserved claim {claim_id}")


__all__ = ["assert_preserved_claims_unchanged", "preserved_claim_ids"]
