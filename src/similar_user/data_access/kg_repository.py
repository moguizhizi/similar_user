"""Business-facing repository interfaces for KG reads."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from config.settings import GraphPathLimitSettings, load_query_settings

from .cypher_queries import (
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY,
    P_E_I_G_I_E_P_PATH_STATISTICS_QUERY,
)
from .neo4j_client import Neo4jClient


DEFAULT_PATH_LIMITS = [500, 1000, 2000, 3000, 5000]
DEFAULT_QUERY_CONFIG_PATH = Path("config/query.yaml")


@dataclass(frozen=True)
class GraphPathLimitRecommendation:
    """Recommended query limit derived from graph statistics."""

    per_g: int
    limit: int


@dataclass
class KgRepository:
    """Repository for graph reads used by similarity features."""

    client: Neo4jClient
    default_limits: list[int] = field(default_factory=lambda: DEFAULT_PATH_LIMITS.copy())
    query_config_path: Path = DEFAULT_QUERY_CONFIG_PATH

    def get_patient_task_set_task_game_task_set_patient_pattern_statistics(
        self,
        patient_id: str,
    ) -> list[dict[str, int]]:
        """Return statistics for the fixed P-S-I-G-I-S-P traversal pattern."""
        normalized_patient_id = patient_id.strip()
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY,
            parameters={"patient_id": normalized_patient_id},
        )

    def recommend_graph_path_limit(
        self,
        total_paths: int,
        g_count: int,
    ) -> GraphPathLimitRecommendation:
        """Derive a Cypher limit from fixed-pattern graph statistics."""
        if total_paths < 0:
            raise ValueError("total_paths must be a non-negative integer.")
        if g_count < 0:
            raise ValueError("g_count must be a non-negative integer.")

        settings = load_query_settings(self.query_config_path).graph_path_limit
        return self._recommend_graph_path_limit(total_paths, g_count, settings)

    def get_patient_p_e_i_g_i_e_p_path_statistics(
        self,
        patient_id: str,
        limits: list[int] | tuple[int, ...] | None = None,
    ) -> list[dict[str, int]]:
        """Return P-E-I-G-I-E-P path statistics for a patient across APOC limits."""
        normalized_patient_id = patient_id.strip()
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        normalized_limits = self._normalize_limits(limits)
        return self.client.run_query(
            query=P_E_I_G_I_E_P_PATH_STATISTICS_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "limits": normalized_limits,
            },
        )

    def _normalize_limits(
        self,
        limits: list[int] | tuple[int, ...] | None,
    ) -> list[int]:
        """Validate and normalize traversal limits passed to Cypher."""
        candidate_limits = self.default_limits if limits is None else list(limits)
        if not candidate_limits:
            raise ValueError("limits must contain at least one integer.")

        normalized_limits: list[int] = []
        for limit in candidate_limits:
            if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
                raise ValueError("limits must contain positive integers.")
            normalized_limits.append(limit)

        return normalized_limits

    @staticmethod
    def _recommend_graph_path_limit(
        total_paths: int,
        g_count: int,
        settings: GraphPathLimitSettings,
    ) -> GraphPathLimitRecommendation:
        """Apply configured threshold bands to derive the final Cypher limit."""
        if settings.max_limit_source != "total_paths":
            raise ValueError("Unsupported max_limit_source for graph_path_limit.")

        per_g = settings.bands[-1].per_g
        for band in settings.bands:
            if band.max_g_count is None or g_count <= band.max_g_count:
                per_g = band.per_g
                break

        limit = min(g_count * per_g, total_paths)
        return GraphPathLimitRecommendation(per_g=per_g, limit=limit)
