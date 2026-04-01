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
