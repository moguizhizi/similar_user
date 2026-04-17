"""Tests for KG repository query orchestration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from config.settings import QueryLimitBandSettings, load_query_settings
from src.similar_user.data_access.cypher_queries import (
    PATIENT_DISEASE_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_DISEASE_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_START_DATE_QUERY,
    PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY,
    PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_END_DATE_RANDOMIZED_PATH_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_RANDOMIZED_PATH_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY,
)
from src.similar_user.data_access.kg_repository import (
    GraphPathLimitRecommendation,
    KgRepository,
)


class KgRepositoryTest(unittest.TestCase):
    def test_get_patient_training_date_games_by_start_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "trainingDate": "2022-01-13",
                "games": [{"id": "42"}, {"id": "84"}],
            }
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_training_date_games_by_start_date(
            " 30010096 ",
            " 2022-01-01 ",
        )

        self.assertEqual(
            result,
            [{"trainingDate": "2022-01-13", "games": [{"id": "42"}, {"id": "84"}]}],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
            },
        )

    def test_get_patient_training_date_games_by_start_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_training_date_games_by_start_date(
                "   ",
                "2022-01-01",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_training_date_games_by_start_date(
                "30010096",
                "   ",
            )

    def test_get_patient_distinct_games_by_end_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"g": {"id": "42", "name": "打怪物"}},
            {"g": {"id": "84", "name": "真假句辨别"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_games_by_end_date(
            " 30010096 ",
            " 2022-01-13 ",
        )

        self.assertEqual(
            result,
            [
                {"g": {"id": "42", "name": "打怪物"}},
                {"g": {"id": "84", "name": "真假句辨别"}},
            ],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_distinct_games_by_end_date_rejects_blank_inputs(self) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_games_by_end_date(
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_distinct_games_by_end_date(
                "30010096",
                "   ",
            )

    def test_get_patient_game_norm_score_series_comparison_by_end_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "game": "打怪物",
                "scores_p1": ["91", "95"],
                "scores_p2": ["88", "93"],
            }
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_game_norm_score_series_comparison_by_end_date(
            " 40 ",
            " 30000035 ",
            " 2026-02-12 ",
        )

        self.assertEqual(
            result,
            [{"game": "打怪物", "scores_p1": ["91", "95"], "scores_p2": ["88", "93"]}],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY,
            parameters={
                "primary_patient_id": "40",
                "comparison_patient_id": "30000035",
                "end_date": "2026-02-12",
            },
        )

    def test_get_patient_game_norm_score_series_comparison_by_end_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(
            ValueError,
            "primary_patient_id must be a non-empty string.",
        ):
            repository.get_patient_game_norm_score_series_comparison_by_end_date(
                "   ",
                "30000035",
                "2026-02-12",
            )

        with self.assertRaisesRegex(
            ValueError,
            "comparison_patient_id must be a non-empty string.",
        ):
            repository.get_patient_game_norm_score_series_comparison_by_end_date(
                "40",
                "   ",
                "2026-02-12",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_game_norm_score_series_comparison_by_end_date(
                "40",
                "30000035",
                "   ",
            )

    def test_get_patient_distinct_task_instances_by_start_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_task_instances_by_start_date(
            " 30010096 ",
            " 2022-01-01 ",
        )

        self.assertEqual(
            result,
            [{"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}}],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
            },
        )

    def test_get_patient_distinct_task_instances_by_start_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_task_instances_by_start_date(
                "   ",
                "2022-01-01",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_distinct_task_instances_by_start_date(
                "30010096",
                "   ",
            )

    def test_get_patient_distinct_task_instances_by_end_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_task_instances_by_end_date(
            " 30010096 ",
            " 2022-01-13 ",
        )

        self.assertEqual(
            result,
            [{"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}}],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_distinct_task_instances_by_end_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_task_instances_by_end_date(
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_distinct_task_instances_by_end_date(
                "30010096",
                "   ",
            )

    def test_get_patient_distinct_task_instances_by_date_range(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_task_instances_by_date_range(
            " 30010096 ",
            " 2022-01-01 ",
            " 2022-01-13 ",
        )

        self.assertEqual(
            result,
            [{"i1": {"id": "40_20220516_42_464CAOTKJK2BX3", "状态": "完成"}}],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_distinct_task_instances_by_date_range_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_task_instances_by_date_range(
                "   ",
                "2022-01-01",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_distinct_task_instances_by_date_range(
                "30010096",
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_distinct_task_instances_by_date_range(
                "30010096",
                "2022-01-01",
                "   ",
            )

    def test_get_patient_distinct_symptoms_by_end_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}},
            {"sym": {"id": "AU_SYM_0012", "name": "注意力不集中"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_symptoms_by_end_date(
            " 30010096 ",
            " 2022-01-13 ",
        )

        self.assertEqual(
            result,
            [
                {"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}},
                {"sym": {"id": "AU_SYM_0012", "name": "注意力不集中"}},
            ],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_distinct_symptoms_by_end_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_symptoms_by_end_date(
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_distinct_symptoms_by_end_date(
                "30010096",
                "   ",
            )

    def test_get_patient_distinct_symptoms_by_start_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_symptoms_by_start_date(
            " 30010096 ",
            " 2022-01-01 ",
        )

        self.assertEqual(result, [{"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_SYMPTOMS_BY_START_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
            },
        )

    def test_get_patient_distinct_symptoms_by_start_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_symptoms_by_start_date(
                "   ",
                "2022-01-01",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_distinct_symptoms_by_start_date(
                "30010096",
                "   ",
            )

    def test_get_patient_distinct_symptoms_by_date_range(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_symptoms_by_date_range(
            " 30010096 ",
            " 2022-01-01 ",
            " 2022-01-13 ",
        )

        self.assertEqual(result, [{"sym": {"id": "AU_SYM_0007", "name": "睡眠障碍"}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_distinct_symptoms_by_date_range_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_symptoms_by_date_range(
                "   ",
                "2022-01-01",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_distinct_symptoms_by_date_range(
                "30010096",
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_distinct_symptoms_by_date_range(
                "30010096",
                "2022-01-01",
                "   ",
            )

    def test_get_patient_distinct_diseases_by_end_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}},
            {"dis": {"id": "AU_DIS_0002", "name": "轻度认知障碍"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_diseases_by_end_date(
            " 30010096 ",
            " 2022-01-13 ",
        )

        self.assertEqual(
            result,
            [
                {"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}},
                {"dis": {"id": "AU_DIS_0002", "name": "轻度认知障碍"}},
            ],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_distinct_diseases_by_end_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_diseases_by_end_date(
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_distinct_diseases_by_end_date(
                "30010096",
                "   ",
            )

    def test_get_patient_disease_set_comparison_by_end_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "diseases1": [{"id": "AU_DIS_0001", "name": "阿尔茨海默病"}],
                "diseases2": [{"id": "AU_DIS_0002", "name": "轻度认知障碍"}],
            }
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_disease_set_comparison_by_end_date(
            " 40 ",
            " 20121011 ",
            " 2022-05-22 ",
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
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY,
            parameters={
                "primary_patient_id": "40",
                "comparison_patient_id": "20121011",
                "end_date": "2022-05-22",
            },
        )

    def test_get_patient_disease_set_comparison_by_end_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(
            ValueError,
            "primary_patient_id must be a non-empty string.",
        ):
            repository.get_patient_disease_set_comparison_by_end_date(
                "   ",
                "20121011",
                "2022-05-22",
            )

        with self.assertRaisesRegex(
            ValueError,
            "comparison_patient_id must be a non-empty string.",
        ):
            repository.get_patient_disease_set_comparison_by_end_date(
                "40",
                "   ",
                "2022-05-22",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_disease_set_comparison_by_end_date(
                "40",
                "20121011",
                "   ",
            )

    def test_get_patient_disease_set_comparison_by_start_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "diseases1": [{"id": "AU_DIS_0001", "name": "阿尔茨海默病"}],
                "diseases2": [{"id": "AU_DIS_0002", "name": "轻度认知障碍"}],
            }
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_disease_set_comparison_by_start_date(
            " 40 ",
            " 20121011 ",
            " 2022-05-01 ",
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
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISEASE_SET_COMPARISON_BY_START_DATE_QUERY,
            parameters={
                "primary_patient_id": "40",
                "comparison_patient_id": "20121011",
                "start_date": "2022-05-01",
            },
        )

    def test_get_patient_disease_set_comparison_by_start_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(
            ValueError,
            "primary_patient_id must be a non-empty string.",
        ):
            repository.get_patient_disease_set_comparison_by_start_date(
                "   ",
                "20121011",
                "2022-05-01",
            )

        with self.assertRaisesRegex(
            ValueError,
            "comparison_patient_id must be a non-empty string.",
        ):
            repository.get_patient_disease_set_comparison_by_start_date(
                "40",
                "   ",
                "2022-05-01",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_disease_set_comparison_by_start_date(
                "40",
                "20121011",
                "   ",
            )

    def test_get_patient_disease_set_comparison_by_date_range(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "diseases1": [{"id": "AU_DIS_0001", "name": "阿尔茨海默病"}],
                "diseases2": [{"id": "AU_DIS_0002", "name": "轻度认知障碍"}],
            }
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_disease_set_comparison_by_date_range(
            " 40 ",
            " 20121011 ",
            " 2022-05-01 ",
            " 2022-05-22 ",
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
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISEASE_SET_COMPARISON_BY_DATE_RANGE_QUERY,
            parameters={
                "primary_patient_id": "40",
                "comparison_patient_id": "20121011",
                "start_date": "2022-05-01",
                "end_date": "2022-05-22",
            },
        )

    def test_get_patient_disease_set_comparison_by_date_range_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(
            ValueError,
            "primary_patient_id must be a non-empty string.",
        ):
            repository.get_patient_disease_set_comparison_by_date_range(
                "   ",
                "20121011",
                "2022-05-01",
                "2022-05-22",
            )

        with self.assertRaisesRegex(
            ValueError,
            "comparison_patient_id must be a non-empty string.",
        ):
            repository.get_patient_disease_set_comparison_by_date_range(
                "40",
                "   ",
                "2022-05-01",
                "2022-05-22",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_disease_set_comparison_by_date_range(
                "40",
                "20121011",
                "   ",
                "2022-05-22",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_disease_set_comparison_by_date_range(
                "40",
                "20121011",
                "2022-05-01",
                "   ",
            )

    def test_get_patient_distinct_diseases_by_start_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_diseases_by_start_date(
            " 30010096 ",
            " 2022-01-01 ",
        )

        self.assertEqual(result, [{"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_DISEASES_BY_START_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
            },
        )

    def test_get_patient_distinct_diseases_by_start_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_diseases_by_start_date(
                "   ",
                "2022-01-01",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_distinct_diseases_by_start_date(
                "30010096",
                "   ",
            )

    def test_get_patient_distinct_diseases_by_date_range(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_diseases_by_date_range(
            " 30010096 ",
            " 2022-01-01 ",
            " 2022-01-13 ",
        )

        self.assertEqual(result, [{"dis": {"id": "AU_DIS_0001", "name": "阿尔茨海默病"}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_distinct_diseases_by_date_range_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_diseases_by_date_range(
                "   ",
                "2022-01-01",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_distinct_diseases_by_date_range(
                "30010096",
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_distinct_diseases_by_date_range(
                "30010096",
                "2022-01-01",
                "   ",
            )

    def test_get_patient_distinct_unknowns_by_end_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}},
            {"un": {"id": "AU_UNK_0002", "name": "待分类表现"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_unknowns_by_end_date(
            " 30010096 ",
            " 2022-01-13 ",
        )

        self.assertEqual(
            result,
            [
                {"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}},
                {"un": {"id": "AU_UNK_0002", "name": "待分类表现"}},
            ],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_distinct_unknowns_by_end_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_unknowns_by_end_date(
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_distinct_unknowns_by_end_date(
                "30010096",
                "   ",
            )

    def test_get_patient_distinct_unknowns_by_start_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_unknowns_by_start_date(
            " 30010096 ",
            " 2022-01-01 ",
        )

        self.assertEqual(result, [{"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_UNKNOWNS_BY_START_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
            },
        )

    def test_get_patient_distinct_unknowns_by_start_date_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_unknowns_by_start_date(
                "   ",
                "2022-01-01",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_distinct_unknowns_by_start_date(
                "30010096",
                "   ",
            )

    def test_get_patient_distinct_unknowns_by_date_range(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_unknowns_by_date_range(
            " 30010096 ",
            " 2022-01-01 ",
            " 2022-01-13 ",
        )

        self.assertEqual(result, [{"un": {"id": "AU_UNK_0001", "name": "其他异常表现"}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_distinct_unknowns_by_date_range_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_distinct_unknowns_by_date_range(
                "   ",
                "2022-01-01",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_distinct_unknowns_by_date_range(
                "30010096",
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_distinct_unknowns_by_date_range(
                "30010096",
                "2022-01-01",
                "   ",
            )

    def test_dated_randomized_path_by_end_date_query_keeps_date_order_constraint(
        self,
    ) -> None:
        self.assertIn(
            "date(s1.`训练日期`) >= date(s2.`训练日期`)",
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertIn(
            "date(s1.`训练日期`) <= date($end_date)",
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )

    def test_end_date_randomized_path_query_matches_new_contract(self) -> None:
        self.assertIn(
            "date(s1.`训练日期`) <= date($end_date)",
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_END_DATE_RANDOMIZED_PATH_QUERY,
        )
        self.assertNotIn(
            "date(s1.`训练日期`) >= date(s2.`训练日期`)",
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_END_DATE_RANDOMIZED_PATH_QUERY,
        )

    def test_load_query_settings_from_yaml(self) -> None:
        settings = load_query_settings("config/settings.yaml")

        self.assertEqual(settings.graph_path_limit.max_limit_source, "total_paths")
        self.assertEqual(settings.graph_path_limit.per_g_strategy, "band")
        self.assertEqual(
            settings.graph_path_limit.bands,
            (
                QueryLimitBandSettings(max_g_count=49, per_g=10),
                QueryLimitBandSettings(max_g_count=199, per_g=6),
                QueryLimitBandSettings(max_g_count=None, per_g=4),
            ),
        )
        self.assertEqual(settings.pattern_path_storage.output_dir, "data/pattern_paths")
        self.assertEqual(settings.candidate_ranking.path_top_k, 50)
        self.assertEqual(settings.candidate_ranking.candidate_top_k, 10)

    def test_get_patient_task_instance_set_ordered_training_dates(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "p": {"id": "30010096"},
                "orderedDatesa": ["2022-01-01", "2022-01-13"],
            }
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_instance_set_ordered_training_dates(
            " 30010096 "
        )

        self.assertEqual(
            result,
            [{"p": {"id": "30010096"}, "orderedDatesa": ["2022-01-01", "2022-01-13"]}],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY,
            parameters={"patient_id": "30010096"},
        )

    def test_get_patient_task_instance_set_ordered_training_dates_rejects_blank_patient_id(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_task_instance_set_ordered_training_dates("   ")

    def test_get_patient_task_set_task_game_task_set_patient_pattern_statistics(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 12, "gCount": 3, "p2Count": 4}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_pattern_statistics(
            " 30010096 "
        )

        self.assertEqual(
            result,
            [{"totalPaths": 12, "gCount": 3, "p2Count": 4}],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY,
            parameters={"patient_id": "30010096"},
        )

    def test_get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 8, "gCount": 2, "p2Count": 3}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics(
            " 30010096 "
        )

        self.assertEqual(
            result,
            [{"totalPaths": 8, "gCount": 2, "p2Count": 3}],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY,
            parameters={"patient_id": "30010096"},
        )

    def test_get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 7, "gCount": 2, "p2Count": 3}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date(
            " 30010096 ",
            " 2022-01-13 ",
        )

        self.assertEqual(result, [{"totalPaths": 7, "gCount": 2, "p2Count": 3}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY,
            parameters={"patient_id": "30010096", "end_date": "2022-01-13"},
        )

    def test_get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_start_date(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 6, "gCount": 2, "p2Count": 2}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_start_date(
            " 30010096 ",
            " 2022-01-01 ",
        )

        self.assertEqual(result, [{"totalPaths": 6, "gCount": 2, "p2Count": 2}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY,
            parameters={"patient_id": "30010096", "start_date": "2022-01-01"},
        )

    def test_get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_date_range(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 5, "gCount": 1, "p2Count": 2}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_date_range(
            " 30010096 ",
            " 2022-01-01 ",
            " 2022-01-13 ",
        )

        self.assertEqual(result, [{"totalPaths": 5, "gCount": 1, "p2Count": 2}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_task_set_task_game_task_set_patient_pattern_statistics_rejects_blank_patient_id(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_pattern_statistics(
                "   "
            )

    def test_get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_rejects_blank_patient_id(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics(
                "   "
            )

    def test_get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_with_date_filters_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date(
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_end_date(
                "30010096",
                "   ",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_start_date(
                "30010096",
                "   ",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_date_range(
                "30010096",
                "   ",
                "2022-01-13",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_pattern_statistics_by_date_range(
                "30010096",
                "2022-01-01",
                "   ",
            )

    def test_get_patient_task_set_task_game_task_set_patient_randomized_paths(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
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
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_randomized_paths(
            " 30010096 ",
            per_g=3,
            limit=100,
        )

        self.assertEqual(
            result,
            [
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
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_RANDOMIZED_PATH_QUERY,
            parameters={
                "patient_id": "30010096",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_patient_task_set_task_game_task_set_patient_randomized_paths_rejects_invalid_parameters(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_randomized_paths(
                "   ",
                per_g=3,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "per_g must be a positive integer."):
            repository.get_patient_task_set_task_game_task_set_patient_randomized_paths(
                "30010096",
                per_g=0,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "limit must be a positive integer."):
            repository.get_patient_task_set_task_game_task_set_patient_randomized_paths(
                "30010096",
                per_g=3,
                limit=0,
            )

    def test_get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_start_date(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_start_date(
            " 30010096 ",
            " 2022-01-13 ",
            per_g=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-13",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_start_date_rejects_invalid_parameters(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_start_date(
                "   ",
                "2022-01-13",
                per_g=3,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_start_date(
                "30010096",
                "   ",
                per_g=3,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "per_g must be a positive integer."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_start_date(
                "30010096",
                "2022-01-13",
                per_g=0,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "limit must be a positive integer."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_start_date(
                "30010096",
                "2022-01-13",
                per_g=3,
                limit=0,
            )

    def test_get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date(
            " 30010096 ",
            " 2022-01-13 ",
            per_g=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "end_date": "2022-01-13",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_patient_task_set_task_game_task_set_patient_randomized_paths_by_end_date(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_randomized_paths_by_end_date(
            " 30010096 ",
            " 2022-01-13 ",
            per_g=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_END_DATE_RANDOMIZED_PATH_QUERY,
            parameters={
                "patient_id": "30010096",
                "end_date": "2022-01-13",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date_rejects_invalid_parameters(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date(
                "   ",
                "2022-01-13",
                per_g=3,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date(
                "30010096",
                "   ",
                per_g=3,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "per_g must be a positive integer."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date(
                "30010096",
                "2022-01-13",
                per_g=0,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "limit must be a positive integer."):
            repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_end_date(
                "30010096",
                "2022-01-13",
                per_g=3,
                limit=0,
            )

    def test_get_patient_task_set_task_game_task_set_patient_randomized_paths_by_end_date_rejects_invalid_parameters(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_randomized_paths_by_end_date(
                "   ",
                "2022-01-13",
                per_g=3,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_randomized_paths_by_end_date(
                "30010096",
                "   ",
                per_g=3,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "per_g must be a positive integer."):
            repository.get_patient_task_set_task_game_task_set_patient_randomized_paths_by_end_date(
                "30010096",
                "2022-01-13",
                per_g=0,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "limit must be a positive integer."):
            repository.get_patient_task_set_task_game_task_set_patient_randomized_paths_by_end_date(
                "30010096",
                "2022-01-13",
                per_g=3,
                limit=0,
            )

    def test_recommend_graph_path_limit_uses_config_yaml(self) -> None:
        repository = KgRepository(client=Mock())

        result = repository.recommend_graph_path_limit(
            total_paths=500,
            g_count=20,
            p2_count=25,
        )

        self.assertEqual(result, GraphPathLimitRecommendation(per_g=10, limit=200))

    def test_recommend_graph_path_limit_caps_by_total_paths(self) -> None:
        repository = KgRepository(client=Mock())

        result = repository.recommend_graph_path_limit(
            total_paths=120,
            g_count=300,
            p2_count=301,
        )

        self.assertEqual(result, GraphPathLimitRecommendation(per_g=4, limit=120))

    def test_recommend_graph_path_limit_uses_p2_div_g_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        '  per_g_strategy: "p2_div_g"',
                        "  bands:",
                        "    - per_g: 5",
                        '  max_limit_source: "total_paths"',
                    ]
                ),
                encoding="utf-8",
            )

            repository = KgRepository(client=Mock(), config_path=config_path)

            result = repository.recommend_graph_path_limit(
                total_paths=100,
                g_count=3,
                p2_count=10,
            )

        self.assertEqual(result, GraphPathLimitRecommendation(per_g=4, limit=12))

    def test_recommend_graph_path_limit_returns_zero_limit_when_g_count_is_zero(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        '  per_g_strategy: "p2_div_g"',
                        "  bands:",
                        "    - per_g: 5",
                        '  max_limit_source: "total_paths"',
                    ]
                ),
                encoding="utf-8",
            )

            repository = KgRepository(client=Mock(), config_path=config_path)

            result = repository.recommend_graph_path_limit(
                total_paths=100,
                g_count=0,
                p2_count=10,
            )

        self.assertEqual(result, GraphPathLimitRecommendation(per_g=1, limit=0))

    def test_recommend_graph_path_limit_rejects_negative_inputs(self) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            repository.recommend_graph_path_limit(total_paths=-1, g_count=20, p2_count=1)

        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            repository.recommend_graph_path_limit(total_paths=1, g_count=20, p2_count=-1)

    def test_recommend_graph_path_limit_rejects_unsupported_limit_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 5",
                        '  max_limit_source: "unsupported"',
                    ]
                ),
                encoding="utf-8",
            )

            repository = KgRepository(client=Mock(), config_path=config_path)

            with self.assertRaisesRegex(ValueError, "Unsupported max_limit_source"):
                repository.recommend_graph_path_limit(total_paths=10, g_count=1, p2_count=1)

    def test_recommend_graph_path_limit_rejects_unsupported_per_g_strategy(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        '  per_g_strategy: "unsupported"',
                        "  bands:",
                        "    - per_g: 5",
                        '  max_limit_source: "total_paths"',
                    ]
                ),
                encoding="utf-8",
            )

            repository = KgRepository(client=Mock(), config_path=config_path)

            with self.assertRaisesRegex(ValueError, "Unsupported per_g_strategy"):
                repository.recommend_graph_path_limit(
                    total_paths=10,
                    g_count=1,
                    p2_count=1,
                )


if __name__ == "__main__":
    unittest.main()
