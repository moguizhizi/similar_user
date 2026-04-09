"""Tests for KG repository query orchestration."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from config.settings import QueryLimitBandSettings, load_query_settings
from src.similar_user.data_access.cypher_queries import (
    PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_RANDOMIZED_PATH_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY,
    P_E_I_G_I_E_P_PATH_STATISTICS_QUERY,
)
from src.similar_user.data_access.kg_repository import (
    GraphPathLimitRecommendation,
    KgRepository,
)


class KgRepositoryTest(unittest.TestCase):
    def test_load_query_settings_from_yaml(self) -> None:
        settings = load_query_settings("config/query.yaml")

        self.assertEqual(settings.graph_path_limit.max_limit_source, "total_paths")
        self.assertEqual(
            settings.graph_path_limit.bands,
            (
                QueryLimitBandSettings(max_g_count=49, per_g=10),
                QueryLimitBandSettings(max_g_count=199, per_g=6),
                QueryLimitBandSettings(max_g_count=None, per_g=4),
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
        mock_client.run_query.return_value = [{"path": ["mocked-path"]}]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_task_set_task_game_task_set_patient_randomized_paths(
            " 30010096 ",
            per_g=3,
            limit=100,
        )

        self.assertEqual(result, [{"path": ["mocked-path"]}])
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

    def test_recommend_graph_path_limit_uses_query_yaml(self) -> None:
        repository = KgRepository(client=Mock())

        result = repository.recommend_graph_path_limit(total_paths=500, g_count=20)

        self.assertEqual(result, GraphPathLimitRecommendation(per_g=10, limit=200))

    def test_recommend_graph_path_limit_caps_by_total_paths(self) -> None:
        repository = KgRepository(client=Mock())

        result = repository.recommend_graph_path_limit(total_paths=120, g_count=300)

        self.assertEqual(result, GraphPathLimitRecommendation(per_g=4, limit=120))

    def test_recommend_graph_path_limit_rejects_negative_inputs(self) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "non-negative integer"):
            repository.recommend_graph_path_limit(total_paths=-1, g_count=20)

    def test_recommend_graph_path_limit_rejects_unsupported_limit_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "query.yaml"
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

            repository = KgRepository(client=Mock(), query_config_path=config_path)

            with self.assertRaisesRegex(ValueError, "Unsupported max_limit_source"):
                repository.recommend_graph_path_limit(total_paths=10, g_count=1)

    def test_get_patient_p_e_i_g_i_e_p_path_statistics_uses_default_limits(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [
            {"lim": 500, "totalPaths": 12, "gCount": 3, "pCount": 4}
        ]
        repository = KgRepository(client=mock_client)

        result = repository.get_patient_p_e_i_g_i_e_p_path_statistics("30010096")

        self.assertEqual(
            result,
            [{"lim": 500, "totalPaths": 12, "gCount": 3, "pCount": 4}],
        )
        mock_client.run_query.assert_called_once_with(
            query=P_E_I_G_I_E_P_PATH_STATISTICS_QUERY,
            parameters={
                "patient_id": "30010096",
                "limits": [500, 1000, 2000, 3000, 5000],
            },
        )

    def test_get_patient_p_e_i_g_i_e_p_path_statistics_accepts_custom_limits(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = []
        repository = KgRepository(client=mock_client)

        repository.get_patient_p_e_i_g_i_e_p_path_statistics(
            " 30010096 ",
            limits=(100, 200),
        )

        mock_client.run_query.assert_called_once_with(
            query=P_E_I_G_I_E_P_PATH_STATISTICS_QUERY,
            parameters={
                "patient_id": "30010096",
                "limits": [100, 200],
            },
        )

    def test_get_patient_p_e_i_g_i_e_p_path_statistics_rejects_blank_patient_id(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_p_e_i_g_i_e_p_path_statistics("   ")

    def test_get_patient_p_e_i_g_i_e_p_path_statistics_rejects_invalid_limits(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "positive integers"):
            repository.get_patient_p_e_i_g_i_e_p_path_statistics(
                "30010096",
                limits=[500, 0],
            )


if __name__ == "__main__":
    unittest.main()
