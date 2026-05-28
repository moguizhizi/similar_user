"""Business-facing repository interfaces for KG reads."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from config.settings import GraphPathLimitSettings, load_query_settings
from ..domain.graph_schema import PathPattern
from ..utils.logger import get_logger

from .neo4j_client import Neo4jClient
from .cypher_queries import (
    DISEASE_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY,
    DISEASE_TASKSET_PATIENT_CACHE_PATHS_QUERY,
    SYMPTOM_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY,
    SYMPTOM_TASKSET_PATIENT_CACHE_PATHS_QUERY,
    UNKNOWN_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY,
    UNKNOWN_TASKSET_PATIENT_CACHE_PATHS_QUERY,
)
from .cypher_queries.pattern_paths import (
    DISEASE_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY,
    DISEASE_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY,
    SYMPTOM_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY,
    SYMPTOM_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY,
    UNKNOWN_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY,
    UNKNOWN_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY,
)
from .graph_query_registry import get_graph_query_spec
from .pattern_registry import (
    PatternQuerySet,
    QueryDateWindow,
    get_path_pattern_spec,
)


LOGGER = get_logger(__name__)
DEFAULT_PATH_LIMITS = [500, 1000, 2000, 3000, 5000]
DEFAULT_CONFIG_PATH = Path("config/settings.yaml")


@dataclass(frozen=True)
class GraphPathLimitRecommendation:
    """Recommended query limit derived from graph statistics."""

    per_g: int
    limit: int


class PatternQueryFamily(str, Enum):
    """Named query families for a path pattern candidate space."""

    DATE_WINDOW = "date_window"
    TRAINING_ORDER_SOURCE_WINDOW = "training_order_source_window"
    TRAINING_ORDER_LOCAL_SAMPLING_SOURCE_WINDOW = (
        "training_order_local_sampling_source_window"
    )
    TRAINING_ORDER_AGE_ONLY_SOURCE_WINDOW = "training_order_age_only_source_window"
    TRAINING_ORDER_LAYER1_AGE_COMPLETION_SOURCE_WINDOW = (
        "training_order_layer1_age_completion_source_window"
    )
    TRAINING_ORDER_LAYER2_EDUCATION_EXACT_SOURCE_WINDOW = (
        "training_order_layer2_education_exact_source_window"
    )
    TRAINING_ORDER_LAYER3_ACTIVITY_TASK_TYPE_SOURCE_WINDOW = (
        "training_order_layer3_activity_task_type_source_window"
    )
    TRAINING_ORDER_DUAL_WINDOW = "training_order_dual_window"
    TRAINING_ORDER_LOCAL_SAMPLING_DUAL_WINDOW = "training_order_local_sampling_dual_window"
    TRAINING_ORDER_AGE_ONLY_DUAL_WINDOW = "training_order_age_only_dual_window"
    TRAINING_ORDER_LAYER1_AGE_COMPLETION_DUAL_WINDOW = (
        "training_order_layer1_age_completion_dual_window"
    )
    TRAINING_ORDER_LAYER2_EDUCATION_EXACT_DUAL_WINDOW = (
        "training_order_layer2_education_exact_dual_window"
    )
    TRAINING_ORDER_LAYER3_ACTIVITY_TASK_TYPE_DUAL_WINDOW = (
        "training_order_layer3_activity_task_type_dual_window"
    )


@dataclass
class KgRepository:
    """Repository for graph reads used by similarity features."""

    client: Neo4jClient
    default_limits: list[int] = field(default_factory=lambda: DEFAULT_PATH_LIMITS.copy())
    config_path: Path = DEFAULT_CONFIG_PATH

    def get_patient_ids(self) -> list[str]:
        """Return all patient IDs in the graph."""
        spec = get_graph_query_spec("patient_ids")
        rows = self.client.run_query(
            query=spec.query,
            parameters={},
        )
        return self._extract_patient_ids(rows)

    def patient_exists(self, patient_id: str) -> bool:
        """Return whether a Patient node exists for the given ID."""
        normalized_patient_id = self._normalize_required_string(
            patient_id,
            "patient_id",
        )
        spec = get_graph_query_spec("patient_exists")
        rows = self.client.run_query(
            query=spec.query,
            parameters={"patient_id": normalized_patient_id},
        )
        if not rows:
            return False
        return bool(rows[0].get("exists"))

    def get_patient_ids_with_training_on_date(
        self,
        base_date: str,
        limit: int | None = None,
    ) -> list[str]:
        """Return patient IDs with training records on base_date."""
        normalized_base_date = self._normalize_required_string(base_date, "base_date")
        parameters: dict[str, object] = {"base_date": normalized_base_date}
        if limit is None:
            spec = get_graph_query_spec("patient_ids_with_training_on_date")
        else:
            if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
                raise ValueError("limit must be a positive integer.")
            spec = get_graph_query_spec("patient_ids_with_training_on_date_limit")
            parameters["limit"] = limit
        rows = self.client.run_query(
            query=spec.query,
            parameters=parameters,
        )
        return self._extract_patient_ids(rows)

    def get_source_patient_ids_with_secondary_ability_scores(self) -> list[str]:
        """Return source patient IDs with secondary ability training records."""
        spec = get_graph_query_spec("source_patient_ids_with_secondary_ability_scores")
        rows = self.client.run_query(
            query=spec.query,
            parameters={},
        )
        return self._extract_patient_ids(rows)

    @staticmethod
    def _extract_patient_ids(rows: list[dict[str, object]]) -> list[str]:
        """Extract non-empty patient IDs from query rows."""
        patient_ids: list[str] = []
        for row in rows:
            patient_id = str(row.get("patient_id") or "").strip()
            if patient_id:
                patient_ids.append(patient_id)
        return patient_ids

    def get_distinct_training_games(self) -> list[dict[str, object]]:
        """Return distinct games that appear in training records."""
        spec = get_graph_query_spec("distinct_training_games")
        return self.client.run_query(
            query=spec.query,
            parameters={},
        )

    def get_disease_taskset_task_game_sampled_per_game(
        self,
        disease_id: str,
    ) -> list[dict[str, object]]:
        """Return one sampled TaskInstanceSet/TaskInstance row per game for a disease."""
        normalized_disease_id = self._normalize_required_string(
            disease_id,
            "disease_id",
        )
        spec = get_graph_query_spec("disease_taskset_task_game_sampled_per_game")
        return self.client.run_query(
            query=spec.query,
            parameters={"disease_id": normalized_disease_id},
        )

    def get_disease_taskset_exclusive_task_game_sampled_per_game(
        self,
        disease_id: str,
    ) -> list[dict[str, object]]:
        """Return one sampled exclusive TaskInstance row per game for a disease."""
        normalized_disease_id = self._normalize_required_string(
            disease_id,
            "disease_id",
        )
        spec = get_graph_query_spec(
            "disease_taskset_exclusive_task_game_sampled_per_game"
        )
        return self.client.run_query(
            query=spec.query,
            parameters={"disease_id": normalized_disease_id},
        )

    def get_disease_education_age_exclusive_task_games(
        self,
        disease_id: str,
        education: str,
        min_age: int,
        max_age: int,
    ) -> list[dict[str, object]]:
        """Return exclusive-task games matching disease, education, and age range."""
        normalized_disease_id = self._normalize_required_string(
            disease_id,
            "disease_id",
        )
        return self._get_entity_education_age_exclusive_task_games(
            query_name="disease_education_age_exclusive_task_game",
            id_parameter_name="disease_id",
            entity_id=normalized_disease_id,
            education=education,
            min_age=min_age,
            max_age=max_age,
        )

    def get_symptom_taskset_task_game_sampled_per_game(
        self,
        symptom_id: str,
    ) -> list[dict[str, object]]:
        """Return one sampled TaskInstanceSet/TaskInstance row per game for a symptom."""
        normalized_symptom_id = self._normalize_required_string(
            symptom_id,
            "symptom_id",
        )
        spec = get_graph_query_spec("symptom_taskset_task_game_sampled_per_game")
        return self.client.run_query(
            query=spec.query,
            parameters={"symptom_id": normalized_symptom_id},
        )

    def get_symptom_taskset_exclusive_task_game_sampled_per_game(
        self,
        symptom_id: str,
    ) -> list[dict[str, object]]:
        """Return one sampled exclusive TaskInstance row per game for a symptom."""
        normalized_symptom_id = self._normalize_required_string(
            symptom_id,
            "symptom_id",
        )
        spec = get_graph_query_spec(
            "symptom_taskset_exclusive_task_game_sampled_per_game"
        )
        return self.client.run_query(
            query=spec.query,
            parameters={"symptom_id": normalized_symptom_id},
        )

    def get_symptom_education_age_exclusive_task_games(
        self,
        symptom_id: str,
        education: str,
        min_age: int,
        max_age: int,
    ) -> list[dict[str, object]]:
        """Return exclusive-task games matching symptom, education, and age range."""
        normalized_symptom_id = self._normalize_required_string(
            symptom_id,
            "symptom_id",
        )
        return self._get_entity_education_age_exclusive_task_games(
            query_name="symptom_education_age_exclusive_task_game",
            id_parameter_name="symptom_id",
            entity_id=normalized_symptom_id,
            education=education,
            min_age=min_age,
            max_age=max_age,
        )

    def get_unknown_taskset_task_game_sampled_per_game(
        self,
        unknown_id: str,
    ) -> list[dict[str, object]]:
        """Return one sampled TaskInstanceSet/TaskInstance row per game for unknown."""
        normalized_unknown_id = self._normalize_required_string(
            unknown_id,
            "unknown_id",
        )
        spec = get_graph_query_spec("unknown_taskset_task_game_sampled_per_game")
        return self.client.run_query(
            query=spec.query,
            parameters={"unknown_id": normalized_unknown_id},
        )

    def get_unknown_taskset_exclusive_task_game_sampled_per_game(
        self,
        unknown_id: str,
    ) -> list[dict[str, object]]:
        """Return one sampled exclusive TaskInstance row per game for unknown."""
        normalized_unknown_id = self._normalize_required_string(
            unknown_id,
            "unknown_id",
        )
        spec = get_graph_query_spec(
            "unknown_taskset_exclusive_task_game_sampled_per_game"
        )
        return self.client.run_query(
            query=spec.query,
            parameters={"unknown_id": normalized_unknown_id},
        )

    def get_unknown_education_age_exclusive_task_games(
        self,
        unknown_id: str,
        education: str,
        min_age: int,
        max_age: int,
    ) -> list[dict[str, object]]:
        """Return exclusive-task games matching unknown, education, and age range."""
        normalized_unknown_id = self._normalize_required_string(
            unknown_id,
            "unknown_id",
        )
        return self._get_entity_education_age_exclusive_task_games(
            query_name="unknown_education_age_exclusive_task_game",
            id_parameter_name="unknown_id",
            entity_id=normalized_unknown_id,
            education=education,
            min_age=min_age,
            max_age=max_age,
        )

    def _get_entity_education_age_exclusive_task_games(
        self,
        *,
        query_name: str,
        id_parameter_name: str,
        entity_id: str,
        education: str,
        min_age: int,
        max_age: int,
    ) -> list[dict[str, object]]:
        """Run a shared entity/education/age exclusive-task game query."""
        normalized_education = self._normalize_required_string(
            education,
            "education",
        )
        if (
            not isinstance(min_age, int)
            or isinstance(min_age, bool)
            or not isinstance(max_age, int)
            or isinstance(max_age, bool)
        ):
            raise ValueError("min_age and max_age must be integers.")
        if min_age < 0:
            raise ValueError(f"min_age must be non-negative, got {min_age}.")
        if max_age < min_age:
            raise ValueError(
                f"max_age must be greater than or equal to min_age, got {max_age}."
            )
        spec = get_graph_query_spec(query_name)
        return self.client.run_query(
            query=spec.query,
            parameters={
                id_parameter_name: entity_id,
                "education": normalized_education,
                "min_age": min_age,
                "max_age": max_age,
            },
        )

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

        spec = get_graph_query_spec("patient_training_date_games_by_start_date")
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
            },
        )

    def get_disease_taskset_patient_randomized_paths(
        self,
        disease_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        """Return one randomized Disease-TaskInstanceSet-Patient path per patient."""
        normalized_disease_id = disease_id.strip()
        normalized_start_date = self._normalize_optional_string(start_date, "start_date")
        normalized_end_date = self._normalize_optional_string(end_date, "end_date")
        date_window = QueryDateWindow(
            start_date=normalized_start_date,
            end_date=normalized_end_date,
        )
        if not normalized_disease_id:
            raise ValueError("disease_id must be a non-empty string.")

        spec = get_path_pattern_spec(PathPattern.DISEASE_TASKSET_PATIENT)
        if spec.direct_queries is None:
            raise ValueError("DISEASE_TASKSET_PATIENT has no direct path queries.")
        query = spec.direct_queries.randomized_path.select(date_window)
        parameters: dict[str, object] = {"disease_id": normalized_disease_id}
        parameters.update(date_window.parameters())

        return self.client.run_query(
            query=query,
            parameters=parameters,
        )

    def get_symptom_taskset_patient_randomized_paths(
        self,
        symptom_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        """Return one randomized Symptom-TaskInstanceSet-Patient path per patient."""
        normalized_symptom_id = symptom_id.strip()
        normalized_start_date = self._normalize_optional_string(start_date, "start_date")
        normalized_end_date = self._normalize_optional_string(end_date, "end_date")
        date_window = QueryDateWindow(
            start_date=normalized_start_date,
            end_date=normalized_end_date,
        )
        if not normalized_symptom_id:
            raise ValueError("symptom_id must be a non-empty string.")

        spec = get_path_pattern_spec(PathPattern.SYMPTOM_TASKSET_PATIENT)
        if spec.direct_queries is None:
            raise ValueError("SYMPTOM_TASKSET_PATIENT has no direct path queries.")
        query = spec.direct_queries.randomized_path.select(date_window)
        parameters: dict[str, object] = {"symptom_id": normalized_symptom_id}
        parameters.update(date_window.parameters())

        return self.client.run_query(
            query=query,
            parameters=parameters,
        )

    def get_unknown_taskset_patient_randomized_paths(
        self,
        unknown_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        """Return one randomized Unknown-TaskInstanceSet-Patient path per patient."""
        normalized_unknown_id = unknown_id.strip()
        normalized_start_date = self._normalize_optional_string(start_date, "start_date")
        normalized_end_date = self._normalize_optional_string(end_date, "end_date")
        date_window = QueryDateWindow(
            start_date=normalized_start_date,
            end_date=normalized_end_date,
        )
        if not normalized_unknown_id:
            raise ValueError("unknown_id must be a non-empty string.")

        spec = get_path_pattern_spec(PathPattern.UNKNOWN_TASKSET_PATIENT)
        if spec.direct_queries is None:
            raise ValueError("UNKNOWN_TASKSET_PATIENT has no direct path queries.")
        query = spec.direct_queries.randomized_path.select(date_window)
        parameters: dict[str, object] = {"unknown_id": normalized_unknown_id}
        parameters.update(date_window.parameters())

        return self.client.run_query(
            query=query,
            parameters=parameters,
        )

    def get_direct_taskset_patient_cache_paths(
        self,
        pattern: PathPattern,
        *,
        start_date: str | None = None,
    ) -> list[dict[str, object]]:
        """Return direct source-taskset-patient paths for local cache sync."""
        normalized_pattern = (
            pattern if isinstance(pattern, PathPattern) else PathPattern(pattern)
        )
        normalized_start_date = self._normalize_optional_string(
            start_date,
            "start_date",
        )
        query_map = {
            PathPattern.DISEASE_TASKSET_PATIENT: (
                DISEASE_TASKSET_PATIENT_CACHE_PATHS_QUERY,
                DISEASE_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY,
            ),
            PathPattern.SYMPTOM_TASKSET_PATIENT: (
                SYMPTOM_TASKSET_PATIENT_CACHE_PATHS_QUERY,
                SYMPTOM_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY,
            ),
            PathPattern.UNKNOWN_TASKSET_PATIENT: (
                UNKNOWN_TASKSET_PATIENT_CACHE_PATHS_QUERY,
                UNKNOWN_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY,
            ),
        }
        try:
            base_query, start_date_query = query_map[normalized_pattern]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported direct cache sync pattern: {normalized_pattern.value}"
            ) from exc

        parameters: dict[str, object] = {}
        query = base_query
        if normalized_start_date is not None:
            query = start_date_query
            parameters["start_date"] = normalized_start_date

        return self.client.run_query(
            query=query,
            parameters=parameters,
        )

    def get_direct_taskset_patient_source_summaries(
        self,
        pattern: PathPattern,
    ) -> list[dict[str, object]]:
        """Return source IDs and latest training dates for a direct path pattern."""
        normalized_pattern = (
            pattern if isinstance(pattern, PathPattern) else PathPattern(pattern)
        )
        query_map = {
            PathPattern.DISEASE_TASKSET_PATIENT: DISEASE_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY,
            PathPattern.SYMPTOM_TASKSET_PATIENT: SYMPTOM_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY,
            PathPattern.UNKNOWN_TASKSET_PATIENT: UNKNOWN_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY,
        }
        try:
            query = query_map[normalized_pattern]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported direct source summary pattern: {normalized_pattern.value}"
            ) from exc
        return self.client.run_query(query=query, parameters={})

    def get_direct_taskset_patient_latest_training_date(
        self,
        pattern: PathPattern,
        source_id: str,
    ) -> str | None:
        """Return the latest TaskInstanceSet training date for one direct source."""
        normalized_pattern = (
            pattern if isinstance(pattern, PathPattern) else PathPattern(pattern)
        )
        normalized_source_id = self._normalize_required_string(source_id, "source_id")
        query_map = {
            PathPattern.DISEASE_TASKSET_PATIENT: DISEASE_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY,
            PathPattern.SYMPTOM_TASKSET_PATIENT: SYMPTOM_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY,
            PathPattern.UNKNOWN_TASKSET_PATIENT: UNKNOWN_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY,
        }
        try:
            query = query_map[normalized_pattern]
        except KeyError as exc:
            raise ValueError(
                f"Unsupported direct latest-date pattern: {normalized_pattern.value}"
            ) from exc
        rows = self.client.run_query(
            query=query,
            parameters={"source_id": normalized_source_id},
        )
        if not rows:
            return None
        value = rows[0].get("latest_training_date")
        return str(value) if value is not None else None

    def get_patient_distinct_games_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct games for one patient before an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_distinct_games_by_end_date")
        return self.client.run_query(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_distinct_games_by_start_date")
        return self.client.run_query(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_distinct_games_by_date_range")
        return self.client.run_query(
            query=spec.query,
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
        """Return game rows for one patient before an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_games_by_end_date")
        return self.client.run_query(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_games_by_start_date")
        return self.client.run_query(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_games_by_date_range")
        return self.client.run_query(
            query=spec.query,
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
        """Return game sets for two patients before an end date."""
        spec = get_graph_query_spec("patient_game_set_comparison_by_end_date")
        return self._run_patient_pair_query_by_end_date(
            query=spec.query,
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
        spec = get_graph_query_spec("patient_game_set_comparison_by_start_date")
        return self._run_patient_pair_query_by_start_date(
            query=spec.query,
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
        spec = get_graph_query_spec("patient_game_set_comparison_by_date_range")
        return self._run_patient_pair_query_by_date_range(
            query=spec.query,
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
        """Return game-level norm-score series for two patients before an end date."""
        normalized_primary_patient_id = primary_patient_id.strip()
        normalized_comparison_patient_id = comparison_patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_primary_patient_id:
            raise ValueError("primary_patient_id must be a non-empty string.")
        if not normalized_comparison_patient_id:
            raise ValueError("comparison_patient_id must be a non-empty string.")

        spec = get_graph_query_spec(
            "patient_game_norm_score_series_comparison_by_end_date"
        )
        return self.client.run_query(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_distinct_task_instances_by_start_date")
        return self.client.run_query(
            query=spec.query,
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
        """Return distinct task instances for one patient before an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_distinct_task_instances_by_end_date")
        return self.client.run_query(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_distinct_task_instances_by_date_range")
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_profile_entities_by_effective_date(
        self,
        patient_id: str,
        base_date: str,
    ) -> list[dict[str, object]]:
        """Return disease, symptom, and unknown nodes on the nearest effective date."""
        normalized_patient_id = patient_id.strip()
        normalized_base_date = self._normalize_required_string(base_date, "base_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_profile_entities_by_effective_date")
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "base_date": normalized_base_date,
            },
        )

    def get_patient_direct_entity_scoring_profile(
        self,
        patient_id: str,
        base_date: str,
    ) -> list[dict[str, object]]:
        """Return the profile fields needed before direct-entity path scoring."""
        normalized_patient_id = self._normalize_required_string(
            patient_id,
            "patient_id",
        )
        normalized_base_date = self._normalize_required_string(base_date, "base_date")

        spec = get_graph_query_spec("patient_direct_entity_scoring_profile")
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "base_date": normalized_base_date,
            },
        )

    def get_patient_profile_gender_education_age_exclusive_task_games(
        self,
        patient_id: str,
        base_date: str,
        age_window: int,
    ) -> list[dict[str, object]]:
        """Return exclusive-task games matching a patient's profile and age window."""
        normalized_patient_id = patient_id.strip()
        normalized_base_date = self._normalize_required_string(base_date, "base_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")
        if (
            not isinstance(age_window, int)
            or isinstance(age_window, bool)
            or age_window < 0
        ):
            raise ValueError("age_window must be a non-negative integer.")

        spec = get_graph_query_spec(
            "patient_profile_gender_education_age_exclusive_task_game"
        )
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "base_date": normalized_base_date,
                "age_window": age_window,
            },
        )

    def get_patient_profile_gender_education_age_windowed_exclusive_task_games(
        self,
        patient_id: str,
        base_date: str,
        age_window: int,
        profile_candidate_training_window_days: int,
    ) -> list[dict[str, object]]:
        """Return profile-matched exclusive-task games within a training-date window."""
        normalized_patient_id = patient_id.strip()
        normalized_base_date = self._normalize_required_string(base_date, "base_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")
        if (
            not isinstance(age_window, int)
            or isinstance(age_window, bool)
            or age_window < 0
        ):
            raise ValueError("age_window must be a non-negative integer.")
        if (
            not isinstance(profile_candidate_training_window_days, int)
            or isinstance(profile_candidate_training_window_days, bool)
            or profile_candidate_training_window_days < 0
        ):
            raise ValueError(
                "profile_candidate_training_window_days must be a non-negative integer."
            )

        spec = get_graph_query_spec(
            "patient_profile_gender_education_age_windowed_exclusive_task_game"
        )
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "base_date": normalized_base_date,
                "age_window": age_window,
                "profile_candidate_training_window_days": profile_candidate_training_window_days,
            },
        )

    def get_patient_secondary_ability_scores_by_disease_course_window(
        self,
        patient_id: str,
        base_date: str,
        disease_course_window_days: int,
    ) -> list[dict[str, object]]:
        """Return secondary ability scores in a disease-course window."""
        normalized_patient_id = patient_id.strip()
        normalized_base_date = self._normalize_required_string(base_date, "base_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")
        if (
            not isinstance(disease_course_window_days, int)
            or isinstance(disease_course_window_days, bool)
            or disease_course_window_days <= 0
        ):
            raise ValueError("disease_course_window_days must be a positive integer.")

        spec = get_graph_query_spec(
            "patient_secondary_ability_scores_by_disease_course_window"
        )
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "base_date": normalized_base_date,
                "disease_course_window_days": disease_course_window_days,
            },
        )

    def get_patient_total_scores_by_disease_course_window(
        self,
        patient_id: str,
        base_date: str,
        disease_course_window_days: int,
    ) -> list[dict[str, object]]:
        """Return total scores in a disease-course window."""
        normalized_patient_id = patient_id.strip()
        normalized_base_date = self._normalize_required_string(base_date, "base_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")
        if (
            not isinstance(disease_course_window_days, int)
            or isinstance(disease_course_window_days, bool)
            or disease_course_window_days <= 0
        ):
            raise ValueError("disease_course_window_days must be a positive integer.")

        spec = get_graph_query_spec(
            "patient_total_scores_by_disease_course_window"
        )
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "base_date": normalized_base_date,
                "disease_course_window_days": disease_course_window_days,
            },
        )

    def get_patient_distinct_symptoms_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct symptoms for one patient before an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_distinct_symptoms_by_end_date")
        return self.client.run_query(
            query=spec.query,
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
        """Return symptom sets for two patients before an end date."""
        spec = get_graph_query_spec("patient_symptom_set_comparison_by_end_date")
        return self._run_patient_pair_query_by_end_date(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_distinct_symptoms_by_start_date")
        return self.client.run_query(
            query=spec.query,
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
        spec = get_graph_query_spec("patient_symptom_set_comparison_by_start_date")
        return self._run_patient_pair_query_by_start_date(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_distinct_symptoms_by_date_range")
        return self.client.run_query(
            query=spec.query,
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
        spec = get_graph_query_spec("patient_symptom_set_comparison_by_date_range")
        return self._run_patient_pair_query_by_date_range(
            query=spec.query,
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
        """Return distinct diseases for one patient before an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_distinct_diseases_by_end_date")
        return self.client.run_query(
            query=spec.query,
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
        """Return disease sets for two patients before an end date."""
        spec = get_graph_query_spec("patient_disease_set_comparison_by_end_date")
        return self._run_patient_pair_query_by_end_date(
            query=spec.query,
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
        spec = get_graph_query_spec("patient_disease_set_comparison_by_start_date")
        return self._run_patient_pair_query_by_start_date(
            query=spec.query,
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
        spec = get_graph_query_spec("patient_disease_set_comparison_by_date_range")
        return self._run_patient_pair_query_by_date_range(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_distinct_diseases_by_start_date")
        return self.client.run_query(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_distinct_diseases_by_date_range")
        return self.client.run_query(
            query=spec.query,
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
        """Return distinct unknown-category nodes for one patient before an end date."""
        normalized_patient_id = patient_id.strip()
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_distinct_unknowns_by_end_date")
        return self.client.run_query(
            query=spec.query,
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
        """Return unknown-category sets for two patients before an end date."""
        spec = get_graph_query_spec("patient_unknown_set_comparison_by_end_date")
        return self._run_patient_pair_query_by_end_date(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_distinct_unknowns_by_start_date")
        return self.client.run_query(
            query=spec.query,
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
        spec = get_graph_query_spec("patient_unknown_set_comparison_by_start_date")
        return self._run_patient_pair_query_by_start_date(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_distinct_unknowns_by_date_range")
        return self.client.run_query(
            query=spec.query,
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
        spec = get_graph_query_spec("patient_unknown_set_comparison_by_date_range")
        return self._run_patient_pair_query_by_date_range(
            query=spec.query,
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

        spec = get_graph_query_spec("patient_task_instance_set_ordered_training_dates")
        return self.client.run_query(
            query=spec.query,
            parameters={"patient_id": normalized_patient_id},
        )

    def get_patient_total_score_timepoints(
        self,
        patient_id: str,
    ) -> list[dict[str, object]]:
        """Return TaskInstanceSet timepoints that have total scores for one patient."""
        normalized_patient_id = patient_id.strip()
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_total_score_timepoints")
        return self.client.run_query(
            query=spec.query,
            parameters={"patient_id": normalized_patient_id},
        )

    def get_patient_total_score_by_date(
        self,
        patient_id: str,
        training_date: str,
    ) -> list[dict[str, object]]:
        """Return a patient's total score on one training date."""
        normalized_patient_id = patient_id.strip()
        normalized_training_date = self._normalize_required_string(
            training_date,
            "training_date",
        )
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_total_score_by_date")
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "training_date": normalized_training_date,
            },
        )

    def get_patient_training_task_history(
        self,
        patient_id: str,
    ) -> list[dict[str, object]]:
        """Return dated task-instance and game rows for one patient."""
        normalized_patient_id = patient_id.strip()
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_training_task_history")
        return self.client.run_query(
            query=spec.query,
            parameters={"patient_id": normalized_patient_id},
        )

    def get_patient_training_task_history_by_date_window(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return task history in a left-closed, right-open date window."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec("patient_training_task_history_by_date_window")
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def get_patient_exclusive_training_task_history_by_date_window(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return exclusive-task history in a left-closed, right-open date window."""
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        spec = get_graph_query_spec(
            "patient_exclusive_training_task_history_by_date_window"
        )
        return self.client.run_query(
            query=spec.query,
            parameters={
                "patient_id": normalized_patient_id,
                "start_date": normalized_start_date,
                "end_date": normalized_end_date,
            },
        )

    def get_pattern_date_window_statistics(
        self,
        pattern: PathPattern | str,
        patient_id: str,
    ) -> list[dict[str, int]]:
        """Return statistics for rows with non-null training dates."""
        return self.get_pattern_statistics(
            pattern=pattern,
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=patient_id,
        )

    def get_pattern_date_window_statistics_by_end_date(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, int]]:
        """Return date-window statistics constrained before an end date."""
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        return self.get_pattern_statistics(
            pattern=pattern,
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=patient_id,
            end_date=normalized_end_date,
        )

    def get_pattern_date_window_statistics_by_start_date(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, int]]:
        """Return date-window statistics constrained from a start date."""
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        return self.get_pattern_statistics(
            pattern=pattern,
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=patient_id,
            start_date=normalized_start_date,
        )

    def get_pattern_date_window_statistics_by_date_range(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, int]]:
        """Return date-window statistics constrained to a date range."""
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        return self.get_pattern_statistics(
            pattern=pattern,
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=patient_id,
            start_date=normalized_start_date,
            end_date=normalized_end_date,
        )

    def get_training_order_pattern_statistics(
        self,
        pattern: PathPattern | str,
        patient_id: str,
    ) -> list[dict[str, int]]:
        """Return statistics for rows constrained by s1/s2 training-date order."""
        return self.get_pattern_statistics(
            pattern=pattern,
            query_family=PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW,
            patient_id=patient_id,
        )

    def get_training_order_pattern_statistics_by_end_date(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, int]]:
        """Return training-order statistics constrained before an end date."""
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        return self.get_pattern_statistics(
            pattern=pattern,
            query_family=PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW,
            patient_id=patient_id,
            end_date=normalized_end_date,
        )

    def get_training_order_pattern_statistics_by_start_date(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, int]]:
        """Return training-order statistics constrained from a start date."""
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        return self.get_pattern_statistics(
            pattern=pattern,
            query_family=PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW,
            patient_id=patient_id,
            start_date=normalized_start_date,
        )

    def get_training_order_pattern_statistics_by_date_range(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, int]]:
        """Return training-order statistics constrained to a date range."""
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        return self.get_pattern_statistics(
            pattern=pattern,
            query_family=PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW,
            patient_id=patient_id,
            start_date=normalized_start_date,
            end_date=normalized_end_date,
        )

    def get_pattern_statistics(
        self,
        *,
        pattern: PathPattern | str,
        query_family: PatternQueryFamily | str,
        patient_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, int]]:
        """Return statistics for one pattern family and optional date bounds."""
        spec = get_path_pattern_spec(pattern)
        normalized_query_family = self._normalize_pattern_query_family(query_family)
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_optional_string(start_date, "start_date")
        normalized_end_date = self._normalize_optional_string(end_date, "end_date")
        date_window = QueryDateWindow(
            start_date=normalized_start_date,
            end_date=normalized_end_date,
        )
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")

        query = self._select_pattern_statistics_query(
            spec.queries,
            normalized_query_family,
            date_window=date_window,
        )
        parameters: dict[str, object] = {"patient_id": normalized_patient_id}
        parameters.update(date_window.parameters())

        return self.client.run_query(
            query=query,
            parameters=parameters,
        )

    def get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics(
        self,
        patient_id: str,
    ) -> list[dict[str, int]]:
        """Return fixed-pattern statistics constrained by TaskInstanceSet training dates."""
        return self.get_training_order_pattern_statistics(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            patient_id,
        )

    def get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, int]]:
        """Return dated fixed-pattern statistics constrained before an end date."""
        return self.get_training_order_pattern_statistics_by_end_date(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            patient_id,
            end_date,
        )

    def get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, int]]:
        """Return dated fixed-pattern statistics constrained from a start date."""
        return self.get_training_order_pattern_statistics_by_start_date(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            patient_id,
            start_date,
        )

    def get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, int]]:
        """Return dated fixed-pattern statistics constrained to a date range."""
        return self.get_training_order_pattern_statistics_by_date_range(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            patient_id,
            start_date,
            end_date,
        )

    def get_pattern_randomized_paths_by_start_date(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        start_date: str,
        per_group: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized rows for a registered pattern from a start date."""
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        return self.get_pattern_randomized_paths(
            pattern=pattern,
            query_family=PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW,
            patient_id=patient_id,
            start_date=normalized_start_date,
            per_group=per_group,
            limit=limit,
        )

    def get_pattern_date_window_randomized_paths(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        per_group: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized rows constrained to non-null training dates."""
        return self.get_pattern_randomized_paths(
            pattern=pattern,
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=patient_id,
            per_group=per_group,
            limit=limit,
        )

    def get_pattern_date_window_randomized_paths_by_start_date(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        start_date: str,
        per_group: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized rows constrained from a start date without date order."""
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        return self.get_pattern_randomized_paths(
            pattern=pattern,
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=patient_id,
            start_date=normalized_start_date,
            per_group=per_group,
            limit=limit,
        )

    def get_pattern_date_window_randomized_paths_by_end_date(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        end_date: str,
        per_group: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized rows constrained before an end date without date order."""
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        return self.get_pattern_randomized_paths(
            pattern=pattern,
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=patient_id,
            end_date=normalized_end_date,
            per_group=per_group,
            limit=limit,
        )

    def get_pattern_date_window_randomized_paths_by_date_range(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        start_date: str,
        end_date: str,
        per_group: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized rows in a date range without date order."""
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        return self.get_pattern_randomized_paths(
            pattern=pattern,
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=patient_id,
            start_date=normalized_start_date,
            end_date=normalized_end_date,
            per_group=per_group,
            limit=limit,
        )

    def get_pattern_training_order_randomized_paths(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        per_group: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized rows with s1/s2 training-date order."""
        return self.get_pattern_randomized_paths(
            pattern=pattern,
            query_family=PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW,
            patient_id=patient_id,
            per_group=per_group,
            limit=limit,
        )

    def get_pattern_dated_randomized_paths_by_end_date(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        end_date: str,
        per_group: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return date-aware randomized rows before an end date."""
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        return self.get_pattern_randomized_paths(
            pattern=pattern,
            query_family=PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW,
            patient_id=patient_id,
            end_date=normalized_end_date,
            per_group=per_group,
            limit=limit,
        )

    def get_pattern_randomized_paths_by_date_range(
        self,
        pattern: PathPattern | str,
        patient_id: str,
        start_date: str,
        end_date: str,
        per_group: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized rows for a registered pattern in a date range."""
        normalized_start_date = self._normalize_required_string(start_date, "start_date")
        normalized_end_date = self._normalize_required_string(end_date, "end_date")
        return self.get_pattern_randomized_paths(
            pattern=pattern,
            query_family=PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW,
            patient_id=patient_id,
            start_date=normalized_start_date,
            end_date=normalized_end_date,
            per_group=per_group,
            limit=limit,
        )

    def get_pattern_randomized_paths(
        self,
        *,
        pattern: PathPattern | str,
        query_family: PatternQueryFamily | str,
        patient_id: str,
        per_group: int,
        limit: int,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[dict[str, object]]:
        """Return randomized paths for one pattern family and optional date bounds."""
        spec = get_path_pattern_spec(pattern)
        normalized_query_family = self._normalize_pattern_query_family(query_family)
        normalized_patient_id = patient_id.strip()
        normalized_start_date = self._normalize_optional_string(start_date, "start_date")
        normalized_end_date = self._normalize_optional_string(end_date, "end_date")
        date_window = QueryDateWindow(
            start_date=normalized_start_date,
            end_date=normalized_end_date,
        )
        if not normalized_patient_id:
            raise ValueError("patient_id must be a non-empty string.")
        if (
            not isinstance(per_group, int)
            or isinstance(per_group, bool)
            or per_group <= 0
        ):
            raise ValueError("per_g must be a positive integer.")
        if not isinstance(limit, int) or isinstance(limit, bool) or limit <= 0:
            raise ValueError("limit must be a positive integer.")

        query = spec.queries.family(
            normalized_query_family.value
        ).randomized_path.select(date_window)
        return self.client.run_query(
            query=query,
            parameters=self._build_pattern_path_parameters(
                patient_id=normalized_patient_id,
                per_group=per_group,
                limit=limit,
                date_window=date_window,
            ),
        )

    def get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_start_date(
        self,
        patient_id: str,
        start_date: str,
        per_g: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized fixed-pattern rows constrained from a start date."""
        return self.get_pattern_randomized_paths_by_start_date(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            patient_id,
            start_date,
            per_group=per_g,
            limit=limit,
        )

    def get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date(
        self,
        patient_id: str,
        end_date: str,
        per_g: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized fixed-pattern rows constrained before an end date."""
        return self.get_pattern_dated_randomized_paths_by_end_date(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            patient_id,
            end_date,
            per_group=per_g,
            limit=limit,
        )

    def get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
        per_g: int,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return randomized fixed-pattern rows constrained to a date range."""
        return self.get_pattern_randomized_paths_by_date_range(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            patient_id,
            start_date,
            end_date,
            per_group=per_g,
            limit=limit,
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

    @staticmethod
    def _normalize_optional_string(value: str | None, field_name: str) -> str | None:
        """Validate and normalize an optional string parameter."""
        if value is None:
            return None
        if not isinstance(value, str):
            raise ValueError(f"{field_name} must be a non-empty string or None.")

        normalized_value = value.strip()
        if not normalized_value:
            raise ValueError(f"{field_name} must be a non-empty string or None.")

        return normalized_value

    @staticmethod
    def _normalize_pattern_query_family(
        value: PatternQueryFamily | str,
    ) -> PatternQueryFamily:
        """Normalize a raw query-family value."""
        if isinstance(value, PatternQueryFamily):
            return value
        if isinstance(value, str) and value.strip():
            return PatternQueryFamily(value.strip())
        raise ValueError("query_family must be a supported pattern query family.")

    @staticmethod
    def _select_pattern_statistics_query(
        queries: PatternQuerySet,
        query_family: PatternQueryFamily,
        *,
        date_window: QueryDateWindow,
    ) -> str:
        """Select the static statistics query for one family and date shape."""
        return queries.family(query_family.value).statistics.select(date_window)

    @staticmethod
    def _build_pattern_path_parameters(
        *,
        patient_id: str,
        per_group: int,
        limit: int,
        date_window: QueryDateWindow,
    ) -> dict[str, object]:
        """Build randomized path query parameters for the selected date shape."""
        parameters: dict[str, object] = {
            "patient_id": patient_id,
            "per_g": per_group,
            "limit": limit,
        }
        parameters.update(date_window.parameters())
        return parameters

    def _run_patient_pair_query_by_end_date(
        self,
        *,
        query: str,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Run a two-patient query constrained before an end date."""
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
