"""Tests for user service behavior."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from src.similar_user.domain.graph_schema import (
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
)
from src.similar_user.services.user_service import UserService


class UserServiceTest(unittest.TestCase):
    def test_get_patient_training_date_games_by_start_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_training_date_games_by_start_date.return_value = [
            {"trainingDate": "2022-01-13", "games": [{"id": "42"}]}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_training_date_games_by_start_date(
            "30010096",
            "2022-01-01",
        )

        self.assertEqual(
            result,
            [{"trainingDate": "2022-01-13", "games": [{"id": "42"}]}],
        )
        mock_repository.get_patient_training_date_games_by_start_date.assert_called_once_with(
            "30010096",
            "2022-01-01",
        )

    def test_get_patient_distinct_games_by_end_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_games_by_end_date.return_value = [
            {"g": {"id": "42", "name": "打怪物"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_games_by_end_date(
            "30010096",
            "2022-01-13",
        )

        self.assertEqual(result, [{"g": {"id": "42", "name": "打怪物"}}])
        mock_repository.get_patient_distinct_games_by_end_date.assert_called_once_with(
            "30010096",
            "2022-01-13",
        )

    def test_get_patient_game_norm_score_series_comparison_by_end_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_game_norm_score_series_comparison_by_end_date.return_value = [
            {"game": "打怪物", "scores_p1": ["91", "95"], "scores_p2": ["88", "93"]}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_game_norm_score_series_comparison_by_end_date(
            "40",
            "30000035",
            "2026-02-12",
        )

        self.assertEqual(
            result,
            [{"game": "打怪物", "scores_p1": ["91", "95"], "scores_p2": ["88", "93"]}],
        )
        mock_repository.get_patient_game_norm_score_series_comparison_by_end_date.assert_called_once_with(
            "40",
            "30000035",
            "2026-02-12",
        )

    def test_get_patient_distinct_task_instances_by_start_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_task_instances_by_start_date.return_value = [
            {"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_task_instances_by_start_date(
            "30010096",
            "2022-01-01",
        )

        self.assertEqual(
            result,
            [{"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}}],
        )
        mock_repository.get_patient_distinct_task_instances_by_start_date.assert_called_once_with(
            "30010096",
            "2022-01-01",
        )

    def test_get_patient_distinct_task_instances_by_end_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_task_instances_by_end_date.return_value = [
            {"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_task_instances_by_end_date(
            "30010096",
            "2022-01-13",
        )

        self.assertEqual(
            result,
            [{"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}}],
        )
        mock_repository.get_patient_distinct_task_instances_by_end_date.assert_called_once_with(
            "30010096",
            "2022-01-13",
        )

    def test_get_patient_distinct_task_instances_by_date_range_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_task_instances_by_date_range.return_value = [
            {"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_task_instances_by_date_range(
            "30010096",
            "2022-01-01",
            "2022-01-13",
        )

        self.assertEqual(
            result,
            [{"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}}],
        )
        mock_repository.get_patient_distinct_task_instances_by_date_range.assert_called_once_with(
            "30010096",
            "2022-01-01",
            "2022-01-13",
        )

    def test_get_patient_distinct_symptoms_by_end_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_symptoms_by_end_date.return_value = [
            {"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_symptoms_by_end_date(
            "30010096",
            "2022-01-01",
        )

        self.assertEqual(
            result,
            [{"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}}],
        )
        mock_repository.get_patient_distinct_symptoms_by_end_date.assert_called_once_with(
            "30010096",
            "2022-01-01",
        )

    def test_get_patient_distinct_symptoms_by_start_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_symptoms_by_start_date.return_value = [
            {"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_symptoms_by_start_date(
            "30010096",
            "2022-01-01",
        )

        self.assertEqual(
            result,
            [{"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}}],
        )
        mock_repository.get_patient_distinct_symptoms_by_start_date.assert_called_once_with(
            "30010096",
            "2022-01-01",
        )

    def test_get_patient_distinct_symptoms_by_date_range_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_symptoms_by_date_range.return_value = [
            {"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_symptoms_by_date_range(
            "30010096",
            "2022-01-01",
            "2022-01-13",
        )

        self.assertEqual(
            result,
            [{"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}}],
        )
        mock_repository.get_patient_distinct_symptoms_by_date_range.assert_called_once_with(
            "30010096",
            "2022-01-01",
            "2022-01-13",
        )

    def test_get_patient_distinct_diseases_by_end_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_diseases_by_end_date.return_value = [
            {"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_diseases_by_end_date(
            "30010096",
            "2022-01-01",
        )

        self.assertEqual(
            result,
            [{"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}}],
        )
        mock_repository.get_patient_distinct_diseases_by_end_date.assert_called_once_with(
            "30010096",
            "2022-01-01",
        )

    def test_get_patient_distinct_diseases_by_start_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_diseases_by_start_date.return_value = [
            {"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_diseases_by_start_date(
            "30010096",
            "2022-01-01",
        )

        self.assertEqual(
            result,
            [{"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}}],
        )
        mock_repository.get_patient_distinct_diseases_by_start_date.assert_called_once_with(
            "30010096",
            "2022-01-01",
        )

    def test_get_patient_distinct_diseases_by_date_range_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_diseases_by_date_range.return_value = [
            {"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_diseases_by_date_range(
            "30010096",
            "2022-01-01",
            "2022-01-13",
        )

        self.assertEqual(
            result,
            [{"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}}],
        )
        mock_repository.get_patient_distinct_diseases_by_date_range.assert_called_once_with(
            "30010096",
            "2022-01-01",
            "2022-01-13",
        )

    def test_get_patient_distinct_unknowns_by_end_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_unknowns_by_end_date.return_value = [
            {"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_unknowns_by_end_date(
            "30010096",
            "2022-01-01",
        )

        self.assertEqual(
            result,
            [{"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}}],
        )
        mock_repository.get_patient_distinct_unknowns_by_end_date.assert_called_once_with(
            "30010096",
            "2022-01-01",
        )

    def test_get_patient_distinct_unknowns_by_start_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_unknowns_by_start_date.return_value = [
            {"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_unknowns_by_start_date(
            "30010096",
            "2022-01-01",
        )

        self.assertEqual(
            result,
            [{"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}}],
        )
        mock_repository.get_patient_distinct_unknowns_by_start_date.assert_called_once_with(
            "30010096",
            "2022-01-01",
        )

    def test_get_patient_distinct_unknowns_by_date_range_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_unknowns_by_date_range.return_value = [
            {"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_unknowns_by_date_range(
            "30010096",
            "2022-01-01",
            "2022-01-13",
        )

        self.assertEqual(
            result,
            [{"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}}],
        )
        mock_repository.get_patient_distinct_unknowns_by_date_range.assert_called_once_with(
            "30010096",
            "2022-01-01",
            "2022-01-13",
        )

    @patch("src.similar_user.services.user_service.LOGGER")
    def test_get_patient_pattern_paths_returns_empty_payload_when_no_training_dates(
        self,
        mock_logger: Mock,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = []
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_pattern_paths("30010096")

        self.assertEqual(
            result,
            {
                "patient_id": "30010096",
                "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "retrieval_context": None,
            },
        )
        mock_logger.info.assert_called()

    def test_get_patient_pattern_paths_returns_statistics_only_when_no_paths(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = [
            {"orderedDatesa": ["2022-01-01", "2022-01-05", "2022-01-09", "2022-01-13", "2022-01-17"]}
        ]
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date.return_value = [
            {"totalPaths": 0, "gCount": 0, "p2Count": 0}
        ]
        mock_repository.get_patient_training_date_games_by_start_date.return_value = [
            {"trainingDate": "2022-01-13", "games": [{"id": "42"}]},
            {"trainingDate": "2022-01-17", "games": [{"id": "84"}]},
        ]
        mock_repository.recommend_graph_path_limit.return_value.per_g = 4
        mock_repository.recommend_graph_path_limit.return_value.limit = 10
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date.return_value = []
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_pattern_paths("30010096")

        self.assertEqual(
            result["ordered_training_dates"],
            ["2022-01-01", "2022-01-05", "2022-01-09", "2022-01-13", "2022-01-17"],
        )
        self.assertEqual(
            result["retrieval_context"],
            {
                "split_training_date": "2022-01-13",
                "before_split": {"totalPaths": 0, "gCount": 0, "p2Count": 0},
                "post_split_games": [
                    {"trainingDate": "2022-01-13", "games": [{"id": "42"}]},
                    {"trainingDate": "2022-01-17", "games": [{"id": "84"}]},
                ],
                "limit_recommendation": None,
                "paths": [],
            },
        )
        self.assertEqual(
            result["pattern"],
            PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        )
        mock_repository.recommend_graph_path_limit.assert_not_called()
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date.assert_not_called()
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date.assert_called_once_with(
            "30010096",
            "2022-01-13",
        )
        mock_repository.get_patient_training_date_games_by_start_date.assert_called_once_with(
            "30010096",
            "2022-01-13",
        )

    def test_get_patient_pattern_paths_returns_paths_with_recommendation(self) -> None:
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = [
            {"orderedDatesa": ["2022-01-01", "2022-01-05", "2022-01-09", "2022-01-13", "2022-01-17"]}
        ]
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date.return_value = [
            {"totalPaths": 20, "gCount": 5, "p2Count": 6}
        ]
        mock_repository.get_patient_training_date_games_by_start_date.return_value = [
            {"trainingDate": "2022-01-13", "games": [{"id": "42"}]},
            {"trainingDate": "2022-01-17", "games": [{"id": "84"}]},
        ]
        mock_repository.recommend_graph_path_limit.return_value.per_g = 5
        mock_repository.recommend_graph_path_limit.return_value.limit = 10
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date.return_value = [
            {
                "row": {
                    "p": {"id": "30010096"},
                    "s1": {"id": "40_20220516"},
                    "i1": {"id": "40_20220516_42_464CAOTKJK2BX3"},
                    "g": {"id": "42"},
                    "i2": {"id": "20113562_20211214_42_KUVB2LIK9KX60Y"},
                    "s2": {"id": "20113562_20211214"},
                    "p2": {"id": "20113562"},
                }
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_pattern_paths("30010096")

        self.assertEqual(result["first_training_date"], "2022-01-01")
        self.assertEqual(result["last_training_date"], "2022-01-17")
        self.assertEqual(result["training_date_count"], 5)
        self.assertEqual(
            result["pattern"],
            PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        )
        self.assertEqual(
            result["retrieval_context"],
            {
                "split_training_date": "2022-01-13",
                "before_split": {"totalPaths": 20, "gCount": 5, "p2Count": 6},
                "post_split_games": [
                    {"trainingDate": "2022-01-13", "games": [{"id": "42"}]},
                    {"trainingDate": "2022-01-17", "games": [{"id": "84"}]},
                ],
                "limit_recommendation": {"per_g": 5, "limit": 10},
                "paths": [
                    {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "40_20220516"},
                            "i1": {"id": "40_20220516_42_464CAOTKJK2BX3"},
                            "g": {"id": "42"},
                            "i2": {"id": "20113562_20211214_42_KUVB2LIK9KX60Y"},
                            "s2": {"id": "20113562_20211214"},
                            "p2": {"id": "20113562"},
                        }
                    }
                ],
            },
        )
        mock_repository.recommend_graph_path_limit.assert_called_once_with(
            total_paths=20,
            g_count=5,
            p2_count=6,
        )
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date.assert_called_once_with(
            patient_id="30010096",
            end_date="2022-01-13",
            per_g=5,
            limit=10,
        )

    def test_get_patient_pattern_paths_returns_early_when_training_dates_are_below_configured_minimum(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_repository.get_patient_task_instance_set_ordered_training_dates.return_value = [
            {"orderedDatesa": ["2022-01-01", "2022-01-13", "2022-01-21", "2022-01-30"]}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_pattern_paths("30010096")

        self.assertEqual(result["ordered_training_dates"], ["2022-01-01", "2022-01-13", "2022-01-21", "2022-01-30"])
        self.assertEqual(
            result["pattern"],
            PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        )
        self.assertEqual(result["retrieval_context"], None)
        mock_repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date.assert_not_called()
        mock_repository.get_patient_training_date_games_by_start_date.assert_not_called()

    def test_select_training_date_split_point_uses_approximately_four_to_one_ratio(
        self,
    ) -> None:
        service = UserService(kg_repository=Mock())

        result = service._select_training_date_split_point(
            ["2022-01-01", "2022-01-05", "2022-01-09", "2022-01-13", "2022-01-17"],
            4,
            1,
        )

        self.assertEqual(result, "2022-01-13")

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
