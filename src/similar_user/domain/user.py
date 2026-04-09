"""User node structure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PatientNode:
    """Patient node data used by fixed graph path patterns."""

    id: str
    name: str | None = None
    性别: str | None = None
