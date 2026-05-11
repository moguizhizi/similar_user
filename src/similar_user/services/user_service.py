"""User-facing service orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from ..domain.graph_schema import PathPattern
from ..data_access.kg_repository import KgRepository, PatternQueryFamily
from ..data_access.pattern_registry import (
    PatternQueryMode,
    get_path_pattern_spec,
)
from ..utils.logger import get_logger


LOGGER = get_logger(__name__)


@dataclass
class UserService:
    """Application-facing helpers built on top of repository reads."""

    kg_repository: KgRepository

    def get_patient_ids(self) -> list[str]:
        """Return all patient IDs in the graph."""
        return self.kg_repository.get_patient_ids()

    def get_patient_ids_with_training_on_date(self, base_date: str) -> list[str]:
        """Return patient IDs with training records on base_date."""
        return self.kg_repository.get_patient_ids_with_training_on_date(base_date)

    def get_distinct_training_games(self) -> list[dict[str, object]]:
        """Return distinct games that appear in training records."""
        return self.kg_repository.get_distinct_training_games()

    def get_patient_training_date_games_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return training-date grouped games from the given start date."""
        return self.kg_repository.get_patient_training_date_games_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_distinct_games_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct games for one patient before an end date."""
        return self.kg_repository.get_patient_distinct_games_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_distinct_games_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct games for one patient from a start date."""
        return self.kg_repository.get_patient_distinct_games_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_distinct_games_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct games for one patient within a date range."""
        return self.kg_repository.get_patient_distinct_games_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_games_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game rows for one patient before an end date."""
        return self.kg_repository.get_patient_games_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_games_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return game rows for one patient from a start date."""
        return self.kg_repository.get_patient_games_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_games_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game rows for one patient within a date range."""
        return self.kg_repository.get_patient_games_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_game_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game sets for two patients before an end date."""
        return self.kg_repository.get_patient_game_set_comparison_by_end_date(
            primary_patient_id,
            comparison_patient_id,
            end_date,
        )

    def get_patient_game_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return game sets for two patients from a start date."""
        return self.kg_repository.get_patient_game_set_comparison_by_start_date(
            primary_patient_id,
            comparison_patient_id,
            start_date,
        )

    def get_patient_game_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game sets for two patients within a date range."""
        return self.kg_repository.get_patient_game_set_comparison_by_date_range(
            primary_patient_id,
            comparison_patient_id,
            start_date,
            end_date,
        )

    def get_patient_game_norm_score_series_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game-level norm-score series for two patients before an end date."""
        return self.kg_repository.get_patient_game_norm_score_series_comparison_by_end_date(
            primary_patient_id,
            comparison_patient_id,
            end_date,
        )

    def get_patient_distinct_task_instances_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct task instances for one patient from a start date."""
        return self.kg_repository.get_patient_distinct_task_instances_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_distinct_task_instances_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct task instances for one patient before an end date."""
        return self.kg_repository.get_patient_distinct_task_instances_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_distinct_task_instances_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct task instances for one patient within a date range."""
        return self.kg_repository.get_patient_distinct_task_instances_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_distinct_symptoms_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct symptoms for one patient before an end date."""
        return self.kg_repository.get_patient_distinct_symptoms_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_symptom_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return symptom sets for two patients before an end date."""
        return self.kg_repository.get_patient_symptom_set_comparison_by_end_date(
            primary_patient_id,
            comparison_patient_id,
            end_date,
        )

    def get_patient_distinct_symptoms_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct symptoms for one patient from a start date."""
        return self.kg_repository.get_patient_distinct_symptoms_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_symptom_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return symptom sets for two patients from a start date."""
        return self.kg_repository.get_patient_symptom_set_comparison_by_start_date(
            primary_patient_id,
            comparison_patient_id,
            start_date,
        )

    def get_patient_distinct_symptoms_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct symptoms for one patient within a date range."""
        return self.kg_repository.get_patient_distinct_symptoms_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_symptom_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return symptom sets for two patients within a date range."""
        return self.kg_repository.get_patient_symptom_set_comparison_by_date_range(
            primary_patient_id,
            comparison_patient_id,
            start_date,
            end_date,
        )

    def get_patient_distinct_diseases_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct diseases for one patient before an end date."""
        return self.kg_repository.get_patient_distinct_diseases_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_disease_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return disease sets for two patients before an end date."""
        return self.kg_repository.get_patient_disease_set_comparison_by_end_date(
            primary_patient_id,
            comparison_patient_id,
            end_date,
        )

    def get_patient_disease_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return disease sets for two patients from a start date."""
        return self.kg_repository.get_patient_disease_set_comparison_by_start_date(
            primary_patient_id,
            comparison_patient_id,
            start_date,
        )

    def get_patient_disease_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return disease sets for two patients within a date range."""
        return self.kg_repository.get_patient_disease_set_comparison_by_date_range(
            primary_patient_id,
            comparison_patient_id,
            start_date,
            end_date,
        )

    def get_patient_distinct_diseases_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct diseases for one patient from a start date."""
        return self.kg_repository.get_patient_distinct_diseases_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_distinct_diseases_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct diseases for one patient within a date range."""
        return self.kg_repository.get_patient_distinct_diseases_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_distinct_unknowns_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct unknown-category nodes for one patient before an end date."""
        return self.kg_repository.get_patient_distinct_unknowns_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_unknown_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return unknown-category sets for two patients before an end date."""
        return self.kg_repository.get_patient_unknown_set_comparison_by_end_date(
            primary_patient_id,
            comparison_patient_id,
            end_date,
        )

    def get_patient_distinct_unknowns_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct unknown-category nodes for one patient from a start date."""
        return self.kg_repository.get_patient_distinct_unknowns_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_unknown_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return unknown-category sets for two patients from a start date."""
        return self.kg_repository.get_patient_unknown_set_comparison_by_start_date(
            primary_patient_id,
            comparison_patient_id,
            start_date,
        )

    def get_patient_distinct_unknowns_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct unknown-category nodes for one patient within a date range."""
        return self.kg_repository.get_patient_distinct_unknowns_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_unknown_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return unknown-category sets for two patients within a date range."""
        return self.kg_repository.get_patient_unknown_set_comparison_by_date_range(
            primary_patient_id,
            comparison_patient_id,
            start_date,
            end_date,
        )

    def get_pattern_paths(
        self,
        source_id: str,
        base_date: str,
        window_days: int,
        pattern: PathPattern | str = PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        query_family: PatternQueryFamily | str | None = None,
    ) -> dict[str, Any]:
        """Run the end-to-end fixed-pattern path flow for one source node."""
        normalized_source_id = self._normalize_required_string(source_id, "source_id")
        spec = get_path_pattern_spec(pattern)
        normalized_pattern = spec.pattern
        path_window = self._build_path_window(base_date, window_days)
        LOGGER.info(
            "Starting pattern path flow in service: source_id=%s, source_parameter=%s, pattern=%s, query_mode=%s, base_date=%s, window_days=%s",
            normalized_source_id,
            spec.source_parameter,
            normalized_pattern.value,
            spec.query_mode.value,
            path_window["base_date"],
            path_window["window_days"],
        )

        if spec.query_mode == PatternQueryMode.DIRECT_PATH:
            if query_family is not None:
                raise ValueError(
                    f"Pattern {normalized_pattern.value} does not support query_family."
                )
            return self._get_direct_pattern_paths(
                source_id=normalized_source_id,
                pattern=normalized_pattern,
                source_parameter=spec.source_parameter,
                path_window=path_window,
            )
        elif spec.query_mode == PatternQueryMode.PAIRED_STATISTICS:
                return self._get_paired_statistics_pattern_paths(
                    source_id=normalized_source_id,
                    pattern=normalized_pattern,
                    source_parameter=spec.source_parameter,
                    query_family=query_family,
                    path_window=path_window,
                )
        else:
            raise ValueError(
                f"Unsupported pattern query mode for {normalized_pattern.value}: "
                f"{spec.query_mode}"
            )

    def _get_paired_statistics_pattern_paths(
        self,
        *,
        source_id: str,
        pattern: PathPattern,
        source_parameter: str,
        query_family: PatternQueryFamily | str | None,
        path_window: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a statistics-guided randomized path query for one pattern family."""
        normalized_query_family = (
            PatternQueryFamily.TRAINING_ORDER
            if query_family is None
            else self._normalize_pattern_query_family(query_family)
        )
        source_context = self._build_source_context(
            source_id,
            source_parameter,
        )
        self._log_source_context(source_context)

        statistics, active_statistics = self._load_window_statistics(
            source_id,
            pattern,
            normalized_query_family,
            path_window,
        )

        total_paths = int(active_statistics.get("totalPaths", 0))
        group_count = self._extract_pattern_group_count(
            pattern,
            active_statistics,
        )
        p2_count = int(active_statistics.get("p2Count", 0))

        if total_paths <= 0:
            LOGGER.warning(
                "No available paths after statistics evaluation: source_id=%s, active_statistics=%s",
                source_id,
                active_statistics,
            )
            return self._build_pattern_result(
                source_context=source_context,
                pattern=pattern,
                query_family=normalized_query_family,
                statistics=statistics,
                limit_recommendation=None,
                paths=[],
            )

        recommendation = self.kg_repository.recommend_graph_path_limit(
            total_paths=total_paths,
            g_count=group_count,
            p2_count=p2_count,
        )

        limit_recommendation = {
            "per_g": recommendation.per_g,
            "limit": recommendation.limit,
        }

        LOGGER.info(
            "Calculated path limit recommendation: source_id=%s, per_g=%s, limit=%s",
            source_id,
            recommendation.per_g,
            recommendation.limit,
        )

        if recommendation.limit <= 0:
            LOGGER.warning(
                "Recommendation limit is non-positive: source_id=%s, limit_recommendation=%s",
                source_id,
                limit_recommendation,
            )
            return self._build_pattern_result(
                source_context=source_context,
                pattern=pattern,
                query_family=normalized_query_family,
                statistics=statistics,
                limit_recommendation=limit_recommendation,
                paths=[],
            )

        paths = self.kg_repository.get_pattern_randomized_paths(
            pattern=pattern,
            query_family=normalized_query_family,
            patient_id=source_id,
            start_date=path_window["start_date"],
            end_date=path_window["end_date"],
            per_group=recommendation.per_g,
            limit=recommendation.limit,
        )

        LOGGER.info(
            "Loaded randomized paths: source_id=%s, path_count=%s",
            source_id,
            len(paths),
        )

        LOGGER.debug(
            "Pattern path flow result in service: source_id=%s, statistics_summary=%s, limit_recommendation=%s",
            source_id,
            self._summarize_statistics_for_logging(statistics),
            limit_recommendation,
        )

        return self._build_pattern_result(
            source_context=source_context,
            pattern=pattern,
            query_family=normalized_query_family,
            statistics=statistics,
            limit_recommendation=limit_recommendation,
            paths=paths,
        )

    def _get_direct_pattern_paths(
        self,
        *,
        source_id: str,
        pattern: PathPattern,
        source_parameter: str,
        path_window: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a direct path query for a source-driven pattern."""
        if pattern == PathPattern.DISEASE_TASKSET_PATIENT:
            paths = self.kg_repository.get_disease_taskset_patient_randomized_paths(
                source_id,
                start_date=path_window["start_date"],
                end_date=path_window["end_date"],
            )
        elif pattern == PathPattern.SYMPTOM_TASKSET_PATIENT:
            paths = self.kg_repository.get_symptom_taskset_patient_randomized_paths(
                source_id,
                start_date=path_window["start_date"],
                end_date=path_window["end_date"],
            )
        elif pattern == PathPattern.UNKNOWN_TASKSET_PATIENT:
            paths = self.kg_repository.get_unknown_taskset_patient_randomized_paths(
                source_id,
                start_date=path_window["start_date"],
                end_date=path_window["end_date"],
            )
        else:
            raise ValueError(f"Unsupported direct path pattern: {pattern.value}")

        LOGGER.info(
            "Loaded direct randomized paths: source_id=%s, pattern=%s, path_count=%s",
            source_id,
            pattern.value,
            len(paths),
        )
        statistics = {
            "base_date": path_window["base_date"],
            "query_family": None,
            "path_window": path_window,
            "window_statistics": None,
        }
        return self._build_pattern_result(
            source_context=self._build_source_context(source_id, source_parameter),
            pattern=pattern,
            query_family=None,
            statistics=statistics,
            limit_recommendation=None,
            paths=paths,
        )

    def get_patient_ordered_training_dates(self, patient_id: str) -> list[str]:
        """Return only the ordered TaskInstanceSet training dates for a patient."""
        records = self.kg_repository.get_patient_task_instance_set_ordered_training_dates(
            patient_id
        )
        if not records:
            return []

        ordered_dates = records[0].get("orderedDatesa", [])
        if not isinstance(ordered_dates, list):
            return []

        return [str(value) for value in ordered_dates]

    def get_patient_training_task_history(
        self,
        patient_id: str,
    ) -> list[dict[str, object]]:
        """Return dated task-instance and game rows for one patient."""
        return self.kg_repository.get_patient_training_task_history(patient_id)

    def get_patient_training_task_history_by_date_window(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return task history in a left-closed, right-open date window."""
        return self.kg_repository.get_patient_training_task_history_by_date_window(
            patient_id,
            start_date,
            end_date,
        )

    def _load_window_statistics(
        self,
        patient_id: str,
        pattern: PathPattern,
        query_family: PatternQueryFamily,
        path_window: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Load path statistics for the configured left-closed, right-open window."""
        statistics_records = (
            self.kg_repository.get_pattern_statistics(
                pattern=pattern,
                query_family=query_family,
                patient_id=patient_id,
                start_date=path_window["start_date"],
                end_date=path_window["end_date"],
            )
        )

        window_statistics = self._extract_statistics(statistics_records)
        statistics = {
            "base_date": path_window["base_date"],
            "query_family": query_family.value,
            "path_window": path_window,
            "window_statistics": window_statistics,
        }

        LOGGER.info(
            "Loaded path window statistics: patient_id=%s, path_window=%s, window_statistics=%s",
            patient_id,
            path_window,
            window_statistics,
        )

        return statistics, window_statistics

    @staticmethod
    def _build_source_context(
        source_id: str,
        source_parameter: str,
    ) -> dict[str, Any]:
        """Build a normalized context payload for path generation."""
        context: dict[str, Any] = {
            "source_id": source_id,
            "source_parameter": source_parameter,
            source_parameter: source_id,
            "ordered_training_dates": [],
            "first_training_date": None,
            "last_training_date": None,
            "training_date_count": 0,
        }
        return context

    @staticmethod
    def _build_pattern_result(
        *,
        source_context: dict[str, Any],
        pattern: PathPattern,
        query_family: PatternQueryFamily | None,
        statistics: dict[str, Any] | None,
        limit_recommendation: dict[str, int] | None,
        paths: list[dict[str, object]],
    ) -> dict[str, Any]:
        """Build the standard pattern path result payload."""
        retrieval_context = (
            None
            if statistics is None and limit_recommendation is None and not paths
            else {
                "base_date": statistics.get("base_date") if isinstance(statistics, dict) else None,
                "query_family": query_family.value if query_family is not None else None,
                "path_window": statistics.get("path_window") if isinstance(statistics, dict) else None,
                "window_statistics": (
                    statistics.get("window_statistics")
                    if isinstance(statistics, dict)
                    else None
                ),
                "limit_recommendation": limit_recommendation,
                "paths": paths,
            }
        )
        return {
            **source_context,
            "pattern": pattern.value,
            "retrieval_context": retrieval_context,
        }

    @staticmethod
    def _normalize_pattern_query_family(
        value: PatternQueryFamily | str,
    ) -> PatternQueryFamily:
        """Normalize a query family from public input."""
        if isinstance(value, PatternQueryFamily):
            return value
        if isinstance(value, str) and value.strip():
            return PatternQueryFamily(value.strip())
        raise ValueError("query_family must be a supported pattern query family.")

    @staticmethod
    def _log_source_context(source_context: dict[str, Any]) -> None:
        """Log the basic context for the pattern path flow."""
        LOGGER.info(
            "Initialized path flow context: source_id=%s, source_parameter=%s",
            source_context["source_id"],
            source_context["source_parameter"],
        )

    @staticmethod
    def _normalize_required_string(value: object, field_name: str) -> str:
        """Normalize and validate a required string."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string.")
        return value.strip()

    @staticmethod
    def _extract_statistics(records: list[dict[str, Any]]) -> dict[str, int]:
        """Return a normalized statistics mapping from repository results."""
        if not records:
            return {
                "totalPaths": 0,
                "gCount": 0,
                "p2Count": 0,
            }

        return records[0]

    @staticmethod
    def _extract_pattern_group_count(
        pattern: PathPattern,
        statistics: dict[str, Any],
    ) -> int:
        """Return the pattern-specific grouping count used for path limits."""
        group_field = get_path_pattern_spec(pattern).group_field
        group_count_key = f"{group_field}Count"
        return int(statistics.get(group_count_key, 0))

    @staticmethod
    def _summarize_statistics_for_logging(
        statistics: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Return a log-safe statistics summary without dumping game-level details."""
        if statistics is None:
            return None

        return {
            "base_date": statistics.get("base_date"),
            "path_window": statistics.get("path_window"),
            "window_statistics": statistics.get("window_statistics"),
        }

    @staticmethod
    def _build_path_window(base_date: str, window_days: int) -> dict[str, Any]:
        """Build the left-closed, right-open path retrieval window."""
        parsed_base_date = _parse_date_value(base_date, "base_date")
        if (
            not isinstance(window_days, int)
            or isinstance(window_days, bool)
            or window_days <= 0
        ):
            raise ValueError(f"window_days must be a positive integer, got {window_days}.")
        start_date = parsed_base_date - timedelta(days=window_days)
        return {
            "base_date": parsed_base_date.isoformat(),
            "start_date": start_date.isoformat(),
            "end_date": parsed_base_date.isoformat(),
            "window_days": window_days,
            "range_semantics": "[start_date, end_date)",
        }


def _parse_date_value(value: str, field_name: str) -> date:
    """Parse a user-provided date string into an ISO calendar date."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty date string.")
    parts = value.strip().split("-")
    if len(parts) != 3:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.")
    try:
        year, month, day = (int(part) for part in parts)
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid calendar date.") from exc
