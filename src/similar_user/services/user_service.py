"""User-facing service orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..data_access.kg_repository import KgRepository


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
        ordered_dates = self.get_patient_ordered_training_dates(patient_id)
        if not ordered_dates:
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

        training_context = {
            "patient_id": patient_id,
            "ordered_training_dates": ordered_dates,
            "first_training_date": ordered_dates[0],
            "last_training_date": ordered_dates[-1],
            "training_date_count": len(ordered_dates),
        }

        if use_dated_statistics:
            statistics_records = (
                self.kg_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics(
                    patient_id
                )
            )
        else:
            statistics_records = (
                self.kg_repository.get_patient_task_set_task_game_task_set_patient_pattern_statistics(
                    patient_id
                )
            )

        statistics = statistics_records[0] if statistics_records else {
            "totalPaths": 0,
            "gCount": 0,
            "p2Count": 0,
        }
        total_paths = int(statistics.get("totalPaths", 0))
        g_count = int(statistics.get("gCount", 0))

        if total_paths <= 0:
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

        if recommendation.limit <= 0:
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

        return {
            **training_context,
            "statistics": statistics,
            "limit_recommendation": limit_recommendation,
            "paths": paths,
        }

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
