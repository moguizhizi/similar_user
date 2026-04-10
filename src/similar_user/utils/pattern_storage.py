"""Helpers for offline pattern path result storage."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config.settings import load_query_settings


def get_pattern_result_output_path(query_config_path: str | Path, pattern: str) -> Path:
    """Return the JSONL output path for a given pattern."""
    settings = load_query_settings(query_config_path)
    output_dir = Path(settings.pattern_path_storage.output_dir)
    return output_dir / f"{pattern}.jsonl"


def append_pattern_result(
    result: dict[str, Any],
    query_config_path: str | Path,
) -> Path:
    """Append a single patient pattern result to its pattern-specific JSONL file."""
    pattern = result.get("pattern")
    if not isinstance(pattern, str) or not pattern.strip():
        raise ValueError("result pattern must be a non-empty string.")

    output_path = get_pattern_result_output_path(query_config_path, pattern.strip())
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(result, ensure_ascii=False, default=str))
        file.write("\n")

    return output_path
