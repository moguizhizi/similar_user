"""Resolve user-entered direct entity names through exact, alias, and embedding lookup."""

from __future__ import annotations

import os
import string
import sys
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..data_access.kg_repository import KgRepository
from ..utils.logger import get_logger


LOGGER = get_logger(__name__)
DEFAULT_TMMKG_ROOT = Path("/home/project/kg_project/construct/TemporalMultimodalMedicalKG")
DEFAULT_TMMKG_CONFIG = DEFAULT_TMMKG_ROOT / "configs" / "tmmkg.yaml"


@dataclass
class DirectEntityNameResolver:
    """Resolve names to Disease/Symptom/Unknown IDs using three lookup levels."""

    repository: KgRepository
    embedding_enabled: bool = True
    embedding_top_k: int = 5
    _embedding_resolver: Any = field(default=None, init=False, repr=False)
    _embedding_init_failed: bool = field(default=False, init=False, repr=False)

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

        embedding_matches = self._embedding_matches(entity_name)
        if embedding_matches:
            return embedding_matches

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

    def _embedding_matches(self, entity_name: str) -> list[dict[str, Any]]:
        if not self.embedding_enabled:
            return []
        resolver = self._get_embedding_resolver()
        if resolver is None:
            return []
        try:
            candidates = resolver.resolve(
                text=entity_name,
                top_k=self.embedding_top_k,
                entity_types=["disease", "symptom", "unknown"],
            )
        except Exception as exc:
            LOGGER.warning("Embedding entity resolution failed: %s", exc)
            return []

        resolved = []
        for candidate in candidates:
            entity_id = _normalize_optional_text(getattr(candidate, "entity_id", None))
            entity_type = _normalize_optional_text(getattr(candidate, "entity_type", None))
            if entity_id is None or entity_type is None:
                continue
            resolved.append(
                {
                    "input_name": entity_name,
                    "entity_type": entity_type,
                    "entity_id": entity_id,
                    "entity_name": None,
                    "alias_label": _normalize_optional_text(
                        getattr(candidate, "alias_label", None)
                    ),
                    "is_canonical": bool(getattr(candidate, "is_canonical", False)),
                    "score": getattr(candidate, "score", None),
                    "resolution_level": "embedding",
                }
            )
        return resolved

    def _get_embedding_resolver(self) -> Any:
        if self._embedding_resolver is not None:
            return self._embedding_resolver
        if self._embedding_init_failed:
            return None

        try:
            self._embedding_resolver = _init_tmmkg_entity_resolver()
        except Exception as exc:
            self._embedding_init_failed = True
            LOGGER.warning("Embedding entity resolver unavailable: %s", exc)
            return None
        return self._embedding_resolver


def _init_tmmkg_entity_resolver() -> Any:
    root = Path(os.getenv("TMMKG_ROOT", str(DEFAULT_TMMKG_ROOT)))
    src_root = root / "src"
    src_root_text = str(src_root)
    if src_root_text not in sys.path:
        sys.path.insert(0, src_root_text)

    from TMMKG.services.entity_resolver import init_entity_resolver  # noqa: PLC0415

    config = _load_tmmkg_config()
    embedding_config = config.get("embedding", {}) if isinstance(config, dict) else {}
    resolver_config = config.get("entity_resolver", {}) if isinstance(config, dict) else {}
    infra_config = config.get("infra", {}) if isinstance(config, dict) else {}
    qdrant_config = infra_config.get("qdrant", {}) if isinstance(infra_config, dict) else {}

    return init_entity_resolver(
        model_name=os.getenv(
            "TMMKG_ENTITY_RESOLVER_MODEL_NAME",
            str(resolver_config.get("model_name") or "Qwen3-Embedding-8B"),
        ),
        model_root=os.getenv(
            "TMMKG_EMBEDDING_MODEL_ROOT",
            embedding_config.get("model_root"),
        ),
        base_collection=os.getenv(
            "TMMKG_ENTITY_RESOLVER_BASE_COLLECTION",
            str(resolver_config.get("base_collection") or "entity_aliases"),
        ),
        qdrant_url=os.getenv(
            "TMMKG_QDRANT_URL",
            str(qdrant_config.get("uri") or "http://localhost:6333"),
        ),
        score_threshold=float(
            os.getenv(
                "TMMKG_ENTITY_RESOLVER_SCORE_THRESHOLD",
                str(resolver_config.get("score_threshold") or 0.9),
            )
        ),
    )


def _load_tmmkg_config() -> dict[str, Any]:
    config_path = Path(os.getenv("TMMKG_CONFIG", str(DEFAULT_TMMKG_CONFIG)))
    if not config_path.exists():
        return {}
    try:
        import yaml  # noqa: PLC0415

        with config_path.open("r", encoding="utf-8") as file:
            data = yaml.safe_load(file)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        LOGGER.warning("Failed to load TMMKG config: %s", exc)
        return {}


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
