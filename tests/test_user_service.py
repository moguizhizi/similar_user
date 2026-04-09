"""Tests for user service behavior."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.similar_user.services.user_service import UserService


class UserServiceTest(unittest.TestCase):
    def test_get_patient_pattern_paths_returns_empty_payload_when_no_training_dates(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = []
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_pattern_paths("30010096")

        self.assertEqual(
            result,
            {
                "patient_id": "30010096",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "statistics": None,
                "limit_recommendation": None,
                "paths": [],
            },
        )

    def test_get_patient_pattern_paths_returns_statistics_only_when_no_paths(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = [
            {"orderedDatesa": ["2022-01-01", "2022-01-13"]}
        ]
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics.return_value = [
            {"totalPaths": 0, "gCount": 0, "p2Count": 0}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_pattern_paths("30010096")

        self.assertEqual(result["ordered_training_dates"], ["2022-01-01", "2022-01-13"])
        self.assertEqual(result["statistics"], {"totalPaths": 0, "gCount": 0, "p2Count": 0})
        self.assertIsNone(result["limit_recommendation"])
        self.assertEqual(result["paths"], [])
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics.assert_called_once_with(
            "30010096"
        )

    def test_get_patient_pattern_paths_returns_paths_with_recommendation(self) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = [
            {"orderedDatesa": ["2022-01-01", "2022-01-13"]}
        ]
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics.return_value = [
            {"totalPaths": 12, "gCount": 3, "p2Count": 4}
        ]
        mock_repository.recommend_graph_path_limit.return_value.per_g = 5
        mock_repository.recommend_graph_path_limit.return_value.limit = 10
        mock_repository.get_patient_task_set_task_game_task_set_patient_randomized_paths.return_value = [
            {"path": ["mocked-path"]}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_pattern_paths("30010096")

        self.assertEqual(result["first_training_date"], "2022-01-01")
        self.assertEqual(result["last_training_date"], "2022-01-13")
        self.assertEqual(result["training_date_count"], 2)
        self.assertEqual(result["statistics"], {"totalPaths": 12, "gCount": 3, "p2Count": 4})
        self.assertEqual(result["limit_recommendation"], {"per_g": 5, "limit": 10})
        self.assertEqual(result["paths"], [{"path": ["mocked-path"]}])
        mock_repository.recommend_graph_path_limit.assert_called_once_with(
            total_paths=12,
            g_count=3,
        )
        mock_repository.get_patient_task_set_task_game_task_set_patient_randomized_paths.assert_called_once_with(
            patient_id="30010096",
            per_g=5,
            limit=10,
        )

    def test_get_patient_pattern_paths_can_use_undated_statistics(self) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = [
            {"orderedDatesa": ["2022-01-01"]}
        ]
        mock_repository.get_patient_task_set_task_game_task_set_patient_pattern_statistics.return_value = [
            {"totalPaths": 5, "gCount": 1, "p2Count": 1}
        ]
        mock_repository.recommend_graph_path_limit.return_value.per_g = 4
        mock_repository.recommend_graph_path_limit.return_value.limit = 4
        mock_repository.get_patient_task_set_task_game_task_set_patient_randomized_paths.return_value = []
        service = UserService(kg_repository=mock_repository)

        service.get_patient_pattern_paths("30010096", use_dated_statistics=False)

        mock_repository.get_patient_task_set_task_game_task_set_patient_pattern_statistics.assert_called_once_with(
            "30010096"
        )

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
