"""Configuration loading entrypoints."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")


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
class CandidateRankingSettings:
    """Configuration for ranking similar-user candidates from scored paths."""

    path_top_k: int = 50
    candidate_top_k: int = 10


@dataclass(frozen=True)
class LlmSettings:
    """Connection settings for an OpenAI-compatible chat-completions service."""

    base_url: str
    model: str
    api_key: str | None = None
    timeout: int = 60
    max_retries: int = 3
    backoff_factor: float = 1.5


@dataclass(frozen=True)
class QuerySettings:
    """Query-related tuning settings."""

    graph_path_limit: GraphPathLimitSettings
    training_date_split: TrainingDateSplitSettings
    pattern_path_storage: PatternPathStorageSettings
    candidate_ranking: CandidateRankingSettings


def load_yaml_config(config_path: str | Path) -> dict[str, Any]:
    """Load a YAML config file into a plain dictionary."""
    path = Path(config_path)
    with path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")

    return data


def _extract_config_section(
    data: dict[str, Any],
    section_name: str,
) -> dict[str, Any]:
    """Return a named config section, falling back to legacy flat mappings."""
    section_data = data.get(section_name)
    if section_data is None:
        return data
    if not isinstance(section_data, dict):
        raise ValueError(f"{section_name} config section must be a mapping.")
    return section_data


def load_neo4j_settings(config_path: str | Path) -> Neo4jSettings:
    """Load Neo4j settings from YAML."""
    data = _extract_config_section(load_yaml_config(config_path), "neo4j")

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


def load_llm_settings(config_path: str | Path) -> LlmSettings:
    """Load OpenAI-compatible LLM settings from YAML."""
    data = _extract_config_section(load_yaml_config(config_path), "llm")

    base_url = data.get("base_url")
    model = data.get("model")
    if not isinstance(base_url, str) or not base_url.strip():
        raise ValueError("llm base_url must be a non-empty string.")
    if not isinstance(model, str) or not model.strip():
        raise ValueError("llm model must be a non-empty string.")

    timeout = data.get("timeout", 60)
    max_retries = data.get("max_retries", 3)
    backoff_factor = data.get("backoff_factor", 1.5)

    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout <= 0:
        raise ValueError("llm timeout must be a positive integer.")
    if (
        not isinstance(max_retries, int)
        or isinstance(max_retries, bool)
        or max_retries <= 0
    ):
        raise ValueError("llm max_retries must be a positive integer.")
    if not isinstance(backoff_factor, (int, float)) or isinstance(
        backoff_factor,
        bool,
    ):
        raise ValueError("llm backoff_factor must be a non-negative number.")
    if float(backoff_factor) < 0:
        raise ValueError("llm backoff_factor must be a non-negative number.")

    configured_api_key = data.get("api_key")
    api_key = os.getenv("SIMILAR_USER_LLM_API_KEY")
    if api_key is None and isinstance(configured_api_key, str):
        api_key = configured_api_key
    if api_key is not None:
        api_key = api_key.strip() or None

    return LlmSettings(
        base_url=base_url.strip(),
        model=model.strip(),
        api_key=api_key,
        timeout=timeout,
        max_retries=max_retries,
        backoff_factor=float(backoff_factor),
    )


def load_query_settings(config_path: str | Path) -> QuerySettings:
    """Load query tuning settings from YAML."""
    data = _extract_config_section(load_yaml_config(config_path), "query")

    graph_path_limit_data = data.get("graph_path_limit") or {}
    training_date_split_data = data.get("training_date_split") or {}
    pattern_path_storage_data = data.get("pattern_path_storage") or {}
    candidate_ranking_data = data.get("candidate_ranking") or {}
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

    path_top_k = candidate_ranking_data.get("path_top_k", 50)
    candidate_top_k = candidate_ranking_data.get("candidate_top_k", 10)
    for field_name, value in (
        ("path_top_k", path_top_k),
        ("candidate_top_k", candidate_top_k),
    ):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(
                f"candidate_ranking {field_name} must be a positive integer."
            )

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
        candidate_ranking=CandidateRankingSettings(
            path_top_k=path_top_k,
            candidate_top_k=candidate_top_k,
        ),
    )
