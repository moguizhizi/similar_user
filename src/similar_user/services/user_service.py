"""User-facing service orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from ..domain.graph_schema import PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT
from ..data_access.kg_repository import KgRepository
from ..utils.logger import get_logger


LOGGER = get_logger(__name__)


@dataclass
class UserService:
    """Application-facing helpers built on top of repository reads."""

    kg_repository: KgRepository

    def get_patient_ids(self) -> list[str]:
        """Return all patient IDs in the graph."""
        return self.kg_repository.get_patient_ids()

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

    def get_patient_pattern_paths(
        self,
        patient_id: str,
        base_date: str,
        window_days: int,
    ) -> dict[str, Any]:
        """Run the end-to-end fixed-pattern path flow for a patient date window."""
        path_window = self._build_path_window(base_date, window_days)
        LOGGER.info(
            "Starting patient pattern path flow in service: patient_id=%s, base_date=%s, window_days=%s",
            patient_id,
            path_window["base_date"],
            path_window["window_days"],
        )

        training_context = self._build_training_context(patient_id)
        self._log_training_context(training_context)

        statistics, active_statistics = self._load_window_statistics(
            patient_id,
            path_window,
        )

        total_paths = int(active_statistics.get("totalPaths", 0))
        g_count = int(active_statistics.get("gCount", 0))
        p2_count = int(active_statistics.get("p2Count", 0))

        if total_paths <= 0:
            LOGGER.warning(
                "No available paths after statistics evaluation: patient_id=%s, active_statistics=%s",
                patient_id,
                active_statistics,
            )
            return self._build_pattern_result(
                training_context=training_context,
                statistics=statistics,
                limit_recommendation=None,
                paths=[],
            )

        recommendation = self.kg_repository.recommend_graph_path_limit(
            total_paths=total_paths,
            g_count=g_count,
            p2_count=p2_count,
        )

        limit_recommendation = {
            "per_g": recommendation.per_g,
            "limit": recommendation.limit,
        }

        LOGGER.info(
            "Calculated path limit recommendation: patient_id=%s, per_g=%s, limit=%s",
            patient_id,
            recommendation.per_g,
            recommendation.limit,
        )

        if recommendation.limit <= 0:
            LOGGER.warning(
                "Recommendation limit is non-positive: patient_id=%s, limit_recommendation=%s",
                patient_id,
                limit_recommendation,
            )
            return self._build_pattern_result(
                training_context=training_context,
                statistics=statistics,
                limit_recommendation=limit_recommendation,
                paths=[],
            )

        paths = self.kg_repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_date_range(
            patient_id=patient_id,
            start_date=path_window["start_date"],
            end_date=path_window["end_date"],
            per_g=recommendation.per_g,
            limit=recommendation.limit,
        )

        LOGGER.info(
            "Loaded randomized paths: patient_id=%s, path_count=%s",
            patient_id,
            len(paths),
        )

        LOGGER.debug(
            "Patient pattern path flow result in service: patient_id=%s, statistics_summary=%s, limit_recommendation=%s",
            patient_id,
            self._summarize_statistics_for_logging(statistics),
            limit_recommendation,
        )

        return self._build_pattern_result(
            training_context=training_context,
            statistics=statistics,
            limit_recommendation=limit_recommendation,
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
        path_window: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Load path statistics for the configured left-closed, right-open window."""
        statistics_records = (
            self.kg_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_date_range(
                patient_id,
                path_window["start_date"],
                path_window["end_date"],
            )
        )

        window_statistics = self._extract_statistics(statistics_records)
        statistics = {
            "base_date": path_window["base_date"],
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
    def _build_training_context(
        patient_id: str,
    ) -> dict[str, Any]:
        """Build a normalized context payload for path generation."""
        return {
            "patient_id": patient_id,
            "ordered_training_dates": [],
            "first_training_date": None,
            "last_training_date": None,
            "training_date_count": 0,
        }

    @staticmethod
    def _build_empty_pattern_result(patient_id: str) -> dict[str, Any]:
        """Build the empty result payload for patients without training dates."""
        return {
            "patient_id": patient_id,
            "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            "ordered_training_dates": [],
            "first_training_date": None,
            "last_training_date": None,
            "training_date_count": 0,
            "retrieval_context": None,
        }

    @staticmethod
    def _build_pattern_result(
        *,
        training_context: dict[str, Any],
        statistics: dict[str, Any] | None,
        limit_recommendation: dict[str, int] | None,
        paths: list[dict[str, object]],
    ) -> dict[str, Any]:
        """Build the standard patient pattern path result payload."""
        retrieval_context = (
            None
            if statistics is None and limit_recommendation is None and not paths
            else {
                "base_date": statistics.get("base_date") if isinstance(statistics, dict) else None,
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
            **training_context,
            "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            "retrieval_context": retrieval_context,
        }

    @staticmethod
    def _log_training_context(training_context: dict[str, Any]) -> None:
        """Log the basic context for the patient path flow."""
        LOGGER.info(
            "Initialized path flow context: patient_id=%s",
            training_context["patient_id"],
        )

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
