"""Business-facing repository interfaces for KG reads."""

from __future__ import annotations

from dataclasses import dataclass, field

from .cypher_queries import (
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY,
    P_E_I_G_I_E_P_PATH_STATISTICS_QUERY,
)
from .neo4j_client import Neo4jClient


DEFAULT_PATH_LIMITS = [500, 1000, 2000, 3000, 5000]


@dataclass
class KgRepository:
    """Repository for graph reads used by similarity features."""

    client: Neo4jClient
    default_limits: list[int] = field(default_factory=lambda: DEFAULT_PATH_LIMITS.copy())

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
