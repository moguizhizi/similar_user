"""Unified direct-path query provider for Neo4j or SQLite cache backends."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from config.settings import DEFAULT_CONFIG_PATH, load_direct_path_cache_settings

from ..data_access.direct_path_cache_store import DirectPathCacheStore
from ..data_access.kg_repository import KgRepository
from ..domain.graph_schema import PathPattern


@dataclass
class DirectPathProvider:
    """Return direct source-taskset-patient paths from configured backend."""

    kg_repository: KgRepository
    config_path: str | Path = DEFAULT_CONFIG_PATH

    def get_randomized_paths(
        self,
        *,
        pattern: PathPattern,
        source_id: str,
        start_date: str | None,
        end_date: str | None,
    ) -> list[dict[str, Any]]:
        """Return paths using SQLite cache when enabled, otherwise Neo4j."""
        settings = load_direct_path_cache_settings(self.config_path)
        if settings.enabled:
            return DirectPathCacheStore(settings.sqlite_path).get_paths(
                pattern,
                source_id,
                start_date=start_date,
                end_date=end_date,
            )
        return self._get_paths_from_neo4j(
            pattern=pattern,
            source_id=source_id,
            start_date=start_date,
            end_date=end_date,
        )

    def _get_paths_from_neo4j(
        self,
        *,
        pattern: PathPattern,
        source_id: str,
        start_date: str | None,
        end_date: str | None,
    ) -> list[dict[str, Any]]:
        if pattern == PathPattern.DISEASE_TASKSET_PATIENT:
            return self.kg_repository.get_disease_taskset_patient_randomized_paths(
                source_id,
                start_date=start_date,
                end_date=end_date,
            )
        if pattern == PathPattern.SYMPTOM_TASKSET_PATIENT:
            return self.kg_repository.get_symptom_taskset_patient_randomized_paths(
                source_id,
                start_date=start_date,
                end_date=end_date,
            )
        if pattern == PathPattern.UNKNOWN_TASKSET_PATIENT:
            return self.kg_repository.get_unknown_taskset_patient_randomized_paths(
                source_id,
                start_date=start_date,
                end_date=end_date,
            )
        raise ValueError(f"Unsupported direct path pattern: {pattern.value}")
