"""Tests for KG repository query orchestration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from config.settings import QueryLimitBandSettings, load_query_settings
from src.similar_user.data_access.cypher_queries import (
    DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
    SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
    UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
    DISTINCT_TRAINING_GAMES_QUERY,
    PATIENT_IDS_QUERY,
    PATIENT_IDS_WITH_TRAINING_ON_DATE_QUERY,
    PATIENT_DISEASE_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_DISEASE_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_START_DATE_QUERY,
    PATIENT_GAMES_BY_DATE_RANGE_QUERY,
    PATIENT_GAMES_BY_END_DATE_QUERY,
    PATIENT_GAMES_BY_START_DATE_QUERY,
    PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_SYMPTOM_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_SYMPTOM_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY,
    PATIENT_UNKNOWN_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_UNKNOWN_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY,
    PATIENT_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY,
    PATIENT_TRAINING_TASK_HISTORY_QUERY,
    SOURCE_PATIENT_IDS_WITH_SECONDARY_ABILITY_SCORES_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY,
)
from src.similar_user.data_access.kg_repository import (
    GraphPathLimitRecommendation,
    KgRepository,
    PatternQueryFamily,
)
from src.similar_user.domain.graph_schema import PathPattern


class KgRepositoryTest(unittest.TestCase):
    def test_get_patient_ids(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"patient_id": "40"},
            {"patient_id": " 41 "},
            {"patient_id": ""},
            {"patient_id": None},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_ids()

        self.assertEqual(result, ["40", "41"])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_IDS_QUERY,
            parameters={},
        )

    def test_get_patient_ids_with_training_on_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"patient_id": "40"},
            {"patient_id": " 41 "},
            {"patient_id": ""},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_ids_with_training_on_date(" 2022-05-22 ")

        self.assertEqual(result, ["40", "41"])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_IDS_WITH_TRAINING_ON_DATE_QUERY,
            parameters={"base_date": "2022-05-22"},
        )

    def test_get_patient_ids_with_training_on_date_rejects_blank_base_date(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "base_date must be a non-empty string."):
            repository.get_patient_ids_with_training_on_date("   ")

    def test_get_source_patient_ids_with_secondary_ability_scores(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"patient_id": "40"},
            {"patient_id": " 41 "},
            {"patient_id": ""},
            {"patient_id": None},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_source_patient_ids_with_secondary_ability_scores()

        self.assertEqual(result, ["40", "41"])
        mock_client.run_query.assert_called_once_with(
            query=SOURCE_PATIENT_IDS_WITH_SECONDARY_ABILITY_SCORES_QUERY,
            parameters={},
        )

    def test_get_distinct_training_games(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"g": {"id": "42", "name": "打怪物"}},
            {"g": {"id": "84", "name": "真假句辨别"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_distinct_training_games()

        self.assertEqual(
            result,
            [
                {"g": {"id": "42", "name": "打怪物"}},
                {"g": {"id": "84", "name": "真假句辨别"}},
            ],
        )
        mock_client.run_query.assert_called_once_with(
            query=DISTINCT_TRAINING_GAMES_QUERY,
            parameters={},
        )

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

    def test_get_disease_taskset_patient_randomized_paths_selects_base_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"d": {"id": "AU_DIS_0013"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_disease_taskset_patient_randomized_paths(
            " AU_DIS_0013 "
        )

        self.assertEqual(result, [{"row": {"d": {"id": "AU_DIS_0013"}}}])
        mock_client.run_query.assert_called_once_with(
            query=DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
            parameters={"disease_id": "AU_DIS_0013"},
        )

    def test_get_disease_taskset_patient_randomized_paths_selects_start_date_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = []
        repository = KgRepository(client=mock_client)

        result = repository.get_disease_taskset_patient_randomized_paths(
            " AU_DIS_0013 ",
            start_date=" 2022-01-01 ",
        )

        self.assertEqual(result, [])
        mock_client.run_query.assert_called_once_with(
            query=DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
            parameters={
                "disease_id": "AU_DIS_0013",
                "start_date": "2022-01-01",
            },
        )

    def test_get_disease_taskset_patient_randomized_paths_selects_end_date_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = []
        repository = KgRepository(client=mock_client)

        result = repository.get_disease_taskset_patient_randomized_paths(
            " AU_DIS_0013 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [])
        mock_client.run_query.assert_called_once_with(
            query=DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
            parameters={
                "disease_id": "AU_DIS_0013",
                "end_date": "2022-01-13",
            },
        )

    def test_get_disease_taskset_patient_randomized_paths_selects_date_range_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = []
        repository = KgRepository(client=mock_client)

        result = repository.get_disease_taskset_patient_randomized_paths(
            " AU_DIS_0013 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [])
        mock_client.run_query.assert_called_once_with(
            query=DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "disease_id": "AU_DIS_0013",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_disease_taskset_patient_randomized_paths_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "disease_id must be a non-empty string."):
            repository.get_disease_taskset_patient_randomized_paths("   ")

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string or None."):
            repository.get_disease_taskset_patient_randomized_paths(
                "AU_DIS_0013",
                start_date="   ",
            )

    def test_get_symptom_taskset_patient_randomized_paths_selects_base_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"sym": {"id": "AU_SYM_0007"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_symptom_taskset_patient_randomized_paths(
            " AU_SYM_0007 "
        )

        self.assertEqual(result, [{"row": {"sym": {"id": "AU_SYM_0007"}}}])
        mock_client.run_query.assert_called_once_with(
            query=SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
            parameters={"symptom_id": "AU_SYM_0007"},
        )

    def test_get_symptom_taskset_patient_randomized_paths_selects_date_range_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = []
        repository = KgRepository(client=mock_client)

        result = repository.get_symptom_taskset_patient_randomized_paths(
            " AU_SYM_0007 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [])
        mock_client.run_query.assert_called_once_with(
            query=SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "symptom_id": "AU_SYM_0007",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_symptom_taskset_patient_randomized_paths_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "symptom_id must be a non-empty string."):
            repository.get_symptom_taskset_patient_randomized_paths("   ")

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string or None."):
            repository.get_symptom_taskset_patient_randomized_paths(
                "AU_SYM_0007",
                end_date="   ",
            )

    def test_get_unknown_taskset_patient_randomized_paths_selects_base_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"un": {"id": "AU_UNKOWN_0005"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_unknown_taskset_patient_randomized_paths(
            " AU_UNKOWN_0005 "
        )

        self.assertEqual(result, [{"row": {"un": {"id": "AU_UNKOWN_0005"}}}])
        mock_client.run_query.assert_called_once_with(
            query=UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
            parameters={"unknown_id": "AU_UNKOWN_0005"},
        )

    def test_get_unknown_taskset_patient_randomized_paths_selects_start_date_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = []
        repository = KgRepository(client=mock_client)

        result = repository.get_unknown_taskset_patient_randomized_paths(
            " AU_UNKOWN_0005 ",
            start_date=" 2022-01-01 ",
        )

        self.assertEqual(result, [])
        mock_client.run_query.assert_called_once_with(
            query=UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
            parameters={
                "unknown_id": "AU_UNKOWN_0005",
                "start_date": "2022-01-01",
            },
        )

    def test_get_unknown_taskset_patient_randomized_paths_selects_end_date_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = []
        repository = KgRepository(client=mock_client)

        result = repository.get_unknown_taskset_patient_randomized_paths(
            " AU_UNKOWN_0005 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [])
        mock_client.run_query.assert_called_once_with(
            query=UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
            parameters={
                "unknown_id": "AU_UNKOWN_0005",
                "end_date": "2022-01-13",
            },
        )

    def test_get_unknown_taskset_patient_randomized_paths_selects_date_range_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = []
        repository = KgRepository(client=mock_client)

        result = repository.get_unknown_taskset_patient_randomized_paths(
            " AU_UNKOWN_0005 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [])
        mock_client.run_query.assert_called_once_with(
            query=UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "unknown_id": "AU_UNKOWN_0005",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_unknown_taskset_patient_randomized_paths_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "unknown_id must be a non-empty string."):
            repository.get_unknown_taskset_patient_randomized_paths("   ")

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string or None."):
            repository.get_unknown_taskset_patient_randomized_paths(
                "AU_UNKOWN_0005",
                start_date="   ",
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

    def test_get_patient_distinct_games_by_start_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"g": {"id": "42", "name": "打怪物"}},
            {"g": {"id": "84", "name": "真假句辨别"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_games_by_start_date(
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
            query=PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-13",
            },
        )

    def test_get_patient_distinct_games_by_date_range(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"g": {"id": "42", "name": "打怪物"}},
            {"g": {"id": "84", "name": "真假句辨别"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_distinct_games_by_date_range(
            " 30010096 ",
            " 2022-01-13 ",
            " 2022-05-22 ",
        )

        self.assertEqual(
            result,
            [
                {"g": {"id": "42", "name": "打怪物"}},
                {"g": {"id": "84", "name": "真假句辨别"}},
            ],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-13",
                "end_date": "2022-05-22",
            },
        )

    def test_get_patient_games_by_end_date_keeps_duplicate_rows(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"g": {"id": "42", "name": "打怪物"}},
            {"g": {"id": "42", "name": "打怪物"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_games_by_end_date(
            " 30010096 ",
            " 2022-01-13 ",
        )

        self.assertEqual(
            result,
            [
                {"g": {"id": "42", "name": "打怪物"}},
                {"g": {"id": "42", "name": "打怪物"}},
            ],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_GAMES_BY_END_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "end_date": "2022-01-13",
            },
        )

    def test_get_patient_games_by_start_date_keeps_duplicate_rows(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"g": {"id": "42", "name": "打怪物"}},
            {"g": {"id": "42", "name": "打怪物"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_games_by_start_date(
            " 30010096 ",
            " 2022-01-13 ",
        )

        self.assertEqual(
            result,
            [
                {"g": {"id": "42", "name": "打怪物"}},
                {"g": {"id": "42", "name": "打怪物"}},
            ],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_GAMES_BY_START_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-13",
            },
        )

    def test_get_patient_games_by_date_range_keeps_duplicate_rows(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"g": {"id": "42", "name": "打怪物"}},
            {"g": {"id": "42", "name": "打怪物"}},
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_games_by_date_range(
            " 30010096 ",
            " 2022-01-13 ",
            " 2022-05-22 ",
        )

        self.assertEqual(
            result,
            [
                {"g": {"id": "42", "name": "打怪物"}},
                {"g": {"id": "42", "name": "打怪物"}},
            ],
        )
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_GAMES_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-13",
                "end_date": "2022-05-22",
            },
        )

    def test_get_patient_game_set_comparison_by_end_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "games1": [{"id": "42", "name": "打怪物"}],
                "games2": [{"id": "84", "name": "真假句辨别"}],
            }
        ]
        repository = KgRepository(client=mock_client)

        with patch(
            "src.similar_user.data_access.kg_repository.get_graph_query_spec"
        ) as mock_get_graph_query_spec:
            mock_get_graph_query_spec.return_value = Mock(query="REGISTERED QUERY")

            result = repository.get_patient_game_set_comparison_by_end_date(
                " 40 ",
                " 20121011 ",
                " 2022-05-22 ",
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
        mock_get_graph_query_spec.assert_called_once_with(
            "patient_game_set_comparison_by_end_date"
        )
        mock_client.run_query.assert_called_once_with(
            query="REGISTERED QUERY",
            parameters={
                "primary_patient_id": "40",
                "comparison_patient_id": "20121011",
                "end_date": "2022-05-22",
            },
        )

    def test_get_patient_game_set_comparison_by_start_date(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "games1": [{"id": "42", "name": "打怪物"}],
                "games2": [{"id": "84", "name": "真假句辨别"}],
            }
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_game_set_comparison_by_start_date(
            " 40 ",
            " 20121011 ",
            " 2022-05-01 ",
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
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY,
            parameters={
                "primary_patient_id": "40",
                "comparison_patient_id": "20121011",
                "start_date": "2022-05-01",
            },
        )

    def test_get_patient_game_set_comparison_by_date_range(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "games1": [{"id": "42", "name": "打怪物"}],
                "games2": [{"id": "84", "name": "真假句辨别"}],
            }
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_game_set_comparison_by_date_range(
            " 40 ",
            " 20121011 ",
            " 2022-05-01 ",
            " 2022-05-22 ",
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
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY,
            parameters={
                "primary_patient_id": "40",
                "comparison_patient_id": "20121011",
                "start_date": "2022-05-01",
                "end_date": "2022-05-22",
            },
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

    def test_get_patient_symptom_set_comparison_queries(self) -> None:
        cases = [
            (
                "get_patient_symptom_set_comparison_by_end_date",
                PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY,
                (" 40 ", " 20121011 ", " 2022-05-22 "),
                {
                    "primary_patient_id": "40",
                    "comparison_patient_id": "20121011",
                    "end_date": "2022-05-22",
                },
            ),
            (
                "get_patient_symptom_set_comparison_by_start_date",
                PATIENT_SYMPTOM_SET_COMPARISON_BY_START_DATE_QUERY,
                (" 40 ", " 20121011 ", " 2022-05-01 "),
                {
                    "primary_patient_id": "40",
                    "comparison_patient_id": "20121011",
                    "start_date": "2022-05-01",
                },
            ),
            (
                "get_patient_symptom_set_comparison_by_date_range",
                PATIENT_SYMPTOM_SET_COMPARISON_BY_DATE_RANGE_QUERY,
                (" 40 ", " 20121011 ", " 2022-05-01 ", " 2022-05-22 "),
                {
                    "primary_patient_id": "40",
                    "comparison_patient_id": "20121011",
                    "start_date": "2022-05-01",
                    "end_date": "2022-05-22",
                },
            ),
        ]

        for method_name, query, args, parameters in cases:
            with self.subTest(method_name=method_name):
                mock_client = Mock()
                mock_client.run_query.return_value = [
                    {
                        "symptoms1": [{"id": "AU_SYM_0007", "name": "睡眠障碍"}],
                        "symptoms2": [{"id": "AU_SYM_0012", "name": "注意力不集中"}],
                    }
                ]
                repository = KgRepository(client=mock_client)

                result = getattr(repository, method_name)(*args)

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
                mock_client.run_query.assert_called_once_with(
                    query=query,
                    parameters=parameters,
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

    def test_get_patient_unknown_set_comparison_queries(self) -> None:
        cases = [
            (
                "get_patient_unknown_set_comparison_by_end_date",
                PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY,
                (" 40 ", " 20121011 ", " 2022-05-22 "),
                {
                    "primary_patient_id": "40",
                    "comparison_patient_id": "20121011",
                    "end_date": "2022-05-22",
                },
            ),
            (
                "get_patient_unknown_set_comparison_by_start_date",
                PATIENT_UNKNOWN_SET_COMPARISON_BY_START_DATE_QUERY,
                (" 40 ", " 20121011 ", " 2022-05-01 "),
                {
                    "primary_patient_id": "40",
                    "comparison_patient_id": "20121011",
                    "start_date": "2022-05-01",
                },
            ),
            (
                "get_patient_unknown_set_comparison_by_date_range",
                PATIENT_UNKNOWN_SET_COMPARISON_BY_DATE_RANGE_QUERY,
                (" 40 ", " 20121011 ", " 2022-05-01 ", " 2022-05-22 "),
                {
                    "primary_patient_id": "40",
                    "comparison_patient_id": "20121011",
                    "start_date": "2022-05-01",
                    "end_date": "2022-05-22",
                },
            ),
        ]

        for method_name, query, args, parameters in cases:
            with self.subTest(method_name=method_name):
                mock_client = Mock()
                mock_client.run_query.return_value = [
                    {
                        "unknowns1": [{"id": "AU_UNK_0001", "name": "其他异常表现"}],
                        "unknowns2": [{"id": "AU_UNK_0002", "name": "待分类表现"}],
                    }
                ]
                repository = KgRepository(client=mock_client)

                result = getattr(repository, method_name)(*args)

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
                mock_client.run_query.assert_called_once_with(
                    query=query,
                    parameters=parameters,
                )

    def test_dated_randomized_path_by_end_date_query_keeps_date_order_constraint(
        self,
    ) -> None:
        self.assertIn(
            "date(s1.`训练日期`) >= date(s2.`训练日期`)",
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertIn(
            "date(s1.`训练日期`) < date($end_date)",
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertNotEqual(
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_QUERY,
        )

    def test_date_window_randomized_path_by_end_date_query_matches_contract(self) -> None:
        self.assertIn(
            "date(s1.`训练日期`) < date($end_date)",
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertNotIn(
            "date(s1.`训练日期`) >= date(s2.`训练日期`)",
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
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
        self.assertEqual(settings.candidate_ranking.candidate_top_k, 10)
        self.assertEqual(
            settings.candidate_ranking.patterns,
            (
                "patient_game_patient",
                "patient_disease_patient",
                "patient_symptom_patient",
                "patient_unknown_patient",
            ),
        )

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

    def test_get_patient_training_task_history(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "trainingDate": "2022-01-13",
                "i": {"id": "i-1", "任务类型": "专属"},
                "g": {"id": "42", "name": "打怪物"},
            }
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_training_task_history(" 30010096 ")

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
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TRAINING_TASK_HISTORY_QUERY,
            parameters={"patient_id": "30010096"},
        )

    def test_get_patient_training_task_history_rejects_blank_patient_id(self) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_training_task_history("   ")

    def test_get_patient_training_task_history_by_date_window(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {
                "trainingDate": "2022-05-21",
                "g": {"id": "42", "name": "打怪物"},
            }
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_training_task_history_by_date_window(
            " 30010096 ",
            " 2022-05-20 ",
            " 2022-05-22 ",
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
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-05-20",
                "end_date": "2022-05-22",
            },
        )

    def test_get_patient_training_task_history_by_date_window_rejects_blank_inputs(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_training_task_history_by_date_window(
                "   ",
                "2022-05-20",
                "2022-05-22",
            )

        with self.assertRaisesRegex(ValueError, "start_date must be a non-empty string."):
            repository.get_patient_training_task_history_by_date_window(
                "30010096",
                "   ",
                "2022-05-22",
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_patient_training_task_history_by_date_window(
                "30010096",
                "2022-05-20",
                "   ",
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

    def test_get_training_order_pattern_statistics_by_date_range_uses_registered_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 5, "gCount": 1, "p2Count": 2}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_training_order_pattern_statistics_by_date_range(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
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

    def test_get_pattern_statistics_selects_training_order_date_range_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 5, "gCount": 1, "p2Count": 2}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_statistics(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            query_family=PatternQueryFamily.TRAINING_ORDER,
            patient_id=" 30010096 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
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

    def test_get_pattern_date_window_statistics_by_date_range_uses_registered_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 7, "gCount": 3, "p2Count": 4}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_date_window_statistics_by_date_range(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            " 30010096 ",
            " 2022-01-01 ",
            " 2022-01-13 ",
        )

        self.assertEqual(result, [{"totalPaths": 7, "gCount": 3, "p2Count": 4}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_pattern_statistics_selects_date_window_date_range_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 7, "gCount": 3, "p2Count": 4}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_statistics(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            query_family="date_window",
            patient_id=" 30010096 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [{"totalPaths": 7, "gCount": 3, "p2Count": 4}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_pattern_statistics_selects_disease_date_window_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 8, "disCount": 2, "p2Count": 5}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_statistics(
            pattern="patient_disease_patient",
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=" 30010096 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [{"totalPaths": 8, "disCount": 2, "p2Count": 5}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_pattern_statistics_selects_disease_training_order_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 6, "disCount": 2, "p2Count": 4}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_statistics(
            pattern="patient_disease_patient",
            query_family=PatternQueryFamily.TRAINING_ORDER,
            patient_id=" 30010096 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [{"totalPaths": 6, "disCount": 2, "p2Count": 4}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_pattern_statistics_selects_symptom_date_window_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 9, "symCount": 3, "p2Count": 5}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_statistics(
            pattern="patient_symptom_patient",
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=" 30010096 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [{"totalPaths": 9, "symCount": 3, "p2Count": 5}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_pattern_statistics_selects_symptom_training_order_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 7, "symCount": 3, "p2Count": 4}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_statistics(
            pattern="patient_symptom_patient",
            query_family=PatternQueryFamily.TRAINING_ORDER,
            patient_id=" 30010096 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [{"totalPaths": 7, "symCount": 3, "p2Count": 4}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_pattern_statistics_selects_unknown_date_window_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 11, "unCount": 3, "p2Count": 6}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_statistics(
            pattern="patient_unknown_patient",
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=" 30010096 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [{"totalPaths": 11, "unCount": 3, "p2Count": 6}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
        )

    def test_get_pattern_statistics_selects_unknown_training_order_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"totalPaths": 10, "unCount": 3, "p2Count": 5}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_statistics(
            pattern="patient_unknown_patient",
            query_family=PatternQueryFamily.TRAINING_ORDER,
            patient_id=" 30010096 ",
            start_date=" 2022-01-01 ",
            end_date=" 2022-01-13 ",
        )

        self.assertEqual(result, [{"totalPaths": 10, "unCount": 3, "p2Count": 5}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-01",
                "end_date": "2022-01-13",
            },
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

    def test_get_pattern_date_window_randomized_paths_by_end_date(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_date_window_randomized_paths_by_end_date(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            " 30010096 ",
            " 2022-01-13 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
            parameters={
                "patient_id": "30010096",
                "end_date": "2022-01-13",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_date_range(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_dated_randomized_paths_by_date_range(
            " 30010096 ",
            " 2022-01-03 ",
            " 2022-01-17 ",
            per_g=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-03",
                "end_date": "2022-01-17",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_pattern_randomized_paths_by_date_range_uses_registered_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_randomized_paths_by_date_range(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            " 30010096 ",
            " 2022-01-03 ",
            " 2022-01-17 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-03",
                "end_date": "2022-01-17",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_pattern_date_window_randomized_paths_by_date_range_uses_registered_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_date_window_randomized_paths_by_date_range(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            " 30010096 ",
            " 2022-01-03 ",
            " 2022-01-17 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-03",
                "end_date": "2022-01-17",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_pattern_randomized_paths_selects_date_window_date_range_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_randomized_paths(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            query_family=PatternQueryFamily.DATE_WINDOW,
            patient_id=" 30010096 ",
            start_date=" 2022-01-03 ",
            end_date=" 2022-01-17 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-03",
                "end_date": "2022-01-17",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_pattern_randomized_paths_selects_training_order_base_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_randomized_paths(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            query_family="training_order",
            patient_id=" 30010096 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_QUERY,
            parameters={
                "patient_id": "30010096",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_pattern_randomized_paths_selects_disease_date_window_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_randomized_paths(
            pattern="patient_disease_patient",
            query_family="date_window",
            patient_id=" 30010096 ",
            start_date=" 2022-01-03 ",
            end_date=" 2022-01-17 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-03",
                "end_date": "2022-01-17",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_pattern_randomized_paths_selects_disease_training_order_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_randomized_paths(
            pattern="patient_disease_patient",
            query_family="training_order",
            patient_id=" 30010096 ",
            start_date=" 2022-01-03 ",
            end_date=" 2022-01-17 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-03",
                "end_date": "2022-01-17",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_pattern_randomized_paths_selects_symptom_date_window_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_randomized_paths(
            pattern="patient_symptom_patient",
            query_family="date_window",
            patient_id=" 30010096 ",
            start_date=" 2022-01-03 ",
            end_date=" 2022-01-17 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-03",
                "end_date": "2022-01-17",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_pattern_randomized_paths_selects_symptom_training_order_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_randomized_paths(
            pattern="patient_symptom_patient",
            query_family="training_order",
            patient_id=" 30010096 ",
            start_date=" 2022-01-03 ",
            end_date=" 2022-01-17 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-03",
                "end_date": "2022-01-17",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_pattern_randomized_paths_selects_unknown_date_window_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_randomized_paths(
            pattern="patient_unknown_patient",
            query_family="date_window",
            patient_id=" 30010096 ",
            start_date=" 2022-01-03 ",
            end_date=" 2022-01-17 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-03",
                "end_date": "2022-01-17",
                "per_g": 3,
                "limit": 100,
            },
        )

    def test_get_pattern_randomized_paths_selects_unknown_training_order_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {"p": {"id": "30010096"}}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_pattern_randomized_paths(
            pattern="patient_unknown_patient",
            query_family="training_order",
            patient_id=" 30010096 ",
            start_date=" 2022-01-03 ",
            end_date=" 2022-01-17 ",
            per_group=3,
            limit=100,
        )

        self.assertEqual(result, [{"row": {"p": {"id": "30010096"}}}])
        mock_client.run_query.assert_called_once_with(
            query=PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            parameters={
                "patient_id": "30010096",
                "start_date": "2022-01-03",
                "end_date": "2022-01-17",
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

    def test_get_pattern_date_window_randomized_paths_by_end_date_rejects_invalid_parameters(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_pattern_date_window_randomized_paths_by_end_date(
                PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "   ",
                "2022-01-13",
                per_group=3,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "end_date must be a non-empty string."):
            repository.get_pattern_date_window_randomized_paths_by_end_date(
                PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "30010096",
                "   ",
                per_group=3,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "per_g must be a positive integer."):
            repository.get_pattern_date_window_randomized_paths_by_end_date(
                PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "30010096",
                "2022-01-13",
                per_group=0,
                limit=100,
            )

        with self.assertRaisesRegex(ValueError, "limit must be a positive integer."):
            repository.get_pattern_date_window_randomized_paths_by_end_date(
                PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "30010096",
                "2022-01-13",
                per_group=3,
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
