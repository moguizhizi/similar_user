"""Helpers for offline pattern path result storage."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterator

from config.settings import load_query_settings


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

    def save(self, result: dict[str, Any]) -> Path:
        """Save one patient's result as a single JSON file, overwriting older data."""
        pattern = _normalize_required_string(result.get("pattern"), "pattern")
        patient_id = _normalize_required_string(result.get("patient_id"), "patient_id")
        output_path = get_patient_pattern_result_output_path(
            self.query_config_path,
            pattern,
            patient_id,
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)

        serialized = json.dumps(result, ensure_ascii=False, default=str, indent=2)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=output_path.parent,
            prefix=f"{patient_id}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_file.write(serialized)
            temp_path = Path(temp_file.name)

        os.replace(temp_path, output_path)
        return output_path

    def load(self, pattern: str, patient_id: str) -> dict[str, Any]:
        """Load one patient's saved result."""
        output_path = get_patient_pattern_result_output_path(
            self.query_config_path,
            pattern,
            patient_id,
        )
        with output_path.open("r", encoding="utf-8") as file:
            return json.load(file)

    def iter_pattern_results(self, pattern: str) -> Iterator[dict[str, Any]]:
        """Yield all saved results for the given pattern."""
        pattern_dir = get_pattern_result_output_dir(self.query_config_path, pattern)
        if not pattern_dir.exists():
            return

        for path in sorted(pattern_dir.rglob("*.json")):
            with path.open("r", encoding="utf-8") as file:
                yield json.load(file)


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
