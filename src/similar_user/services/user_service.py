"""User-facing service orchestration."""

from __future__ import annotations

from dataclasses import dataclass

from ..data_access.kg_repository import KgRepository


@dataclass
class UserService:
    """Application-facing helpers built on top of repository reads."""

    kg_repository: KgRepository

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
