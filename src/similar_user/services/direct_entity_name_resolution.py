"""Resolve user-entered direct entity names through exact and alias lookup."""

from __future__ import annotations

import string
import unicodedata
from dataclasses import dataclass
from typing import Any

from ..data_access.kg_repository import KgRepository


@dataclass
class DirectEntityNameResolver:
    """Resolve names to Disease/Symptom/Unknown IDs using exact and alias lookup."""

    repository: KgRepository

    def resolve_names(self, entity_names: list[str]) -> dict[str, list[dict[str, Any]]]:
        """Resolve names and keep unresolved names explicit for downstream fallback."""
        resolved: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []
        for entity_name in _dedupe_texts(entity_names):
            matches = self._resolve_one(entity_name)
            if matches:
                resolved.extend(matches)
            else:
                unresolved.append(
                    {
                        "input_name": entity_name,
                        "reason": "not_found_in_kg",
                    }
                )
        return {
            "resolved": resolved,
            "unresolved": unresolved,
        }

    def _resolve_one(self, entity_name: str) -> list[dict[str, Any]]:
        exact_matches = self._exact_matches(entity_name)
        if exact_matches:
            return exact_matches

        alias_matches = self._alias_index_matches(entity_name)
        if alias_matches:
            return alias_matches

        return []

    def _exact_matches(self, entity_name: str) -> list[dict[str, Any]]:
        rows = self.repository.resolve_direct_entity_name(entity_name)
        return _rows_to_resolved_items(
            rows,
            input_name=entity_name,
            resolution_level="neo4j_exact",
        )

    def _alias_index_matches(self, entity_name: str) -> list[dict[str, Any]]:
        normalized_input = _normalize_lookup_key(entity_name)
        if not normalized_input:
            return []
        matches = []
        for row in self.repository.get_direct_entity_alias_index():
            alias_label = _normalize_optional_text(row.get("alias_label"))
            if _normalize_lookup_key(alias_label) != normalized_input:
                continue
            matches.append(row)
        return _rows_to_resolved_items(
            matches,
            input_name=entity_name,
            resolution_level="neo4j_alias_index",
        )


def _rows_to_resolved_items(
    rows: list[dict[str, Any]],
    *,
    input_name: str,
    resolution_level: str,
) -> list[dict[str, Any]]:
    resolved: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in rows:
        entity_type = _normalize_optional_text(row.get("entity_type"))
        entity_id = _normalize_optional_text(row.get("entity_id"))
        if entity_type is None or entity_id is None:
            continue
        key = (entity_type, entity_id)
        if key in seen:
            continue
        resolved.append(
            {
                "input_name": input_name,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "entity_name": _normalize_optional_text(row.get("entity_name")),
                "alias_label": _normalize_optional_text(row.get("alias_label")),
                "resolution_level": resolution_level,
            }
        )
        seen.add(key)
    return resolved


def _dedupe_texts(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _normalize_optional_text(value)
        if text is None or text in seen:
            continue
        deduped.append(text)
        seen.add(text)
    return deduped


def _normalize_lookup_key(value: object) -> str:
    text = _normalize_optional_text(value)
    if text is None:
        return ""
    normalized = unicodedata.normalize("NFKC", text).casefold()
    return "".join(
        char
        for char in normalized
        if not char.isspace() and char not in string.punctuation
    )


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
