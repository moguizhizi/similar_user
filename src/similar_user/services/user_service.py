"""User-facing service orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from config.settings import load_query_settings

from ..domain.graph_schema import PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT
from ..data_access.kg_repository import KgRepository
from ..utils.logger import get_logger


LOGGER = get_logger(__name__)


@dataclass
class UserService:
    """Application-facing helpers built on top of repository reads."""

    kg_repository: KgRepository

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
        """Return distinct games for one patient up to and including an end date."""
        return self.kg_repository.get_patient_distinct_games_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_game_norm_score_series_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game-level norm-score series for two patients up to an end date."""
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
        """Return distinct task instances for one patient up to and including an end date."""
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
        """Return distinct symptoms for one patient up to and including an end date."""
        return self.kg_repository.get_patient_distinct_symptoms_by_end_date(
            patient_id,
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

    def get_patient_distinct_diseases_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct diseases for one patient up to and including an end date."""
        return self.kg_repository.get_patient_distinct_diseases_by_end_date(
            patient_id,
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
        """Return distinct unknown-category nodes for one patient up to and including an end date."""
        return self.kg_repository.get_patient_distinct_unknowns_by_end_date(
            patient_id,
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

    def get_patient_pattern_paths(
        self,
        patient_id: str,
    ) -> dict[str, Any]:
        """Run the end-to-end fixed-pattern path flow for a patient."""
        LOGGER.info(
            "Starting patient pattern path flow in service: patient_id=%s",
            patient_id,
        )

        ordered_dates = self.get_patient_ordered_training_dates(patient_id)
        if not ordered_dates:
            LOGGER.warning(
                "No training dates found for patient pattern path flow: patient_id=%s",
                patient_id,
            )
            return self._build_empty_pattern_result(patient_id)

        training_context = self._build_training_context(patient_id, ordered_dates)
        self._log_training_context(training_context)

        split_settings = load_query_settings(
            self.kg_repository.config_path
        ).training_date_split
        if len(ordered_dates) < split_settings.min_training_dates:
            LOGGER.warning(
                "Training dates do not meet minimum split requirement: patient_id=%s, training_date_count=%s, min_training_dates=%s",
                patient_id,
                len(ordered_dates),
                split_settings.min_training_dates,
            )
            return self._build_pattern_result(
                training_context=training_context,
                statistics=None,
                limit_recommendation=None,
                paths=[],
            )

        statistics, active_statistics, split_date = self._load_dated_statistics(
            patient_id,
            ordered_dates,
            split_settings.before_ratio,
            split_settings.after_ratio,
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

        paths = self.kg_repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date(
            patient_id=patient_id,
            end_date=split_date,
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

    def _load_dated_statistics(
        self,
        patient_id: str,
        ordered_dates: list[str],
        before_ratio: int,
        after_ratio: int,
    ) -> tuple[dict[str, Any], dict[str, int], str]:
        """Load pre-split statistics and post-split game data."""
        split_date = self._select_training_date_split_point(
            ordered_dates,
            before_ratio,
            after_ratio,
        )

        LOGGER.info(
            "Selected training date split point: patient_id=%s, split_training_date=%s, before_ratio=%s, after_ratio=%s",
            patient_id,
            split_date,
            before_ratio,
            after_ratio,
        )

        statistics_by_end_date_records = (
            self.kg_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date(
                patient_id,
                split_date,
            )
        )
        post_split_games = self.kg_repository.get_patient_training_date_games_by_start_date(
                patient_id,
                split_date,
        )

        statistics_by_end_date = self._extract_statistics(statistics_by_end_date_records)
        statistics = {
            "split_training_date": split_date,
            "before_split": statistics_by_end_date,
            "post_split_games": post_split_games,
        }

        LOGGER.info(
            "Loaded dated statistics: patient_id=%s, before_split=%s, post_split_games_size=%s",
            patient_id,
            statistics_by_end_date,
            len(post_split_games),
        )

        return statistics, statistics_by_end_date, split_date

    @staticmethod
    def _build_training_context(
        patient_id: str,
        ordered_dates: list[str],
    ) -> dict[str, Any]:
        """Build a normalized training context payload."""
        return {
            "patient_id": patient_id,
            "ordered_training_dates": ordered_dates,
            "first_training_date": ordered_dates[0],
            "last_training_date": ordered_dates[-1],
            "training_date_count": len(ordered_dates),
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
                "split_training_date": (
                    statistics.get("split_training_date")
                    if isinstance(statistics, dict)
                    else None
                ),
                "before_split": (
                    statistics.get("before_split")
                    if isinstance(statistics, dict)
                    else None
                ),
                "post_split_games": (
                    statistics.get("post_split_games")
                    if isinstance(statistics, dict)
                    else []
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
        """Log the basic training context for the patient path flow."""
        LOGGER.info(
            "Loaded ordered training dates: patient_id=%s, training_date_count=%s, first_training_date=%s, last_training_date=%s",
            training_context["patient_id"],
            training_context["training_date_count"],
            training_context["first_training_date"],
            training_context["last_training_date"],
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

        post_split_games = statistics.get("post_split_games")
        post_split_games_size = (
            len(post_split_games) if isinstance(post_split_games, list) else None
        )
        return {
            "split_training_date": statistics.get("split_training_date"),
            "before_split": statistics.get("before_split"),
            "post_split_games_size": post_split_games_size,
        }

    @staticmethod
    def _select_training_date_split_point(
        ordered_dates: list[str],
        before_ratio: int,
        after_ratio: int,
    ) -> str:
        """Select a split point based on the configured before/after ratio."""
        if not ordered_dates:
            raise ValueError("ordered_dates must contain at least one date.")
        if before_ratio <= 0 or after_ratio <= 0:
            raise ValueError("before_ratio and after_ratio must be positive integers.")

        total_ratio = before_ratio + after_ratio
        split_index = ((len(ordered_dates) * before_ratio) + total_ratio - 1) // total_ratio - 1
        split_index = max(0, min(split_index, len(ordered_dates) - 1))
        return ordered_dates[split_index]
