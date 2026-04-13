"""Helpers for offline pattern path result storage."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterator

from config.settings import load_query_settings
from ..domain.path_models import (
    PatientTasksetTaskGameTaskTasksetPatientPath,
)


@dataclass(frozen=True)
class StoredPatternResult:
    """Typed view of one saved patient pattern result."""

    patient_id: str
    pattern: str
    ordered_training_dates: list[str] = field(default_factory=list)
    first_training_date: str | None = None
    last_training_date: str | None = None
    training_date_count: int = 0
    statistics: dict[str, Any] | None = None
    limit_recommendation: dict[str, Any] | None = None
    paths: list[dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> StoredPatternResult:
        """Build a typed result from a stored JSON mapping."""
        patient_id = _normalize_required_string(data.get("patient_id"), "patient_id")
        pattern = _normalize_required_string(data.get("pattern"), "pattern")
        ordered_training_dates = data.get("ordered_training_dates", [])
        paths = data.get("paths", [])

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
            statistics=data.get("statistics")
            if isinstance(data.get("statistics"), dict) or data.get("statistics") is None
            else None,
            limit_recommendation=data.get("limit_recommendation")
            if isinstance(data.get("limit_recommendation"), dict)
            or data.get("limit_recommendation") is None
            else None,
            paths=paths if isinstance(paths, list) else [],
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
            "statistics": self.statistics,
            "limit_recommendation": self.limit_recommendation,
            "paths": self.paths,
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
