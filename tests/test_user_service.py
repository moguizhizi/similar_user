"""Tests for user service behavior."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.similar_user.services.user_service import UserService


class UserServiceTest(unittest.TestCase):
    def test_get_patient_ordered_training_dates_returns_dates_only(self) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = [
            {
                "p": {"id": "30010096"},
                "orderedDatesa": ["2022-01-01", "2022-01-13"],
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_ordered_training_dates("30010096")

        self.assertEqual(result, ["2022-01-01", "2022-01-13"])
        mock_repository.get_patient_task_instance_set_ordered_training_dates.assert_called_once_with(
            "30010096"
        )

    def test_get_patient_ordered_training_dates_returns_empty_list_for_no_records(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = []
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_ordered_training_dates("30010096")

        self.assertEqual(result, [])

    def test_get_patient_ordered_training_dates_returns_empty_list_for_missing_dates(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = [
            {"p": {"id": "30010096"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_ordered_training_dates("30010096")

        self.assertEqual(result, [])


if __name__ == "__main__":
    unittest.main()
