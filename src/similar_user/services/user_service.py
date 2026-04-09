"""User-facing service orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..data_access.kg_repository import KgRepository
from ..utils.logger import get_logger


LOGGER = get_logger(__name__)


@dataclass
class UserService:
    """Application-facing helpers built on top of repository reads."""

    kg_repository: KgRepository

    def get_patient_pattern_paths(
        self,
        patient_id: str,
        *,
        use_dated_statistics: bool = True,
    ) -> dict[str, Any]:
        """Run the end-to-end fixed-pattern path flow for a patient."""
        LOGGER.info(
            "Starting patient pattern path flow in service: patient_id=%s, use_dated_statistics=%s",
            patient_id,
            use_dated_statistics,
        )

        ordered_dates = self.get_patient_ordered_training_dates(patient_id)
        if not ordered_dates:
            LOGGER.info(
                "No training dates found for patient pattern path flow: patient_id=%s",
                patient_id,
            )
            return self._build_empty_pattern_result(patient_id)

        training_context = self._build_training_context(patient_id, ordered_dates)
        self._log_training_context(training_context)

        if use_dated_statistics:
            statistics, active_statistics = self._load_dated_statistics(
                patient_id,
                ordered_dates,
            )
        else:
            statistics, active_statistics = self._load_undated_statistics(patient_id)

        total_paths = int(active_statistics.get("totalPaths", 0))
        g_count = int(active_statistics.get("gCount", 0))

        if total_paths <= 0:
            LOGGER.info(
                "No available paths after statistics evaluation: patient_id=%s, active_statistics=%s",
                patient_id,
                active_statistics,
            )
            return {
                **training_context,
                "statistics": statistics,
                "limit_recommendation": None,
                "paths": [],
            }

        recommendation = self.kg_repository.recommend_graph_path_limit(
            total_paths=total_paths,
            g_count=g_count,
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
            LOGGER.info(
                "Recommendation limit is non-positive: patient_id=%s, limit_recommendation=%s",
                patient_id,
                limit_recommendation,
            )
            return {
                **training_context,
                "statistics": statistics,
                "limit_recommendation": limit_recommendation,
                "paths": [],
            }

        paths = self.kg_repository.get_patient_task_set_task_game_task_set_patient_randomized_paths(
            patient_id=patient_id,
            per_g=recommendation.per_g,
            limit=recommendation.limit,
        )

        LOGGER.info(
            "Loaded randomized paths: patient_id=%s, path_count=%s",
            patient_id,
            len(paths),
        )

        LOGGER.debug(
            "Patient pattern path flow result in service: patient_id=%s, statistics=%s, limit_recommendation=%s",
            patient_id,
            statistics,
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
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Load split statistics using a 4:1 training date split point."""
        split_date = self._select_training_date_split_point(ordered_dates)

        LOGGER.info(
            "Selected training date split point: patient_id=%s, split_training_date=%s",
            patient_id,
            split_date,
        )

        statistics_by_end_date_records = (
            self.kg_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date(
                patient_id,
                split_date,
            )
        )
        statistics_by_start_date_records = (
            self.kg_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_start_date(
                patient_id,
                split_date,
            )
        )

        statistics_by_end_date = self._extract_statistics(statistics_by_end_date_records)
        statistics_by_start_date = self._extract_statistics(
            statistics_by_start_date_records
        )
        statistics = {
            "split_training_date": split_date,
            "before_split": statistics_by_end_date,
            "after_split": statistics_by_start_date,
        }

        LOGGER.info(
            "Loaded dated statistics: patient_id=%s, before_split=%s, after_split=%s",
            patient_id,
            statistics_by_end_date,
            statistics_by_start_date,
        )

        return statistics, statistics_by_end_date

    def _load_undated_statistics(
        self,
        patient_id: str,
    ) -> tuple[dict[str, int], dict[str, int]]:
        """Load undated fixed-pattern statistics."""
        statistics_records = (
            self.kg_repository.get_patient_task_set_task_game_task_set_patient_pattern_statistics(
                patient_id
            )
        )
        statistics = self._extract_statistics(statistics_records)

        LOGGER.info(
            "Loaded undated statistics: patient_id=%s, statistics=%s",
            patient_id,
            statistics,
        )

        return statistics, statistics

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
            "ordered_training_dates": [],
            "first_training_date": None,
            "last_training_date": None,
            "training_date_count": 0,
            "statistics": None,
            "limit_recommendation": None,
            "paths": [],
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
        return {
            **training_context,
            "statistics": statistics,
            "limit_recommendation": limit_recommendation,
            "paths": paths,
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
    def _select_training_date_split_point(ordered_dates: list[str]) -> str:
        """Select a split point so earlier vs later dates are approximately 4:1."""
        if not ordered_dates:
            raise ValueError("ordered_dates must contain at least one date.")

        split_index = ((len(ordered_dates) * 4) + 4) // 5 - 1
        split_index = max(0, min(split_index, len(ordered_dates) - 1))
        return ordered_dates[split_index]
