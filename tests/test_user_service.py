"""Tests for user service behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, call, patch

from src.similar_user.domain.graph_schema import (
    DISEASE_TASKSET_PATIENT,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT,
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    SYMPTOM_TASKSET_PATIENT,
    UNKNOWN_TASKSET_PATIENT,
    PathPattern,
)
from src.similar_user.data_access.kg_repository import PatternQueryFamily
from src.similar_user.services.user_service import UserService


class UserServiceTest(unittest.TestCase):
    def test_get_patient_ids_delegates_to_repository(self) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_ids.return_value = ["40", "41"]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_ids()

        self.assertEqual(result, ["40", "41"])
        mock_repository.get_patient_ids.assert_called_once_with()

    def test_get_patient_ids_with_training_on_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_ids_with_training_on_date.return_value = ["40"]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_ids_with_training_on_date("2022-05-22")

        self.assertEqual(result, ["40"])
        mock_repository.get_patient_ids_with_training_on_date.assert_called_once_with(
            "2022-05-22",
            None,
        )

    def test_get_patient_ids_with_training_on_date_delegates_limit_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_ids_with_training_on_date.return_value = ["40"]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_ids_with_training_on_date(
            "2022-05-22",
            limit=100,
        )

        self.assertEqual(result, ["40"])
        mock_repository.get_patient_ids_with_training_on_date.assert_called_once_with(
            "2022-05-22",
            100,
        )

    def test_get_source_patient_ids_with_secondary_ability_scores_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_source_patient_ids_with_secondary_ability_scores.return_value = [
            "40",
            "41",
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_source_patient_ids_with_secondary_ability_scores()

        self.assertEqual(result, ["40", "41"])
        mock_repository.get_source_patient_ids_with_secondary_ability_scores.assert_called_once_with()

    def test_get_distinct_training_games_delegates_to_repository(self) -> None:
        mock_repository = Mock()
        mock_repository.get_distinct_training_games.return_value = [
            {"g": {"id": "42", "name": "打怪物"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_distinct_training_games()

        self.assertEqual(result, [{"g": {"id": "42", "name": "打怪物"}}])
        mock_repository.get_distinct_training_games.assert_called_once_with()

    def test_get_patient_profile_gender_education_age_exclusive_task_games_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_profile_gender_education_age_exclusive_task_games.return_value = [
            {"g": {"id": "42"}, "support_count": 5}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_profile_gender_education_age_exclusive_task_games(
            "20104662",
            "2024-01-31",
            5,
        )

        self.assertEqual(result, [{"g": {"id": "42"}, "support_count": 5}])
        mock_repository.get_patient_profile_gender_education_age_exclusive_task_games.assert_called_once_with(
            "20104662",
            "2024-01-31",
            5,
        )

    def test_get_patient_profile_candidate_training_games_uses_profile_filters(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_profile_gender_education_age_exclusive_task_games.return_value = [
            {
                "g": {"id": "1", "name": "画像任务"},
                "profile_age": 68,
                "profile_gender": "男",
                "profile_education": "本科",
                "support_sources": ["AU_DIS_0013"],
                "support_count": 1,
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_profile_candidate_training_games(
            "30010096",
            "2022-01-13",
        )

        self.assertEqual(
            result,
            [
                {
                    "g": {"id": "1", "name": "画像任务"},
                    "profile_age": 68,
                    "profile_gender": "男",
                    "profile_education": "本科",
                    "support_sources": ["AU_DIS_0013"],
                    "support_count": 1,
                }
            ],
        )
        mock_repository.get_patient_profile_gender_education_age_exclusive_task_games.assert_called_once_with(
            "30010096",
            "2022-01-13",
            0,
        )

    def test_get_patient_profile_candidate_training_games_can_use_windowed_profile_filters(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_profile_gender_education_age_windowed_exclusive_task_games.return_value = [
            {"g": {"id": "1", "name": "画像任务"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_profile_candidate_training_games(
            "30010096",
            "2022-01-13",
            profile_candidate_training_window_days=0,
        )

        self.assertEqual(result, [{"g": {"id": "1", "name": "画像任务"}}])
        mock_repository.get_patient_profile_gender_education_age_windowed_exclusive_task_games.assert_called_once_with(
            "30010096",
            "2022-01-13",
            0,
            0,
        )
        mock_repository.get_patient_profile_gender_education_age_exclusive_task_games.assert_not_called()

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

    def test_get_patient_distinct_games_by_start_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_games_by_start_date.return_value = [
            {"g": {"id": "42", "name": "打怪物"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_games_by_start_date(
            "30010096",
            "2022-01-13",
        )

        self.assertEqual(result, [{"g": {"id": "42", "name": "打怪物"}}])
        mock_repository.get_patient_distinct_games_by_start_date.assert_called_once_with(
            "30010096",
            "2022-01-13",
        )

    def test_get_patient_distinct_games_by_date_range_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_distinct_games_by_date_range.return_value = [
            {"g": {"id": "42", "name": "打怪物"}}
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_distinct_games_by_date_range(
            "30010096",
            "2022-01-13",
            "2022-05-22",
        )

        self.assertEqual(result, [{"g": {"id": "42", "name": "打怪物"}}])
        mock_repository.get_patient_distinct_games_by_date_range.assert_called_once_with(
            "30010096",
            "2022-01-13",
            "2022-05-22",
        )

    def test_get_patient_games_by_end_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_games_by_end_date.return_value = [
            {"g": {"id": "42", "name": "打怪物"}},
            {"g": {"id": "42", "name": "打怪物"}},
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_games_by_end_date(
            "30010096",
            "2022-01-13",
        )

        self.assertEqual(
            result,
            [
                {"g": {"id": "42", "name": "打怪物"}},
                {"g": {"id": "42", "name": "打怪物"}},
            ],
        )
        mock_repository.get_patient_games_by_end_date.assert_called_once_with(
            "30010096",
            "2022-01-13",
        )

    def test_get_patient_games_by_start_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_games_by_start_date.return_value = [
            {"g": {"id": "42", "name": "打怪物"}},
            {"g": {"id": "42", "name": "打怪物"}},
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_games_by_start_date(
            "30010096",
            "2022-01-13",
        )

        self.assertEqual(
            result,
            [
                {"g": {"id": "42", "name": "打怪物"}},
                {"g": {"id": "42", "name": "打怪物"}},
            ],
        )
        mock_repository.get_patient_games_by_start_date.assert_called_once_with(
            "30010096",
            "2022-01-13",
        )

    def test_get_patient_games_by_date_range_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_games_by_date_range.return_value = [
            {"g": {"id": "42", "name": "打怪物"}},
            {"g": {"id": "42", "name": "打怪物"}},
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_games_by_date_range(
            "30010096",
            "2022-01-13",
            "2022-05-22",
        )

        self.assertEqual(
            result,
            [
                {"g": {"id": "42", "name": "打怪物"}},
                {"g": {"id": "42", "name": "打怪物"}},
            ],
        )
        mock_repository.get_patient_games_by_date_range.assert_called_once_with(
            "30010096",
            "2022-01-13",
            "2022-05-22",
        )

    def test_get_patient_game_set_comparison_by_end_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_game_set_comparison_by_end_date.return_value = [
            {
                "games1": [{"id": "42", "name": "打怪物"}],
                "games2": [{"id": "84", "name": "真假句辨别"}],
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_game_set_comparison_by_end_date(
            "40",
            "20121011",
            "2022-05-22",
        )

        self.assertEqual(
            result,
            [
                {
                    "games1": [{"id": "42", "name": "打怪物"}],
                    "games2": [{"id": "84", "name": "真假句辨别"}],
                }
            ],
        )
        mock_repository.get_patient_game_set_comparison_by_end_date.assert_called_once_with(
            "40",
            "20121011",
            "2022-05-22",
        )

    def test_get_patient_game_set_comparison_by_start_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_game_set_comparison_by_start_date.return_value = [
            {
                "games1": [{"id": "42", "name": "打怪物"}],
                "games2": [{"id": "84", "name": "真假句辨别"}],
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_game_set_comparison_by_start_date(
            "40",
            "20121011",
            "2022-05-01",
        )

        self.assertEqual(
            result,
            [
                {
                    "games1": [{"id": "42", "name": "打怪物"}],
                    "games2": [{"id": "84", "name": "真假句辨别"}],
                }
            ],
        )
        mock_repository.get_patient_game_set_comparison_by_start_date.assert_called_once_with(
            "40",
            "20121011",
            "2022-05-01",
        )

    def test_get_patient_game_set_comparison_by_date_range_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_game_set_comparison_by_date_range.return_value = [
            {
                "games1": [{"id": "42", "name": "打怪物"}],
                "games2": [{"id": "84", "name": "真假句辨别"}],
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_game_set_comparison_by_date_range(
            "40",
            "20121011",
            "2022-05-01",
            "2022-05-22",
        )

        self.assertEqual(
            result,
            [
                {
                    "games1": [{"id": "42", "name": "打怪物"}],
                    "games2": [{"id": "84", "name": "真假句辨别"}],
                }
            ],
        )
        mock_repository.get_patient_game_set_comparison_by_date_range.assert_called_once_with(
            "40",
            "20121011",
            "2022-05-01",
            "2022-05-22",
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

    def test_get_patient_secondary_ability_scores_by_disease_course_window_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_secondary_ability_scores_by_disease_course_window.return_value = [
            {
                "effective_ability_date": "2023-10-10",
                "instance_set_id": "40_20231010",
                "training_date": "2023-10-10",
                "secondary_ability_scores": {"二级_书写能力": 20.0},
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_secondary_ability_scores_by_disease_course_window(
            "40",
            "2023-10-15",
            365,
        )

        self.assertEqual(
            result,
            [
                {
                    "effective_ability_date": "2023-10-10",
                    "instance_set_id": "40_20231010",
                    "training_date": "2023-10-10",
                    "secondary_ability_scores": {"二级_书写能力": 20.0},
                }
            ],
        )
        mock_repository.get_patient_secondary_ability_scores_by_disease_course_window.assert_called_once_with(
            "40",
            "2023-10-15",
            365,
        )

    def test_get_patient_total_scores_by_disease_course_window_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_total_scores_by_disease_course_window.return_value = [
            {
                "effective_total_score_date": "2023-10-10",
                "instance_set_id": "40_20231009",
                "training_date": "2023-10-09",
                "total_score": 88.5,
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_total_scores_by_disease_course_window(
            "40",
            "2023-10-15",
            365,
        )

        self.assertEqual(
            result,
            [
                {
                    "effective_total_score_date": "2023-10-10",
                    "instance_set_id": "40_20231009",
                    "training_date": "2023-10-09",
                    "total_score": 88.5,
                }
            ],
        )
        mock_repository.get_patient_total_scores_by_disease_course_window.assert_called_once_with(
            "40",
            "2023-10-15",
            365,
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

    def test_get_patient_symptom_set_comparison_queries_delegate_to_repository(
        self,
    ) -> None:
        cases = [
            (
                "get_patient_symptom_set_comparison_by_end_date",
                ("40", "20121011", "2022-05-22"),
            ),
            (
                "get_patient_symptom_set_comparison_by_start_date",
                ("40", "20121011", "2022-05-01"),
            ),
            (
                "get_patient_symptom_set_comparison_by_date_range",
                ("40", "20121011", "2022-05-01", "2022-05-22"),
            ),
        ]

        for method_name, args in cases:
            with self.subTest(method_name=method_name):
                mock_repository = Mock()
                getattr(mock_repository, method_name).return_value = [
                    {
                        "symptoms1": [{"id": "AU_SYM_0007", "name": "睡眠障碍"}],
                        "symptoms2": [{"id": "AU_SYM_0012", "name": "注意力不集中"}],
                    }
                ]
                service = UserService(kg_repository=mock_repository)

                result = getattr(service, method_name)(*args)

                self.assertEqual(
                    result,
                    [
                        {
                            "symptoms1": [{"id": "AU_SYM_0007", "name": "睡眠障碍"}],
                            "symptoms2": [
                                {"id": "AU_SYM_0012", "name": "注意力不集中"}
                            ],
                        }
                    ],
                )
                getattr(mock_repository, method_name).assert_called_once_with(*args)

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

    def test_get_patient_disease_set_comparison_by_end_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_disease_set_comparison_by_end_date.return_value = [
            {
                "diseases1": [{"id": "AU_DIS_0001", "name": "阿尔茨海默病"}],
                "diseases2": [{"id": "AU_DIS_0002", "name": "轻度认知障碍"}],
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_disease_set_comparison_by_end_date(
            "40",
            "20121011",
            "2022-05-22",
        )

        self.assertEqual(
            result,
            [
                {
                    "diseases1": [{"id": "AU_DIS_0001", "name": "阿尔茨海默病"}],
                    "diseases2": [{"id": "AU_DIS_0002", "name": "轻度认知障碍"}],
                }
            ],
        )
        mock_repository.get_patient_disease_set_comparison_by_end_date.assert_called_once_with(
            "40",
            "20121011",
            "2022-05-22",
        )

    def test_get_patient_disease_set_comparison_by_start_date_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_disease_set_comparison_by_start_date.return_value = [
            {
                "diseases1": [{"id": "AU_DIS_0001", "name": "阿尔茨海默病"}],
                "diseases2": [{"id": "AU_DIS_0002", "name": "轻度认知障碍"}],
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_disease_set_comparison_by_start_date(
            "40",
            "20121011",
            "2022-05-01",
        )

        self.assertEqual(
            result,
            [
                {
                    "diseases1": [{"id": "AU_DIS_0001", "name": "阿尔茨海默病"}],
                    "diseases2": [{"id": "AU_DIS_0002", "name": "轻度认知障碍"}],
                }
            ],
        )
        mock_repository.get_patient_disease_set_comparison_by_start_date.assert_called_once_with(
            "40",
            "20121011",
            "2022-05-01",
        )

    def test_get_patient_disease_set_comparison_by_date_range_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_disease_set_comparison_by_date_range.return_value = [
            {
                "diseases1": [{"id": "AU_DIS_0001", "name": "阿尔茨海默病"}],
                "diseases2": [{"id": "AU_DIS_0002", "name": "轻度认知障碍"}],
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_disease_set_comparison_by_date_range(
            "40",
            "20121011",
            "2022-05-01",
            "2022-05-22",
        )

        self.assertEqual(
            result,
            [
                {
                    "diseases1": [{"id": "AU_DIS_0001", "name": "阿尔茨海默病"}],
                    "diseases2": [{"id": "AU_DIS_0002", "name": "轻度认知障碍"}],
                }
            ],
        )
        mock_repository.get_patient_disease_set_comparison_by_date_range.assert_called_once_with(
            "40",
            "20121011",
            "2022-05-01",
            "2022-05-22",
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

    def test_get_patient_unknown_set_comparison_queries_delegate_to_repository(
        self,
    ) -> None:
        cases = [
            (
                "get_patient_unknown_set_comparison_by_end_date",
                ("40", "20121011", "2022-05-22"),
            ),
            (
                "get_patient_unknown_set_comparison_by_start_date",
                ("40", "20121011", "2022-05-01"),
            ),
            (
                "get_patient_unknown_set_comparison_by_date_range",
                ("40", "20121011", "2022-05-01", "2022-05-22"),
            ),
        ]

        for method_name, args in cases:
            with self.subTest(method_name=method_name):
                mock_repository = Mock()
                getattr(mock_repository, method_name).return_value = [
                    {
                        "unknowns1": [{"id": "AU_UNK_0001", "name": "其他异常表现"}],
                        "unknowns2": [{"id": "AU_UNK_0002", "name": "待分类表现"}],
                    }
                ]
                service = UserService(kg_repository=mock_repository)

                result = getattr(service, method_name)(*args)

                self.assertEqual(
                    result,
                    [
                        {
                            "unknowns1": [
                                {"id": "AU_UNK_0001", "name": "其他异常表现"}
                            ],
                            "unknowns2": [
                                {"id": "AU_UNK_0002", "name": "待分类表现"}
                            ],
                        }
                    ],
                )
                getattr(mock_repository, method_name).assert_called_once_with(*args)

    def test_get_pattern_paths_returns_statistics_only_when_no_paths(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_repository.get_pattern_statistics.return_value = [
            {"totalPaths": 0, "gCount": 0, "p2Count": 0}
        ]
        mock_repository.recommend_graph_path_limit.return_value.per_g = 4
        mock_repository.recommend_graph_path_limit.return_value.limit = 10
        mock_repository.get_pattern_randomized_paths.return_value = []
        service = UserService(kg_repository=mock_repository)

        result = service.get_pattern_paths(
            "30010096",
            base_date="2022-01-17",
            window_days=14,
            pattern="patient_game_patient",
        )

        path_window = {
            "base_date": "2022-01-17",
            "start_date": "2022-01-03",
            "end_date": "2022-01-17",
            "window_days": 14,
            "range_semantics": "[start_date, end_date)",
        }
        self.assertEqual(result["ordered_training_dates"], [])
        self.assertEqual(result["source_id"], "30010096")
        self.assertEqual(result["source_parameter"], "patient_id")
        self.assertEqual(result["patient_id"], "30010096")
        self.assertEqual(
            result["retrieval_context"],
            {
                "base_date": "2022-01-17",
                "query_family": "training_order_source_window",
                "path_window": path_window,
                "window_statistics": {"totalPaths": 0, "gCount": 0, "p2Count": 0},
                "limit_recommendation": None,
                "paths": [],
            },
        )
        self.assertEqual(
            result["pattern"],
            PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        )
        mock_repository.recommend_graph_path_limit.assert_not_called()
        mock_repository.get_pattern_randomized_paths.assert_not_called()
        mock_repository.get_pattern_statistics.assert_called_once_with(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            query_family=PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW,
            patient_id="30010096",
            start_date="2022-01-03",
            end_date="2022-01-17",
        )

    def test_get_pattern_paths_returns_paths_with_recommendation(self) -> None:
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_repository.get_pattern_statistics.return_value = [
            {"totalPaths": 20, "gCount": 5, "p2Count": 6}
        ]
        mock_repository.recommend_graph_path_limit.return_value.per_g = 5
        mock_repository.recommend_graph_path_limit.return_value.limit = 10
        mock_repository.get_pattern_randomized_paths.return_value = [
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

        result = service.get_pattern_paths(
            "30010096",
            base_date="2022-01-17",
            window_days=14,
        )

        self.assertEqual(result["first_training_date"], None)
        self.assertEqual(result["last_training_date"], None)
        self.assertEqual(result["training_date_count"], 0)
        self.assertEqual(result["source_id"], "30010096")
        self.assertEqual(result["source_parameter"], "patient_id")
        self.assertEqual(result["patient_id"], "30010096")
        self.assertEqual(
            result["pattern"],
            PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        )
        path_window = {
            "base_date": "2022-01-17",
            "start_date": "2022-01-03",
            "end_date": "2022-01-17",
            "window_days": 14,
            "range_semantics": "[start_date, end_date)",
        }
        self.assertEqual(
            result["retrieval_context"],
            {
                "base_date": "2022-01-17",
                "query_family": "training_order_source_window",
                "path_window": path_window,
                "window_statistics": {"totalPaths": 20, "gCount": 5, "p2Count": 6},
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
        mock_repository.get_pattern_randomized_paths.assert_called_once_with(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            query_family=PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW,
            patient_id="30010096",
            start_date="2022-01-03",
            end_date="2022-01-17",
            per_group=5,
            limit=10,
        )

    def test_get_pattern_paths_uses_pattern_specific_group_count(self) -> None:
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_repository.get_pattern_statistics.return_value = [
            {"totalPaths": 20, "disCount": 4, "p2Count": 6}
        ]
        mock_repository.recommend_graph_path_limit.return_value.per_g = 5
        mock_repository.recommend_graph_path_limit.return_value.limit = 10
        mock_repository.get_pattern_randomized_paths.return_value = []
        service = UserService(kg_repository=mock_repository)

        result = service.get_pattern_paths(
            "30010096",
            base_date="2022-01-17",
            window_days=14,
            pattern="patient_disease_patient",
            query_family=PatternQueryFamily.DATE_WINDOW,
        )

        self.assertEqual(result["pattern"], PATIENT_TASKSET_DISEASE_TASKSET_PATIENT)
        mock_repository.recommend_graph_path_limit.assert_called_once_with(
            total_paths=20,
            g_count=4,
            p2_count=6,
        )
        mock_repository.get_pattern_randomized_paths.assert_called_once_with(
            pattern=PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT,
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id="30010096",
            start_date="2022-01-03",
            end_date="2022-01-17",
            per_group=5,
            limit=10,
        )

    def test_get_pattern_paths_loads_direct_disease_patient_paths(self) -> None:
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_repository.get_disease_taskset_patient_randomized_paths.return_value = [
            {
                "row": {
                    "d": {"id": "AU_DIS_0013"},
                    "s": {"id": "40_20220516"},
                    "p": {"id": "40"},
                }
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_pattern_paths(
            "AU_DIS_0013",
            base_date="2022-01-17",
            window_days=14,
            pattern="disease_patient",
        )

        path_window = {
            "base_date": "2022-01-17",
            "start_date": "2022-01-03",
            "end_date": "2022-01-17",
            "window_days": 14,
            "range_semantics": "[start_date, end_date)",
        }
        self.assertEqual(result["source_id"], "AU_DIS_0013")
        self.assertEqual(result["source_parameter"], "disease_id")
        self.assertEqual(result["disease_id"], "AU_DIS_0013")
        self.assertNotIn("patient_id", result)
        self.assertEqual(result["pattern"], DISEASE_TASKSET_PATIENT)
        self.assertEqual(
            result["retrieval_context"],
            {
                "base_date": "2022-01-17",
                "query_family": None,
                "path_window": path_window,
                "window_statistics": None,
                "limit_recommendation": None,
                "paths": [
                    {
                        "row": {
                            "d": {"id": "AU_DIS_0013"},
                            "s": {"id": "40_20220516"},
                            "p": {"id": "40"},
                        }
                    }
                ],
            },
        )
        mock_repository.get_disease_taskset_patient_randomized_paths.assert_called_once_with(
            "AU_DIS_0013",
            start_date="2022-01-03",
            end_date="2022-01-17",
        )
        mock_repository.get_pattern_statistics.assert_not_called()
        mock_repository.recommend_graph_path_limit.assert_not_called()
        mock_repository.get_pattern_randomized_paths.assert_not_called()

    def test_get_pattern_paths_loads_direct_symptom_patient_paths(self) -> None:
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_repository.get_symptom_taskset_patient_randomized_paths.return_value = [
            {
                "row": {
                    "sym": {"id": "AU_SYM_0007"},
                    "s": {"id": "40_20220516"},
                    "p": {"id": "40"},
                }
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_pattern_paths(
            "AU_SYM_0007",
            base_date="2022-01-17",
            window_days=14,
            pattern="symptom_patient",
        )

        self.assertEqual(result["source_id"], "AU_SYM_0007")
        self.assertEqual(result["source_parameter"], "symptom_id")
        self.assertEqual(result["symptom_id"], "AU_SYM_0007")
        self.assertNotIn("patient_id", result)
        self.assertEqual(result["pattern"], SYMPTOM_TASKSET_PATIENT)
        self.assertEqual(
            result["retrieval_context"]["paths"],
            [
                {
                    "row": {
                        "sym": {"id": "AU_SYM_0007"},
                        "s": {"id": "40_20220516"},
                        "p": {"id": "40"},
                    }
                }
            ],
        )
        mock_repository.get_symptom_taskset_patient_randomized_paths.assert_called_once_with(
            "AU_SYM_0007",
            start_date="2022-01-03",
            end_date="2022-01-17",
        )
        mock_repository.get_pattern_statistics.assert_not_called()
        mock_repository.recommend_graph_path_limit.assert_not_called()
        mock_repository.get_pattern_randomized_paths.assert_not_called()

    def test_get_pattern_paths_loads_direct_unknown_patient_paths(self) -> None:
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_repository.get_unknown_taskset_patient_randomized_paths.return_value = [
            {
                "row": {
                    "un": {"id": "AU_UNKOWN_0005"},
                    "s": {"id": "40_20220516"},
                    "p": {"id": "40"},
                }
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_pattern_paths(
            "AU_UNKOWN_0005",
            base_date="2022-01-17",
            window_days=14,
            pattern="unknown_patient",
        )

        self.assertEqual(result["source_id"], "AU_UNKOWN_0005")
        self.assertEqual(result["source_parameter"], "unknown_id")
        self.assertEqual(result["unknown_id"], "AU_UNKOWN_0005")
        self.assertNotIn("patient_id", result)
        self.assertEqual(result["pattern"], UNKNOWN_TASKSET_PATIENT)
        self.assertEqual(
            result["retrieval_context"]["paths"],
            [
                {
                    "row": {
                        "un": {"id": "AU_UNKOWN_0005"},
                        "s": {"id": "40_20220516"},
                        "p": {"id": "40"},
                    }
                }
            ],
        )
        mock_repository.get_unknown_taskset_patient_randomized_paths.assert_called_once_with(
            "AU_UNKOWN_0005",
            start_date="2022-01-03",
            end_date="2022-01-17",
        )
        mock_repository.get_pattern_statistics.assert_not_called()
        mock_repository.recommend_graph_path_limit.assert_not_called()
        mock_repository.get_pattern_randomized_paths.assert_not_called()

    def test_get_pattern_paths_rejects_query_family_for_direct_pattern(self) -> None:
        service = UserService(kg_repository=Mock())

        with self.assertRaisesRegex(ValueError, "does not support query_family"):
            service.get_pattern_paths(
                "AU_DIS_0013",
                base_date="2022-01-17",
                window_days=14,
                pattern="disease_patient",
                query_family=PatternQueryFamily.DATE_WINDOW,
            )

    def test_get_pattern_paths_rejects_invalid_window(
        self,
    ) -> None:
        service = UserService(kg_repository=Mock())

        with self.assertRaises(ValueError):
            service.get_pattern_paths(
                "30010096",
                base_date="2022-01-17",
                window_days=0,
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

    def test_get_patient_total_score_timepoints_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_total_score_timepoints.return_value = [
            {
                "instance_set_id": "30010096_20220522",
                "training_date": "2022-05-22",
                "total_score": 91.5,
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_total_score_timepoints("30010096")

        self.assertEqual(
            result,
            [
                {
                    "instance_set_id": "30010096_20220522",
                    "training_date": "2022-05-22",
                    "total_score": 91.5,
                }
            ],
        )
        mock_repository.get_patient_total_score_timepoints.assert_called_once_with(
            "30010096"
        )

    def test_get_patient_total_score_by_date_returns_normalized_score(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_total_score_by_date.return_value = [
            {
                "instance_set_id": "30010096_20220522",
                "training_date": "2022-05-22",
                "total_score": "90.0",
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_total_score_by_date(
            "30010096",
            "2022-05-22",
        )

        self.assertEqual(
            result,
            {
                "instance_set_id": "30010096_20220522",
                "training_date": "2022-05-22",
                "total_score": 90.0,
            },
        )
        mock_repository.get_patient_total_score_by_date.assert_called_once_with(
            "30010096",
            "2022-05-22",
        )

    def test_get_patient_total_score_by_date_returns_none_without_score(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_total_score_by_date.return_value = []
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_total_score_by_date(
            "30010096",
            "2022-05-22",
        )

        self.assertIsNone(result)

    def test_find_patient_total_score_timepoint_matches_returns_nearest_scores(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_total_scores_by_disease_course_window.return_value = [
            {
                "effective_total_score_date": "2022-05-22",
                "instance_set_id": "30010096_20220501",
                "training_date": "2022-05-01",
                "total_score": "88.0",
            },
            {
                "effective_total_score_date": "2022-05-22",
                "instance_set_id": "30010096_20220520",
                "training_date": "2022-05-20",
                "total_score": "92.0",
            }
        ]
        mock_repository.get_patient_total_score_timepoints.side_effect = [
            [
                {
                    "instance_set_id": "20113562_20220501",
                    "training_date": "2022-05-01",
                    "total_score": 88.0,
                },
                {
                    "instance_set_id": "20113562_20220520",
                    "training_date": "2022-05-20",
                    "total_score": "91.0",
                },
            ],
            [
                {
                    "instance_set_id": "20113563_20220510",
                    "training_date": "2022-05-10",
                    "total_score": 89.5,
                }
            ],
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.find_patient_total_score_timepoint_matches(
            "30010096",
            "2022-05-22",
            ["20113562", "20113563"],
        )

        self.assertEqual(
            result,
            [
                {
                    "source": {
                        "patient_id": "30010096",
                        "instance_set_id": None,
                        "training_date": "2022-05-22",
                        "total_score": 90.0,
                        "total_score_aggregation": "mean",
                        "total_score_record_count": 2,
                        "effective_total_score_date": "2022-05-22",
                    },
                    "matched": {
                        "patient_id": "20113562",
                        "instance_set_id": "20113562_20220520",
                        "training_date": "2022-05-20",
                        "total_score": 91.0,
                        "recommended_date": "2022-11-18",
                    },
                    "score_delta": 1.0,
                },
                {
                    "source": {
                        "patient_id": "30010096",
                        "instance_set_id": None,
                        "training_date": "2022-05-22",
                        "total_score": 90.0,
                        "total_score_aggregation": "mean",
                        "total_score_record_count": 2,
                        "effective_total_score_date": "2022-05-22",
                    },
                    "matched": {
                        "patient_id": "20113563",
                        "instance_set_id": "20113563_20220510",
                        "training_date": "2022-05-10",
                        "total_score": 89.5,
                        "recommended_date": "2022-11-08",
                    },
                    "score_delta": 0.5,
                },
            ],
        )
        mock_repository.get_patient_total_scores_by_disease_course_window.assert_called_once_with(
            "30010096",
            "2022-05-22",
            365,
        )
        self.assertEqual(
            mock_repository.get_patient_total_score_timepoints.call_args_list,
            [call("20113562"), call("20113563")],
        )

    def test_find_patient_total_score_timepoint_matches_returns_one_match_by_default(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_total_scores_by_disease_course_window.return_value = [
            {
                "instance_set_id": "source_s",
                "training_date": "2022-05-22",
                "total_score": 90.0,
            }
        ]
        mock_repository.get_patient_total_score_timepoints.return_value = [
            {
                "instance_set_id": "target_s",
                "training_date": "2022-05-21",
                "total_score": 91.0,
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.find_patient_total_score_timepoint_matches(
            "source",
            "2022-05-22",
            ["target"],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["matched"]["instance_set_id"], "target_s")

    def test_find_patient_total_score_timepoint_matches_applies_configured_top_k(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "query:",
                        "  graph_path_limit:",
                        "    bands:",
                        "      - per_g: 4",
                        "  candidate_ranking:",
                        "    total_score_match_top_k: 2",
                        "    disease_course_window_days: 365",
                    ]
                ),
                encoding="utf-8",
            )
            mock_repository = Mock()
            mock_repository.config_path = config_path
            mock_repository.get_patient_total_scores_by_disease_course_window.return_value = [
                {
                    "instance_set_id": "source_s",
                    "training_date": "2022-05-22",
                    "total_score": 90.0,
                }
            ]
            mock_repository.get_patient_total_score_timepoints.return_value = [
                {
                    "instance_set_id": "target_first",
                    "training_date": "2022-05-21",
                    "total_score": 90.5,
                },
                {
                    "instance_set_id": "target_second",
                    "training_date": "2022-05-23",
                    "total_score": 89.0,
                },
                {
                    "instance_set_id": "target_third",
                    "training_date": "2022-05-24",
                    "total_score": 92.0,
                },
            ]
            service = UserService(kg_repository=mock_repository)

            result = service.find_patient_total_score_timepoint_matches(
                "source",
                "2022-05-22",
                ["target"],
            )

        self.assertEqual(
            [match["matched"]["instance_set_id"] for match in result],
            ["target_first", "target_second"],
        )

    def test_find_patient_total_score_timepoint_matches_uses_date_tie_break(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_total_scores_by_disease_course_window.return_value = [
            {
                "instance_set_id": "source_s",
                "training_date": "2022-05-22",
                "total_score": 90.0,
            }
        ]
        mock_repository.get_patient_total_score_timepoints.return_value = [
            {
                "instance_set_id": "target_far",
                "training_date": "2022-01-01",
                "total_score": 91.0,
            },
            {
                "instance_set_id": "target_near",
                "training_date": "2022-05-21",
                "total_score": 89.0,
            },
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.find_patient_total_score_timepoint_matches(
            "source",
            "2022-05-22",
            ["target"],
        )

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["matched"]["instance_set_id"], "target_near")

    def test_find_patient_total_score_timepoint_matches_applies_tolerance(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_total_scores_by_disease_course_window.return_value = [
            {
                "instance_set_id": "source_s",
                "training_date": "2022-05-22",
                "total_score": 90.0,
            }
        ]
        mock_repository.get_patient_total_score_timepoints.return_value = [
            {
                "instance_set_id": "target_s",
                "training_date": "2022-05-21",
                "total_score": 92.0,
            },
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.find_patient_total_score_timepoint_matches(
            "source",
            "2022-05-22",
            ["target"],
            tolerance=1.5,
        )

        self.assertEqual(result, [])

    def test_find_patient_total_score_timepoint_matches_returns_empty_without_source(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_total_scores_by_disease_course_window.return_value = []
        service = UserService(kg_repository=mock_repository)

        result = service.find_patient_total_score_timepoint_matches(
            "source",
            "2022-05-22",
            ["target"],
        )

        self.assertEqual(result, [])
        mock_repository.get_patient_total_scores_by_disease_course_window.assert_called_once_with(
            "source",
            "2022-05-22",
            365,
        )
        mock_repository.get_patient_total_score_timepoints.assert_not_called()

    def test_find_patient_total_score_timepoint_matches_rejects_invalid_tolerance(
        self,
    ) -> None:
        service = UserService(kg_repository=Mock())

        with self.assertRaisesRegex(ValueError, "tolerance must be a non-negative number."):
            service.find_patient_total_score_timepoint_matches(
                "source",
                "2022-05-22",
                ["target"],
                tolerance=-1,
            )

    def test_get_patient_training_task_history_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_training_task_history.return_value = [
            {
                "trainingDate": "2022-01-13",
                "i": {"id": "i-1", "任务类型": "专属"},
                "g": {"id": "42", "name": "打怪物"},
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_training_task_history("30010096")

        self.assertEqual(
            result,
            [
                {
                    "trainingDate": "2022-01-13",
                    "i": {"id": "i-1", "任务类型": "专属"},
                    "g": {"id": "42", "name": "打怪物"},
                }
            ],
        )
        mock_repository.get_patient_training_task_history.assert_called_once_with(
            "30010096"
        )

    def test_get_patient_training_task_history_by_date_window_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_training_task_history_by_date_window.return_value = [
            {
                "trainingDate": "2022-05-21",
                "g": {"id": "42", "name": "打怪物"},
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_training_task_history_by_date_window(
            "30010096",
            "2022-05-20",
            "2022-05-22",
        )

        self.assertEqual(
            result,
            [
                {
                    "trainingDate": "2022-05-21",
                    "g": {"id": "42", "name": "打怪物"},
                }
            ],
        )
        mock_repository.get_patient_training_task_history_by_date_window.assert_called_once_with(
            "30010096",
            "2022-05-20",
            "2022-05-22",
        )

    def test_get_patient_exclusive_training_task_history_by_date_window_delegates_to_repository(
        self,
    ) -> None:
        mock_repository = Mock()
        mock_repository.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {
                "trainingDate": "2022-05-21",
                "g": {"id": "42", "name": "打怪物"},
            }
        ]
        service = UserService(kg_repository=mock_repository)

        result = service.get_patient_exclusive_training_task_history_by_date_window(
            "30010096",
            "2022-05-20",
            "2022-05-22",
        )

        self.assertEqual(
            result,
            [
                {
                    "trainingDate": "2022-05-21",
                    "g": {"id": "42", "name": "打怪物"},
                }
            ],
        )
        mock_repository.get_patient_exclusive_training_task_history_by_date_window.assert_called_once_with(
            "30010096",
            "2022-05-20",
            "2022-05-22",
        )


if __name__ == "__main__":
    unittest.main()
