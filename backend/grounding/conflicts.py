"""Conflict detection facade (kept separate for callers that only need this gate)."""

from backend.grounding.claims import find_conflicts

__all__ = ["find_conflicts"]
