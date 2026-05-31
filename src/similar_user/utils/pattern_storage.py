"""Helpers for offline pattern path result storage."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass, field, is_dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterator

from config.settings import load_query_settings, load_user_cache_settings
from ..data_access.user_cache_index import UserCacheEntry, UserCacheIndexStore
from ..data_access.pattern_registry import get_path_pattern_spec, resolve_path_pattern
from ..domain.graph_schema import PathPattern
from ..domain.item import GameNode
from ..domain.path_models import (
    DiseaseTasksetPatientPath,
    PatientTasksetDiseaseTasksetPatientPath,
    PatientTasksetSymptomTasksetPatientPath,
    PatientTasksetTaskGameTaskTasksetPatientPath,
    PatientTasksetUnknownTasksetPatientPath,
    SymptomTasksetPatientPath,
    UnknownTasksetPatientPath,
)
from .logger import get_logger
from .user_cache_paths import (
    files_root_from_sqlite_path,
    source_cache_leaf_dir,
)


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class StoredTrainingDateGames:
    """Post-split games grouped by one training date."""

    training_date: str
    games: list[GameNode] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredTrainingDateGames:
        """Build one training-date group from raw JSON content."""
        games = data.get("games", [])
        return cls(
            training_date=_normalize_required_string(
                data.get("trainingDate"),
                "post_split_games.trainingDate",
            ),
            games=[
                GameNode.from_dict(game)
                for game in games
                if isinstance(game, dict)
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable mapping for one training-date group."""
        return {
            "trainingDate": self.training_date,
            "games": [_game_node_to_dict(game) for game in self.games],
        }


@dataclass(frozen=True)
class StoredPatternStatistics:
    """Typed view of saved statistics, including post-split game groups."""

    split_training_date: str
    before_split: dict[str, Any]
    post_split_games: list[StoredTrainingDateGames] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredPatternStatistics:
        """Build statistics from raw JSON content."""
        post_split_games = data.get("post_split_games", [])
        before_split = data.get("before_split")
        return cls(
            split_training_date=_normalize_required_string(
                data.get("split_training_date"),
                "statistics.split_training_date",
            ),
            before_split=before_split if isinstance(before_split, dict) else {},
            post_split_games=[
                StoredTrainingDateGames.from_dict(group)
                for group in post_split_games
                if isinstance(group, dict)
            ],
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable mapping for saved statistics."""
        return {
            "split_training_date": self.split_training_date,
            "before_split": self.before_split,
            "post_split_games": [group.to_dict() for group in self.post_split_games],
        }


@dataclass(frozen=True)
class StoredPatternResult:
    """Typed view of one saved patient pattern result."""

    source_id: str
    source_parameter: str
    pattern: str
    patient_id: str | None = None
    ordered_training_dates: list[str] = field(default_factory=list)
    first_training_date: str | None = None
    last_training_date: str | None = None
    training_date_count: int = 0
    retrieval_context: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredPatternResult:
        """Build a typed result from a stored JSON mapping."""
        pattern = _normalize_required_string(data.get("pattern"), "pattern")
        source_parameter = _normalize_source_parameter(data)
        source_id = _normalize_source_id(data, source_parameter)
        patient_id = _optional_string(data.get("patient_id"))
        if patient_id is None and source_parameter == "patient_id":
            patient_id = source_id
        ordered_training_dates = data.get("ordered_training_dates", [])
        retrieval_context = _normalize_retrieval_context(data)

        return cls(
            source_id=source_id,
            source_parameter=source_parameter,
            pattern=pattern,
            patient_id=patient_id,
            ordered_training_dates=[str(value) for value in ordered_training_dates]
            if isinstance(ordered_training_dates, list)
            else [],
            first_training_date=(
                str(data["first_training_date"])
                if data.get("first_training_date") is not None
                else None
            ),
            last_training_date=(
                str(data["last_training_date"])
                if data.get("last_training_date") is not None
                else None
            ),
            training_date_count=int(data.get("training_date_count", 0) or 0),
            retrieval_context=retrieval_context,
        )

    def to_dict(self) -> dict[str, Any]:
        """Return the JSON-serializable mapping for the stored result."""
        result = {
            "source_id": self.source_id,
            "source_parameter": self.source_parameter,
            "pattern": self.pattern,
            "ordered_training_dates": self.ordered_training_dates,
            "first_training_date": self.first_training_date,
            "last_training_date": self.last_training_date,
            "training_date_count": self.training_date_count,
            "retrieval_context": self.retrieval_context,
        }
        result[self.source_parameter] = self.source_id
        if self.patient_id is not None:
            result["patient_id"] = self.patient_id
        return result

    def to_domain_paths(
        self,
    ) -> list[
        PatientTasksetTaskGameTaskTasksetPatientPath
        | PatientTasksetDiseaseTasksetPatientPath
        | PatientTasksetSymptomTasksetPatientPath
        | PatientTasksetUnknownTasksetPatientPath
        | DiseaseTasksetPatientPath
        | SymptomTasksetPatientPath
        | UnknownTasksetPatientPath
    ]:
        """Convert stored raw path rows to typed domain path objects."""
        pattern = resolve_path_pattern(self.pattern)
        if pattern == PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT:
            path_cls = PatientTasksetTaskGameTaskTasksetPatientPath
        elif pattern == PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT:
            path_cls = PatientTasksetDiseaseTasksetPatientPath
        elif pattern == PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT:
            path_cls = PatientTasksetSymptomTasksetPatientPath
        elif pattern == PathPattern.PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT:
            path_cls = PatientTasksetUnknownTasksetPatientPath
        elif pattern == PathPattern.DISEASE_TASKSET_PATIENT:
            path_cls = DiseaseTasksetPatientPath
        elif pattern == PathPattern.SYMPTOM_TASKSET_PATIENT:
            path_cls = SymptomTasksetPatientPath
        elif pattern == PathPattern.UNKNOWN_TASKSET_PATIENT:
            path_cls = UnknownTasksetPatientPath
        else:
            raise ValueError(f"Unsupported stored pattern: {self.pattern}")

        return [
            path_cls.from_dict(
                {
                    **path,
                    "pattern": self.pattern,
                }
            )
            for path in self.paths
        ]

    def to_stored_statistics(self) -> StoredPatternStatistics | None:
        """Convert stored raw statistics to a typed statistics object."""
        if self.statistics is None:
            return None
        return StoredPatternStatistics.from_dict(self.statistics)

    @property
    def statistics(self) -> dict[str, Any] | None:
        """Compatibility accessor for statistics derived from retrieval_context."""
        if not isinstance(self.retrieval_context, dict):
            return None
        split_training_date = self.retrieval_context.get("split_training_date")
        before_split = self.retrieval_context.get("before_split")
        post_split_games = self.retrieval_context.get("post_split_games")
        if split_training_date is None and before_split is None and post_split_games in (None, []):
            return None
        return {
            "split_training_date": split_training_date,
            "before_split": before_split if isinstance(before_split, dict) else {},
            "post_split_games": post_split_games if isinstance(post_split_games, list) else [],
        }

    @property
    def limit_recommendation(self) -> dict[str, Any] | None:
        """Compatibility accessor for limit recommendation stored in retrieval_context."""
        if not isinstance(self.retrieval_context, dict):
            return None
        value = self.retrieval_context.get("limit_recommendation")
        return value if isinstance(value, dict) or value is None else None

    @property
    def paths(self) -> list[dict[str, Any]]:
        """Compatibility accessor for paths stored in retrieval_context."""
        if not isinstance(self.retrieval_context, dict):
            return []
        value = self.retrieval_context.get("paths")
        return value if isinstance(value, list) else []


def get_pattern_result_output_dir(
    config_path: str | Path,
    pattern: str,
    *,
    path_key: str | None = None,
) -> Path:
    """Return the output directory for a given pattern."""
    settings = load_query_settings(config_path)
    normalized_pattern = resolve_path_pattern(pattern)
    base_dir = Path(settings.pattern_path_storage.output_dir)
    normalized_path_key = _normalize_required_string(path_key, "path_key")
    return base_dir / normalized_path_key / normalized_pattern.value


def get_pattern_result_output_path(
    config_path: str | Path,
    pattern: str,
    source_id: str,
    *,
    path_key: str | None = None,
) -> Path:
    """Return the bucketed JSON output path for one pattern source."""
    normalized_pattern = _normalize_required_string(pattern, "pattern")
    normalized_source_id = _normalize_required_string(source_id, "source_id")
    resolved_pattern = resolve_path_pattern(normalized_pattern).value
    settings = load_user_cache_settings(config_path)
    if settings.enabled:
        path_key_value = _normalize_required_string(path_key, "path_key")
        source_parameter = get_path_pattern_spec(resolved_pattern).source_parameter
        source_type = _source_type_from_parameter(source_parameter)
        query_family, window_days, config_hash, base_date = _path_parts_from_key(
            path_key_value,
            default_query_family="direct_entity"
            if source_type != "patient"
            else "default",
        )
        output_base = source_cache_leaf_dir(
            files_root_from_sqlite_path(settings.sqlite_path),
            source_type=source_type,
            source_id=normalized_source_id,
            pattern=resolved_pattern,
            cache_type="raw_paths",
            query_family=query_family,
            window_days=window_days,
            config_hash=build_raw_path_user_cache_config_hash(path_key_value),
            cached_base_date=base_date,
        )
        return output_base / f"{_slug_part(resolved_pattern)}.json"
    return get_legacy_pattern_result_output_path(
        config_path,
        normalized_pattern,
        normalized_source_id,
        path_key=path_key,
    )


def get_legacy_pattern_result_output_path(
    config_path: str | Path,
    pattern: str,
    source_id: str,
    *,
    path_key: str | None = None,
) -> Path:
    """Return the pre-user-cache bucketed output path for one pattern source."""
    normalized_pattern = _normalize_required_string(pattern, "pattern")
    normalized_source_id = _normalize_required_string(source_id, "source_id")
    bucket = normalized_source_id[:2] or "unknown"
    return (
        get_pattern_result_output_dir(
            config_path,
            normalized_pattern,
            path_key=path_key,
        )
        / bucket
        / f"{normalized_source_id}.json"
    )


class PatternResultStore:
    """Read and write source-scoped pattern path result files."""

    def __init__(self, config_path: str | Path) -> None:
        self.config_path = config_path

    def save(self, result: StoredPatternResult | dict[str, Any]) -> Path:
        """Save one source result as a single JSON file, overwriting older data."""
        normalized_result = (
            result if isinstance(result, StoredPatternResult) else StoredPatternResult.from_dict(result)
        )
        path_context = build_path_cache_context(
            self.config_path,
            normalized_result.retrieval_context,
        )
        result_payload = _with_path_cache_context(normalized_result, path_context)
        output_path = get_pattern_result_output_path(
            self.config_path,
            result_payload.pattern,
            result_payload.source_id,
            path_key=path_context["path_key"],
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        serialized = json.dumps(
            result_payload.to_dict(),
            ensure_ascii=False,
            default=str,
            indent=2,
        )
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f"{normalized_result.source_id}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(serialized)
            temp_path = Path(temp_file.name)

        os.replace(temp_path, output_path)
        LOGGER.debug(
            "Saved pattern result: source_id=%s, source_parameter=%s, pattern=%s, path_count=%s, output_path=%s",
            result_payload.source_id,
            result_payload.source_parameter,
            result_payload.pattern,
            len(result_payload.paths),
            output_path,
        )
        _register_raw_path_user_cache(
            self.config_path,
            result_payload,
            output_path,
            path_context=path_context,
        )
        return output_path

    def save_with_path_context(
        self,
        result: StoredPatternResult | dict[str, Any],
        *,
        path_context: dict[str, Any],
    ) -> Path:
        """Save one source result using a caller-supplied cache context."""
        normalized_result = (
            result if isinstance(result, StoredPatternResult) else StoredPatternResult.from_dict(result)
        )
        path_key = _normalize_required_string(path_context.get("path_key"), "path_key")
        result_payload = _with_path_cache_context(normalized_result, path_context)
        output_path = get_pattern_result_output_path(
            self.config_path,
            result_payload.pattern,
            result_payload.source_id,
            path_key=path_key,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        serialized = json.dumps(
            result_payload.to_dict(),
            ensure_ascii=False,
            default=str,
            indent=2,
        )
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f"{normalized_result.source_id}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(serialized)
            temp_path = Path(temp_file.name)

        os.replace(temp_path, output_path)
        LOGGER.debug(
            "Saved pattern result with explicit path context: source_id=%s, source_parameter=%s, pattern=%s, path_count=%s, output_path=%s",
            result_payload.source_id,
            result_payload.source_parameter,
            result_payload.pattern,
            len(result_payload.paths),
            output_path,
        )
        _register_raw_path_user_cache(
            self.config_path,
            result_payload,
            output_path,
            path_context=path_context,
        )
        return output_path

    def load(
        self,
        pattern: str,
        source_id: str,
        *,
        base_date: str | None = None,
        query_family: str | None = None,
    ) -> StoredPatternResult:
        """Load one saved result by source ID."""
        path_key = build_path_key(
            self.config_path,
            base_date=base_date,
            query_family=query_family,
        )
        output_path = get_pattern_result_output_path(
            self.config_path,
            pattern,
            source_id,
            path_key=path_key,
        )
        with output_path.open("r", encoding="utf-8") as file:
            result = StoredPatternResult.from_dict(json.load(file))
        validate_path_cache_context(result.retrieval_context, expected_path_key=path_key)
        LOGGER.debug(
            "Loaded pattern result: source_id=%s, source_parameter=%s, pattern=%s, path_count=%s, input_path=%s",
            result.source_id,
            result.source_parameter,
            result.pattern,
            len(result.paths),
            output_path,
        )
        return result

    def iter_pattern_results(
        self,
        pattern: str,
        *,
        path_key: str | None = None,
    ) -> Iterator[StoredPatternResult]:
        """Yield all saved results for the given pattern."""
        pattern_dir = get_pattern_result_output_dir(
            self.config_path,
            pattern,
            path_key=path_key,
        )
        if not pattern_dir.exists():
            return

        for path in sorted(pattern_dir.rglob("*.json")):
            with path.open("r", encoding="utf-8") as file:
                result = StoredPatternResult.from_dict(json.load(file))
            LOGGER.debug(
                "Loaded pattern result from iterator: source_id=%s, source_parameter=%s, pattern=%s, input_path=%s",
                result.source_id,
                result.source_parameter,
                result.pattern,
                path,
            )
            yield result


def save_pattern_result(
    result: dict[str, Any],
    config_path: str | Path,
) -> Path:
    """Save a single patient pattern result using the default store."""
    return PatternResultStore(config_path).save(result)


def save_direct_pattern_result(
    result: dict[str, Any],
    config_path: str | Path,
    *,
    path_context: dict[str, Any],
) -> Path:
    """Save a direct entity-start pattern result with an explicit cache context."""
    return PatternResultStore(config_path).save_with_path_context(
        result,
        path_context=path_context,
    )


def build_path_key(
    config_path: str | Path,
    *,
    base_date: str | None,
    query_family: str | None,
) -> str:
    """Build a filesystem-safe cache key for raw pattern path results."""
    normalized_base_date = _normalize_required_string(base_date, "base_date")
    resolved_window_days = _resolve_patient_path_window_days(config_path)
    graph_path_limit_hash = _short_hash(
        {"graph_path_limit": _graph_path_limit_config_payload(config_path)}
    )
    normalized_query_family = _normalize_query_family_for_key(query_family)
    return (
        f"base_{_slug_part(normalized_base_date)}"
        f"_window_{resolved_window_days}"
        f"_qf_{normalized_query_family}"
        f"_pathcfg_{graph_path_limit_hash}"
    )


def build_direct_path_key(
    *,
    base_date: str,
    window_days: int,
    direct_path_limit: int,
) -> str:
    """Build a filesystem-safe cache key for direct entity-start path results."""
    normalized_base_date = _normalize_required_string(base_date, "base_date")
    if not isinstance(window_days, int) or isinstance(window_days, bool) or window_days <= 0:
        raise ValueError("window_days must be a positive integer.")
    if (
        not isinstance(direct_path_limit, int)
        or isinstance(direct_path_limit, bool)
        or direct_path_limit <= 0
    ):
        raise ValueError("direct_path_limit must be a positive integer.")
    direct_config_hash = _short_hash(
        {"direct_path": {"direct_path_limit": direct_path_limit}}
    )
    return (
        f"base_{_slug_part(normalized_base_date)}"
        f"_window_{window_days}"
        f"_directcfg_{direct_config_hash}"
    )


def build_path_cache_context(
    config_path: str | Path,
    retrieval_context: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build cache metadata from a stored result retrieval context."""
    base_date = None
    window_days = None
    query_family = None
    if isinstance(retrieval_context, dict):
        raw_base_date = retrieval_context.get("base_date")
        base_date = str(raw_base_date) if raw_base_date is not None else None
        raw_path_window = retrieval_context.get("path_window")
        window_days = _extract_window_days(raw_path_window)
        raw_query_family = retrieval_context.get("query_family")
        query_family = str(raw_query_family) if raw_query_family is not None else None
    if base_date is None:
        raise ValueError("retrieval_context.base_date must be present for path cache key.")
    if window_days is None:
        raise ValueError(
            "retrieval_context.path_window must include a valid start_date/end_date "
            "for path cache key."
        )

    graph_path_limit = _graph_path_limit_config_payload(config_path)
    path_config_hash = _short_hash({"graph_path_limit": graph_path_limit})
    path_key = build_path_key(
        config_path,
        base_date=base_date,
        query_family=query_family,
    )
    return {
        "cache_type": "pattern_paths",
        "path_key": path_key,
        "base_date": base_date,
        "window_days": window_days,
        "query_family": _normalize_query_family_for_key(query_family),
        "path_config_hash": path_config_hash,
        "path_config": {"graph_path_limit": graph_path_limit},
    }


def build_raw_path_user_cache_context(
    config_path: str | Path,
    *,
    source_id: str,
    source_parameter: str,
    path_cache_context: dict[str, Any],
) -> dict[str, Any]:
    """Build source-centered cache metadata for raw path results."""
    settings = load_user_cache_settings(config_path)
    if not settings.enabled:
        return {"enabled": False, "cache_type": "raw_paths"}
    path_key = _normalize_required_string(path_cache_context.get("path_key"), "path_key")
    query_family = _normalize_required_string(
        path_cache_context.get("query_family") or "direct_entity",
        "query_family",
    )
    source_type = _source_type_from_parameter(source_parameter)
    valid_days = (
        settings.patient_raw_paths_valid_days
        if source_type == "patient"
        else settings.direct_raw_paths_valid_days
    )
    return {
        "enabled": True,
        "cache_type": "raw_paths",
        "sqlite_path": settings.sqlite_path,
        "patient_id": _normalize_required_string(source_id, "source_id"),
        "source_type": source_type,
        "source_id": _normalize_required_string(source_id, "source_id"),
        "query_family": query_family,
        "window_days": _normalize_positive_int(
            path_cache_context.get("window_days"),
            "window_days",
        ),
        "config_hash": build_raw_path_user_cache_config_hash(path_key),
        "cached_base_date": _normalize_required_string(
            path_cache_context.get("base_date"),
            "base_date",
        ),
        "valid_days": valid_days,
        "path_key": path_key,
        "path_config_hash": path_cache_context.get("path_config_hash"),
    }


def build_raw_path_user_cache_config_hash(path_key: str) -> str:
    """Build the base-date-independent user-cache hash for raw paths."""
    normalized_path_key = _normalize_required_string(path_key, "path_key")
    return _short_hash(
        {
            "cache_type": "raw_paths",
            "cache_key_without_base_date": _strip_base_date_from_key(
                normalized_path_key
            ),
        }
    )


def build_direct_path_cache_context(
    *,
    base_date: str,
    window_days: int,
    direct_path_limit: int,
) -> dict[str, Any]:
    """Build cache metadata for direct entity-start pattern path results."""
    path_key = build_direct_path_key(
        base_date=base_date,
        window_days=window_days,
        direct_path_limit=direct_path_limit,
    )
    return {
        "cache_type": "direct_pattern_paths",
        "path_key": path_key,
        "base_date": _normalize_required_string(base_date, "base_date"),
        "window_days": window_days,
        "direct_path_limit": direct_path_limit,
        "direct_config": {"direct_path_limit": direct_path_limit},
    }


def validate_path_cache_context(
    retrieval_context: dict[str, Any] | None,
    *,
    expected_path_key: str,
) -> None:
    """Raise if stored path cache metadata does not match the expected key."""
    cache_context = (
        retrieval_context.get("cache_context")
        if isinstance(retrieval_context, dict)
        else None
    )
    if not isinstance(cache_context, dict):
        raise ValueError(
            f"Stored pattern result is missing cache_context for path_key={expected_path_key}."
        )
    stored_path_key = cache_context.get("path_key")
    if stored_path_key != expected_path_key:
        raise ValueError(
            "Stored pattern result cache key mismatch: "
            f"expected={expected_path_key}, actual={stored_path_key}."
        )


def _normalize_required_string(value: object, field_name: str) -> str:
    """Normalize and validate a required string value."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _with_path_cache_context(
    result: StoredPatternResult,
    path_context: dict[str, Any],
) -> StoredPatternResult:
    retrieval_context = dict(result.retrieval_context or {})
    retrieval_context["cache_context"] = path_context
    return StoredPatternResult(
        source_id=result.source_id,
        source_parameter=result.source_parameter,
        pattern=result.pattern,
        patient_id=result.patient_id,
        ordered_training_dates=result.ordered_training_dates,
        first_training_date=result.first_training_date,
        last_training_date=result.last_training_date,
        training_date_count=result.training_date_count,
        retrieval_context=retrieval_context,
    )


def _register_raw_path_user_cache(
    config_path: str | Path,
    result: StoredPatternResult,
    output_path: Path,
    *,
    path_context: dict[str, Any],
) -> None:
    user_cache_context = build_raw_path_user_cache_context(
        config_path,
        source_id=result.source_id,
        source_parameter=result.source_parameter,
        path_cache_context=path_context,
    )
    if not user_cache_context.get("enabled"):
        return
    store = UserCacheIndexStore(
        _normalize_required_string(user_cache_context.get("sqlite_path"), "sqlite_path")
    )
    entry = UserCacheEntry(
        cache_type="raw_paths",
        patient_id=_normalize_required_string(
            user_cache_context.get("patient_id"),
            "patient_id",
        ),
        query_family=_normalize_required_string(
            user_cache_context.get("query_family"),
            "query_family",
        ),
        window_days=_normalize_positive_int(
            user_cache_context.get("window_days"),
            "window_days",
        ),
        config_hash=_normalize_required_string(
            user_cache_context.get("config_hash"),
            "config_hash",
        ),
        cached_base_date=_normalize_required_string(
            user_cache_context.get("cached_base_date"),
            "cached_base_date",
        ),
        valid_days=_normalize_non_negative_int(
            user_cache_context.get("valid_days"),
            "valid_days",
        ),
        data_path=str(output_path),
        payload={
            "path_key": _normalize_required_string(
                user_cache_context.get("path_key"),
                "path_key",
            ),
            "pattern": result.pattern,
            "path_config_hash": user_cache_context.get("path_config_hash"),
            "source_type": user_cache_context.get("source_type"),
            "source_id": user_cache_context.get("source_id"),
        },
        source_type=_normalize_required_string(
            user_cache_context.get("source_type"),
            "source_type",
        ),
        source_id=_normalize_required_string(
            user_cache_context.get("source_id"),
            "source_id",
        ),
    )
    store.upsert_entry(entry)
    LOGGER.info(
        "Registered raw paths in user cache: patient_id=%s, query_family=%s, cached_base_date=%s, path_key=%s, data_path=%s",
        entry.patient_id,
        entry.query_family,
        entry.cached_base_date,
        entry.payload["path_key"],
        entry.data_path,
    )


def _source_type_from_parameter(source_parameter: str) -> str:
    normalized = _normalize_required_string(source_parameter, "source_parameter")
    if normalized == "patient_id":
        return "patient"
    if normalized.endswith("_id"):
        return normalized[:-3]
    return normalized


def _graph_path_limit_config_payload(config_path: str | Path) -> dict[str, Any]:
    settings = load_query_settings(config_path).graph_path_limit
    return _to_plain_data(settings)


def _to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return _to_plain_data(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_plain_data(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_to_plain_data(item) for item in value]
    return value


def _short_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:8]


def _normalize_query_family_for_key(query_family: str | None) -> str:
    if query_family is None or not str(query_family).strip():
        return "default"
    return _slug_part(str(query_family).strip())


def _strip_base_date_from_key(value: str) -> str:
    parts = value.split("_", 2)
    if len(parts) == 3 and parts[0] == "base":
        return parts[2]
    return value


def _path_parts_from_key(
    path_key: str,
    *,
    default_query_family: str,
) -> tuple[str, int, str, str]:
    normalized_path_key = _normalize_required_string(path_key, "path_key")
    parts = normalized_path_key.split("_")
    base_date = _extract_key_value(parts, "base")
    window_days = _parse_positive_int(_extract_key_value(parts, "window"), "window")
    query_family = (
        _extract_key_slice(parts, "qf", ("pathcfg", "directcfg"))
        or default_query_family
    )
    config_hash = (
        _extract_key_value(parts, "pathcfg")
        or _extract_key_value(parts, "directcfg")
        or build_raw_path_user_cache_config_hash(normalized_path_key)
    )
    return query_family, window_days, config_hash, base_date


def _extract_key_value(parts: list[str], marker: str) -> str:
    for index, part in enumerate(parts[:-1]):
        if part == marker:
            return parts[index + 1]
    return ""


def _extract_key_slice(
    parts: list[str],
    start_marker: str,
    end_markers: tuple[str, ...],
) -> str:
    try:
        start_index = parts.index(start_marker) + 1
    except ValueError:
        return ""
    end_index = len(parts)
    for marker in end_markers:
        if marker in parts[start_index:]:
            marker_index = parts.index(marker, start_index)
            end_index = min(end_index, marker_index)
    return "_".join(parts[start_index:end_index]).strip("_")


def _parse_positive_int(value: str, field_name: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a positive integer.") from exc
    return _normalize_positive_int(parsed, field_name)


def _slug_part(value: object) -> str:
    text = str(value).strip().lower()
    slug = []
    for char in text:
        if char.isalnum():
            slug.append(char)
        elif char in ("-", "_"):
            slug.append(char)
        else:
            slug.append("-")
    return "".join(slug).strip("-") or "none"


def _extract_window_days(path_window: object) -> int | None:
    if not isinstance(path_window, dict):
        return None
    start_date = _parse_iso_date(path_window.get("start_date"))
    end_date = _parse_iso_date(path_window.get("end_date"))
    if start_date is None or end_date is None:
        return None
    delta = end_date - start_date
    return delta.days if delta.days > 0 else None


def _resolve_patient_path_window_days(
    config_path: str | Path,
) -> int:
    return load_query_settings(config_path).patient_path.window_days


def _normalize_positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _normalize_non_negative_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _parse_iso_date(value: object) -> date | None:
    if value is None:
        return None
    try:
        return date.fromisoformat(str(value))
    except ValueError:
        return None


def _normalize_source_parameter(data: dict[str, Any]) -> str:
    """Return the semantic ID field name for a stored pattern result."""
    raw_source_parameter = data.get("source_parameter")
    if isinstance(raw_source_parameter, str) and raw_source_parameter.strip():
        return raw_source_parameter.strip()

    pattern = _normalize_required_string(data.get("pattern"), "pattern")
    return get_path_pattern_spec(pattern).source_parameter


def _normalize_source_id(data: dict[str, Any], source_parameter: str) -> str:
    """Return the stored source ID from unified or semantic ID fields."""
    source_id = data.get("source_id")
    if isinstance(source_id, str) and source_id.strip():
        return source_id.strip()

    semantic_id = data.get(source_parameter)
    if isinstance(semantic_id, str) and semantic_id.strip():
        return semantic_id.strip()

    patient_id = data.get("patient_id")
    if isinstance(patient_id, str) and patient_id.strip():
        return patient_id.strip()

    raise ValueError(f"{source_parameter} or source_id must be a non-empty string.")


def _normalize_retrieval_context(data: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize retrieval_context and keep backward compatibility with old payloads."""
    retrieval_context = data.get("retrieval_context")
    if isinstance(retrieval_context, dict):
        normalized_context = {
            "split_training_date": (
                str(retrieval_context["split_training_date"])
                if retrieval_context.get("split_training_date") is not None
                else None
            ),
            "before_split": retrieval_context.get("before_split")
            if isinstance(retrieval_context.get("before_split"), dict)
            or retrieval_context.get("before_split") is None
            else None,
            "post_split_games": retrieval_context.get("post_split_games")
            if isinstance(retrieval_context.get("post_split_games"), list)
            else [],
            "limit_recommendation": retrieval_context.get("limit_recommendation")
            if isinstance(retrieval_context.get("limit_recommendation"), dict)
            or retrieval_context.get("limit_recommendation") is None
            else None,
            "paths": retrieval_context.get("paths")
            if isinstance(retrieval_context.get("paths"), list)
            else [],
        }
        if "base_date" in retrieval_context:
            normalized_context["base_date"] = (
                str(retrieval_context["base_date"])
                if retrieval_context.get("base_date") is not None
                else None
            )
        if "path_window" in retrieval_context:
            normalized_context["path_window"] = (
                retrieval_context.get("path_window")
                if isinstance(retrieval_context.get("path_window"), dict)
                else None
            )
        if "window_statistics" in retrieval_context:
            normalized_context["window_statistics"] = (
                retrieval_context.get("window_statistics")
                if isinstance(retrieval_context.get("window_statistics"), dict)
                else None
            )
        if "query_family" in retrieval_context:
            normalized_context["query_family"] = (
                str(retrieval_context["query_family"])
                if retrieval_context.get("query_family") is not None
                else None
            )
        if "cache_context" in retrieval_context:
            normalized_context["cache_context"] = (
                retrieval_context.get("cache_context")
                if isinstance(retrieval_context.get("cache_context"), dict)
                else None
            )
        return normalized_context

    statistics = data.get("statistics")
    limit_recommendation = data.get("limit_recommendation")
    paths = data.get("paths")
    if statistics is None and limit_recommendation is None and not isinstance(paths, list):
        return None

    normalized_context = {
        "split_training_date": (
            statistics.get("split_training_date")
            if isinstance(statistics, dict)
            else None
        ),
        "before_split": statistics.get("before_split")
        if isinstance(statistics, dict) and isinstance(statistics.get("before_split"), dict)
        else {},
        "post_split_games": statistics.get("post_split_games")
        if isinstance(statistics, dict) and isinstance(statistics.get("post_split_games"), list)
        else [],
        "limit_recommendation": limit_recommendation
        if isinstance(limit_recommendation, dict) or limit_recommendation is None
        else None,
        "paths": paths if isinstance(paths, list) else [],
    }
    if isinstance(statistics, dict) and "base_date" in statistics:
        normalized_context["base_date"] = statistics.get("base_date")
    if isinstance(statistics, dict) and "path_window" in statistics:
        normalized_context["path_window"] = (
            statistics.get("path_window")
            if isinstance(statistics.get("path_window"), dict)
            else None
        )
    if isinstance(statistics, dict) and "window_statistics" in statistics:
        normalized_context["window_statistics"] = (
            statistics.get("window_statistics")
            if isinstance(statistics.get("window_statistics"), dict)
            else None
        )
    return normalized_context


def _optional_string(value: object) -> str | None:
    """Normalize an optional string value."""
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    return value


def _game_node_to_dict(game: GameNode) -> dict[str, Any]:
    """Convert a game node to a JSON-serializable mapping without dropping known fields."""
    return {
        field_name: field_value
        for field_name, field_value in game.__dict__.items()
        if field_value is not None
    }
