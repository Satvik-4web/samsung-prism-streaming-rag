"""Deterministic, dependency-free checks used by the grounding stage."""

from __future__ import annotations

import re
from collections.abc import Iterable

_WORD = re.compile(r"[A-Za-z][A-Za-z0-9'_-]*|\d+(?:[.,]\d+)?%?")
_NUMBER = re.compile(r"(?<![A-Za-z])\d+(?:[.,]\d+)?%?")
_STOP = {"a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "the", "to", "was", "were", "with"}


def normalize(text: str) -> str:
    return " ".join(text.casefold().split())


def terms(text: str) -> set[str]:
    return {token.casefold() for token in _WORD.findall(text) if token.casefold() not in _STOP}


def numbers(text: str) -> set[str]:
    return {value.replace(",", "") for value in _NUMBER.findall(text)}


def entities(text: str) -> set[str]:
    # Capitalized spans are a deliberately conservative named-entity proxy.
    sentence_words = {"A", "An", "And", "But", "For", "In", "It", "On", "The", "This", "That", "To"}
    return {word.casefold() for word in re.findall(r"\b[A-Z][A-Za-z0-9_-]+\b", text) if word not in sentence_words}


def support_score(claim: str, evidence: str) -> float:
    """Return term recall, with hard zero for an atomic number mismatch."""
    wanted, available = terms(claim), terms(evidence)
    if not wanted:
        return 0.0
    if numbers(claim) - numbers(evidence):
        return 0.0
    if entities(claim) - entities(evidence):
        return 0.0
    return len(wanted & available) / len(wanted)


def check_support(claim: str, evidence: str) -> tuple[bool, float]:
    score = support_score(claim, evidence)
    return score >= 0.60, score


def shared_subject(left: str, right: str) -> bool:
    a, b = terms(left), terms(right)
    return bool(a & b) and len(a & b) >= max(1, min(len(a), len(b)) // 3)


def polarity(text: str) -> bool:
    return not bool(re.search(r"\b(no|not|never|cannot|can't|prohibited|forbidden|disallow)\b", text, re.IGNORECASE))


def find_conflicts(claim: str, evidence_texts: Iterable[str]) -> bool:
    """Detect disagreement among evidence supporting the same claim."""
    relevant = [text for text in evidence_texts if shared_subject(claim, text)]
    if len(relevant) < 2:
        return False
    claim_numbers = numbers(claim)
    observed = [numbers(text) for text in relevant]
    nonempty = [values for values in observed if values]
    if len(nonempty) >= 2 and len({frozenset(values) for values in nonempty}) > 1:
        return True
    if len({polarity(text) for text in relevant}) > 1:
        return True
    # A claim with one stated value is conflicting when another relevant source
    # explicitly states a different value.
    return bool(claim_numbers and any(values and values != claim_numbers for values in observed))
