"""Helpers for offline pattern path result storage."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from config.settings import load_query_settings
from ..domain.item import GameNode
from ..domain.path_models import (
    PatientTasksetTaskGameTaskTasksetPatientPath,
)


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

    patient_id: str
    pattern: str
    ordered_training_dates: list[str] = field(default_factory=list)
    first_training_date: str | None = None
    last_training_date: str | None = None
    training_date_count: int = 0
    retrieval_context: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredPatternResult:
        """Build a typed result from a stored JSON mapping."""
        patient_id = _normalize_required_string(data.get("patient_id"), "patient_id")
        pattern = _normalize_required_string(data.get("pattern"), "pattern")
        ordered_training_dates = data.get("ordered_training_dates", [])
        retrieval_context = _normalize_retrieval_context(data)

        return cls(
            patient_id=patient_id,
            pattern=pattern,
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
        return {
            "patient_id": self.patient_id,
            "pattern": self.pattern,
            "ordered_training_dates": self.ordered_training_dates,
            "first_training_date": self.first_training_date,
            "last_training_date": self.last_training_date,
            "training_date_count": self.training_date_count,
            "retrieval_context": self.retrieval_context,
        }

    def to_domain_paths(self) -> list[PatientTasksetTaskGameTaskTasksetPatientPath]:
        """Convert stored raw path rows to typed domain path objects."""
        return [
            PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
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


def get_pattern_result_output_dir(query_config_path: str | Path, pattern: str) -> Path:
    """Return the output directory for a given pattern."""
    settings = load_query_settings(query_config_path)
    return Path(settings.pattern_path_storage.output_dir) / pattern


def get_patient_pattern_result_output_path(
    query_config_path: str | Path,
    pattern: str,
    patient_id: str,
) -> Path:
    """Return the bucketed JSON output path for one patient's pattern result."""
    normalized_pattern = _normalize_required_string(pattern, "pattern")
    normalized_patient_id = _normalize_required_string(patient_id, "patient_id")
    bucket = normalized_patient_id[:2] or "unknown"
    return (
        get_pattern_result_output_dir(query_config_path, normalized_pattern)
        / bucket
        / f"{normalized_patient_id}.json"
    )


class PatternResultStore:
    """Read and write patient-scoped pattern path result files."""

    def __init__(self, query_config_path: str | Path) -> None:
        self.query_config_path = query_config_path

    def save(self, result: StoredPatternResult | dict[str, Any]) -> Path:
        """Save one patient's result as a single JSON file, overwriting older data."""
        normalized_result = (
            result if isinstance(result, StoredPatternResult) else StoredPatternResult.from_dict(result)
        )
        output_path = get_patient_pattern_result_output_path(
            self.query_config_path,
            normalized_result.pattern,
            normalized_result.patient_id,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        serialized = json.dumps(
            normalized_result.to_dict(),
            ensure_ascii=False,
            default=str,
            indent=2,
        )
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f"{normalized_result.patient_id}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(serialized)
            temp_path = Path(temp_file.name)

        os.replace(temp_path, output_path)
        return output_path

    def load(self, pattern: str, patient_id: str) -> StoredPatternResult:
        """Load one patient's saved result."""
        output_path = get_patient_pattern_result_output_path(
            self.query_config_path,
            pattern,
            patient_id,
        )
        with output_path.open("r", encoding="utf-8") as file:
            return StoredPatternResult.from_dict(json.load(file))

    def iter_pattern_results(self, pattern: str) -> Iterator[StoredPatternResult]:
        """Yield all saved results for the given pattern."""
        pattern_dir = get_pattern_result_output_dir(self.query_config_path, pattern)
        if not pattern_dir.exists():
            return

        for path in sorted(pattern_dir.rglob("*.json")):
            with path.open("r", encoding="utf-8") as file:
                yield StoredPatternResult.from_dict(json.load(file))


def save_pattern_result(
    result: dict[str, Any],
    query_config_path: str | Path,
) -> Path:
    """Save a single patient pattern result using the default store."""
    return PatternResultStore(query_config_path).save(result)


def _normalize_required_string(value: object, field_name: str) -> str:
    """Normalize and validate a required string value."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _normalize_retrieval_context(data: dict[str, Any]) -> dict[str, Any] | None:
    """Normalize retrieval_context and keep backward compatibility with old payloads."""
    retrieval_context = data.get("retrieval_context")
    if isinstance(retrieval_context, dict):
        return {
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

    statistics = data.get("statistics")
    limit_recommendation = data.get("limit_recommendation")
    paths = data.get("paths")
    if statistics is None and limit_recommendation is None and not isinstance(paths, list):
        return None

    return {
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
