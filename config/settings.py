"""Configuration loading entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


@dataclass(frozen=True)
class Neo4jSettings:
    """Connection settings for a Neo4j database."""

    uri: str
    username: str
    password: str
    database: str = "neo4j"


@dataclass(frozen=True)
class QueryLimitBandSettings:
    """A single threshold band for query limit tuning."""

    per_g: int
    max_g_count: int | None = None


@dataclass(frozen=True)
class GraphPathLimitSettings:
    """Configuration for deriving graph traversal query limits."""

    bands: tuple[QueryLimitBandSettings, ...]
    per_g_strategy: str = "band"
    max_limit_source: str = "total_paths"


@dataclass(frozen=True)
class TrainingDateSplitSettings:
    """Configuration for splitting ordered training dates into two segments."""

    min_training_dates: int = 5
    before_ratio: int = 4
    after_ratio: int = 1


@dataclass(frozen=True)
class PatternPathStorageSettings:
    """Configuration for offline pattern path result storage."""

    output_dir: str = "data/pattern_paths"


@dataclass(frozen=True)
class QuerySettings:
    """Query-related tuning settings."""

    graph_path_limit: GraphPathLimitSettings
    training_date_split: TrainingDateSplitSettings
    pattern_path_storage: PatternPathStorageSettings


def load_yaml_config(config_path: str | Path) -> dict[str, Any]:
    """Load a YAML config file into a plain dictionary."""
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")

    return data


def load_neo4j_settings(config_path: str | Path) -> Neo4jSettings:
    """Load Neo4j settings from YAML."""
    data = load_yaml_config(config_path)

    required_fields = ("uri", "username", "password")
    missing_fields = [field for field in required_fields if not data.get(field)]
    if missing_fields:
        missing = ", ".join(missing_fields)
        raise ValueError(f"Missing required Neo4j settings: {missing}")

    return Neo4jSettings(
        uri=str(data["uri"]),
        username=str(data["username"]),
        password=str(data["password"]),
        database=str(data.get("database", "neo4j")),
    )


def load_query_settings(config_path: str | Path) -> QuerySettings:
    """Load query tuning settings from YAML."""
    data = load_yaml_config(config_path)

    graph_path_limit_data = data.get("graph_path_limit") or {}
    training_date_split_data = data.get("training_date_split") or {}
    pattern_path_storage_data = data.get("pattern_path_storage") or {}
    bands_data = graph_path_limit_data.get("bands") or []

    bands: list[QueryLimitBandSettings] = []
    for band_data in bands_data:
        if not isinstance(band_data, dict):
            raise ValueError("Each graph_path_limit band must be a mapping.")

        per_g = band_data.get("per_g")
        max_g_count = band_data.get("max_g_count")

        if not isinstance(per_g, int) or isinstance(per_g, bool) or per_g <= 0:
            raise ValueError("graph_path_limit bands must define a positive integer per_g.")
        if max_g_count is not None and (
            not isinstance(max_g_count, int)
            or isinstance(max_g_count, bool)
            or max_g_count < 0
        ):
            raise ValueError("graph_path_limit max_g_count must be a non-negative integer.")

        bands.append(QueryLimitBandSettings(per_g=per_g, max_g_count=max_g_count))

    if not bands:
        raise ValueError("graph_path_limit must define at least one band.")

    min_training_dates = training_date_split_data.get("min_training_dates", 5)
    before_ratio = training_date_split_data.get("before_ratio", 4)
    after_ratio = training_date_split_data.get("after_ratio", 1)

    for field_name, value in (
        ("min_training_dates", min_training_dates),
        ("before_ratio", before_ratio),
        ("after_ratio", after_ratio),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(
                f"training_date_split {field_name} must be a positive integer."
            )

    output_dir = pattern_path_storage_data.get("output_dir", "data/pattern_paths")
    if not isinstance(output_dir, str) or not output_dir.strip():
        raise ValueError("pattern_path_storage output_dir must be a non-empty string.")

    return QuerySettings(
        graph_path_limit=GraphPathLimitSettings(
            bands=tuple(bands),
            per_g_strategy=str(graph_path_limit_data.get("per_g_strategy", "band")),
            max_limit_source=str(
                graph_path_limit_data.get("max_limit_source", "total_paths")
            ),
        ),
        training_date_split=TrainingDateSplitSettings(
            min_training_dates=min_training_dates,
            before_ratio=before_ratio,
            after_ratio=after_ratio,
        ),
        pattern_path_storage=PatternPathStorageSettings(output_dir=output_dir.strip()),
    )
