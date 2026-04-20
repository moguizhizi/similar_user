"""Business-facing repository interfaces for KG reads."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from config.settings import GraphPathLimitSettings, load_query_settings
from ..utils.logger import get_logger

from .cypher_queries import (
    PATIENT_DISEASE_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_DISEASE_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_START_DATE_QUERY,
    PATIENT_GAMES_BY_DATE_RANGE_QUERY,
    PATIENT_GAMES_BY_END_DATE_QUERY,
    PATIENT_GAMES_BY_START_DATE_QUERY,
    PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_GAME_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_SYMPTOM_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_SYMPTOM_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY,
    PATIENT_UNKNOWN_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_UNKNOWN_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_END_DATE_RANDOMIZED_PATH_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_RANDOMIZED_PATH_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY,
)
from .neo4j_client import Neo4jClient


LOGGER = get_logger(__name__)
DEFAULT_PATH_LIMITS = [500, 1000, 2000, 3000, 5000]
DEFAULT_CONFIG_PATH = Path("config/settings.yaml")


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
    config_path: Path = DEFAULT_CONFIG_PATH

    def get_patient_training_date_games_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return games grouped by patient training date from a start date."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
            },
        )

    def get_patient_distinct_games_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct games for one patient up to and including an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_distinct_games_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct games for one patient from a start date."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
            },
        )

    def get_patient_distinct_games_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct games for one patient within a date range."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_games_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game rows for one patient up to and including an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_GAMES_BY_END_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_games_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return game rows for one patient from a start date."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_GAMES_BY_START_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
            },
        )

    def get_patient_games_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game rows for one patient within a date range."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_GAMES_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_game_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game sets for two patients up to and including an end date."""
        return self._run_patient_pair_query_by_end_date(
            query=PATIENT_GAME_SET_COMPARISON_BY_END_DATE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            end_date=end_date,
        )

    def get_patient_game_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return game sets for two patients from a start date."""
        return self._run_patient_pair_query_by_start_date(
            query=PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            start_date=start_date,
        )

    def get_patient_game_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game sets for two patients within a date range."""
        return self._run_patient_pair_query_by_date_range(
            query=PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            start_date=start_date,
            end_date=end_date,
        )

    def get_patient_game_norm_score_series_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game-level norm-score series for two patients up to an end date."""
        normalized_primary_patient_id = primary_patient_id.strip()
        normalized_comparison_patient_id = comparison_patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_primary_patient_id:
            raise ValueError("primary_patient_id must be a non-empty string.")
        if not normalized_comparison_patient_id:
            raise ValueError("comparison_patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY,
            parameters={
                "primary_patient_id": normalized_primary_patient_id,
                "comparison_patient_id": normalized_comparison_patient_id,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_distinct_task_instances_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct task instances for one patient from a start date."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
            },
        )

    def get_patient_distinct_task_instances_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct task instances for one patient up to and including an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_distinct_task_instances_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct task instances for one patient within a date range."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_distinct_symptoms_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct symptoms for one patient up to and including an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_symptom_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return symptom sets for two patients up to and including an end date."""
        return self._run_patient_pair_query_by_end_date(
            query=PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            end_date=end_date,
        )

    def get_patient_distinct_symptoms_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct symptoms for one patient from a start date."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_SYMPTOMS_BY_START_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
            },
        )

    def get_patient_symptom_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return symptom sets for two patients from a start date."""
        return self._run_patient_pair_query_by_start_date(
            query=PATIENT_SYMPTOM_SET_COMPARISON_BY_START_DATE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            start_date=start_date,
        )

    def get_patient_distinct_symptoms_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct symptoms for one patient within a date range."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_symptom_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return symptom sets for two patients within a date range."""
        return self._run_patient_pair_query_by_date_range(
            query=PATIENT_SYMPTOM_SET_COMPARISON_BY_DATE_RANGE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            start_date=start_date,
            end_date=end_date,
        )

    def get_patient_distinct_diseases_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct diseases for one patient up to and including an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_disease_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return disease sets for two patients up to and including an end date."""
        return self._run_patient_pair_query_by_end_date(
            query=PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            end_date=end_date,
        )

    def get_patient_disease_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return disease sets for two patients from a start date."""
        return self._run_patient_pair_query_by_start_date(
            query=PATIENT_DISEASE_SET_COMPARISON_BY_START_DATE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            start_date=start_date,
        )

    def get_patient_disease_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return disease sets for two patients within a date range."""
        return self._run_patient_pair_query_by_date_range(
            query=PATIENT_DISEASE_SET_COMPARISON_BY_DATE_RANGE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            start_date=start_date,
            end_date=end_date,
        )

    def get_patient_distinct_diseases_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct diseases for one patient from a start date."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_DISEASES_BY_START_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
            },
        )

    def get_patient_distinct_diseases_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct diseases for one patient within a date range."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_distinct_unknowns_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct unknown-category nodes for one patient up to and including an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_unknown_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return unknown-category sets for two patients up to and including an end date."""
        return self._run_patient_pair_query_by_end_date(
            query=PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            end_date=end_date,
        )

    def get_patient_distinct_unknowns_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct unknown-category nodes for one patient from a start date."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_UNKNOWNS_BY_START_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
            },
        )

    def get_patient_unknown_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return unknown-category sets for two patients from a start date."""
        return self._run_patient_pair_query_by_start_date(
            query=PATIENT_UNKNOWN_SET_COMPARISON_BY_START_DATE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            start_date=start_date,
        )

    def get_patient_distinct_unknowns_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct unknown-category nodes for one patient within a date range."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_unknown_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return unknown-category sets for two patients within a date range."""
        return self._run_patient_pair_query_by_date_range(
            query=PATIENT_UNKNOWN_SET_COMPARISON_BY_DATE_RANGE_QUERY,
            primary_patient_id=primary_patient_id,
            comparison_patient_id=comparison_patient_id,
            start_date=start_date,
            end_date=end_date,
        )

    def get_patient_task_instance_set_ordered_training_dates(
        self,
        patient_id: str,
    ) -> list[dict[str, object]]:
        """Return a patient and its TaskInstanceSet training dates in ascending order."""
        normalized_patient_id = patient_id.strip()
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY,
            parameters={"patient_id": normalized_patient_id},
        )

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

    def get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics(
        self,
        patient_id: str,
    ) -> list[dict[str, int]]:
        """Return fixed-pattern statistics constrained by TaskInstanceSet training dates."""
        normalized_patient_id = patient_id.strip()
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY,
            parameters={"patient_id": normalized_patient_id},
        )

    def get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, int]]:
        """Return dated fixed-pattern statistics constrained up to an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, int]]:
        """Return dated fixed-pattern statistics constrained from a start date."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
            },
        )

    def get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, int]]:
        """Return dated fixed-pattern statistics constrained to a date range."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        return self.client.run_query(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_task_set_task_game_task_set_patient_randomized_paths(
        self,
        patient_id: str,
        per_g: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized fixed-pattern rows with named nodes and limits applied."""
        normalized_patient_id = patient_id.strip()
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")
        if not isinstance(per_g, int) or isinstance(per_g, bool) or per_g <= 0:
            raise ValueError("per_g must be a positive integer.")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer.")

        return self.client.run_query(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_RANDOMIZED_PATH_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "per_g": per_g,
                "limit": limit,
            },
        )

    def get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_start_date(
        self,
        patient_id: str,
        start_date: str,
        per_g: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized fixed-pattern rows constrained from a start date."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")
        if not isinstance(per_g, int) or isinstance(per_g, bool) or per_g <= 0:
            raise ValueError("per_g must be a positive integer.")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer.")

        return self.client.run_query(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "per_g": per_g,
                "limit": limit,
            },
        )

    def get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date(
        self,
        patient_id: str,
        end_date: str,
        per_g: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized fixed-pattern rows constrained up to an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")
        if not isinstance(per_g, int) or isinstance(per_g, bool) or per_g <= 0:
            raise ValueError("per_g must be a positive integer.")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer.")

        return self.client.run_query(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "end_date": normalized_end_date,
                "per_g": per_g,
                "limit": limit,
            },
        )

    def get_patient_task_set_task_game_task_set_patient_randomized_paths_by_end_date(
        self,
        patient_id: str,
        end_date: str,
        per_g: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized fixed-pattern rows constrained only by end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")
        if not isinstance(per_g, int) or isinstance(per_g, bool) or per_g <= 0:
            raise ValueError("per_g must be a positive integer.")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer.")

        return self.client.run_query(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_END_DATE_RANDOMIZED_PATH_QUERY,
            parameters={
                "patient_id": normalized_patient_id,
                "end_date": normalized_end_date,
                "per_g": per_g,
                "limit": limit,
            },
        )

    def recommend_graph_path_limit(
        self,
        total_paths: int,
        g_count: int,
        p2_count: int,
    ) -> GraphPathLimitRecommendation:
        """Derive a Cypher limit from fixed-pattern graph statistics."""
        if total_paths < 0:
            raise ValueError("total_paths must be a non-negative integer.")
        if g_count < 0:
            raise ValueError("g_count must be a non-negative integer.")
        if p2_count < 0:
            raise ValueError("p2_count must be a non-negative integer.")

        settings = load_query_settings(self.config_path).graph_path_limit
        recommendation = self._recommend_graph_path_limit(
            total_paths,
            g_count,
            p2_count,
            settings,
        )
        LOGGER.debug(
            "Recommended graph path limit: total_paths=%s, g_count=%s, p2_count=%s, per_g=%s, limit=%s",
            total_paths,
            g_count,
            p2_count,
            recommendation.per_g,
            recommendation.limit,
        )
        return recommendation

    @staticmethod
    def _normalize_required_string(value: str, field_name: str) -> str:
        """Validate and normalize a required string parameter."""
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a non-empty string.")

        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"{field_name} must be a non-empty string.")

        return normalized_value

    def _run_patient_pair_query_by_end_date(
        self,
        *,
        query: str,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Run a two-patient query constrained up to and including an end date."""
        normalized_primary_patient_id, normalized_comparison_patient_id = (
            self._normalize_patient_pair(primary_patient_id, comparison_patient_id)
        )
        normalized_end_date = self._normalize_required_string(end_date, "end_date")

        return self.client.run_query(
            query=query,
            parameters={
                "primary_patient_id": normalized_primary_patient_id,
                "comparison_patient_id": normalized_comparison_patient_id,
                "end_date": normalized_end_date,
            },
        )

    def _run_patient_pair_query_by_start_date(
        self,
        *,
        query: str,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Run a two-patient query constrained from a start date."""
        normalized_primary_patient_id, normalized_comparison_patient_id = (
            self._normalize_patient_pair(primary_patient_id, comparison_patient_id)
        )
        normalized_start_date = self._normalize_required_string(start_date, "start_date")

        return self.client.run_query(
            query=query,
            parameters={
                "primary_patient_id": normalized_primary_patient_id,
                "comparison_patient_id": normalized_comparison_patient_id,
                "start_date": normalized_start_date,
            },
        )

    def _run_patient_pair_query_by_date_range(
        self,
        *,
        query: str,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Run a two-patient query constrained to a date range."""
        normalized_primary_patient_id, normalized_comparison_patient_id = (
            self._normalize_patient_pair(primary_patient_id, comparison_patient_id)
        )
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")

        return self.client.run_query(
            query=query,
            parameters={
                "primary_patient_id": normalized_primary_patient_id,
                "comparison_patient_id": normalized_comparison_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def _normalize_patient_pair(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
    ) -> tuple[str, str]:
        """Validate and normalize two patient ids used by comparison queries."""
        return (
            self._normalize_required_string(primary_patient_id, "primary_patient_id"),
            self._normalize_required_string(
                comparison_patient_id,
                "comparison_patient_id",
            ),
        )

    @staticmethod
    def _recommend_graph_path_limit(
        total_paths: int,
        g_count: int,
        p2_count: int,
        settings: GraphPathLimitSettings,
    ) -> GraphPathLimitRecommendation:
        """Apply configured threshold bands to derive the final Cypher limit."""
        if settings.max_limit_source != "total_paths":
            raise ValueError("Unsupported max_limit_source for graph_path_limit.")

        if settings.per_g_strategy == "band":
            per_g = settings.bands[-1].per_g
            for band in settings.bands:
                if band.max_g_count is None or g_count <= band.max_g_count:
                    per_g = band.per_g
                    break
        elif settings.per_g_strategy == "p2_div_g":
            per_g = 1 if g_count == 0 else max(1, math.ceil(p2_count / g_count))
        else:
            raise ValueError("Unsupported per_g_strategy for graph_path_limit.")

        limit = min(g_count * per_g, total_paths)
        return GraphPathLimitRecommendation(per_g=per_g, limit=limit)
