"""Tests for KG repository query orchestration."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.similar_user.data_access.cypher_queries import (
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY,
    P_E_I_G_I_E_P_PATH_STATISTICS_QUERY,
)
from src.similar_user.data_access.kg_repository import KgRepository


class KgRepositoryTest(unittest.TestCase):
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

    def test_get_patient_task_set_task_game_task_set_patient_pattern_statistics_rejects_blank_patient_id(
        self,
    ) -> None:
        repository = KgRepository(client=Mock())

        with self.assertRaisesRegex(ValueError, "patient_id must be a non-empty string."):
            repository.get_patient_task_set_task_game_task_set_patient_pattern_statistics(
                "   "
            )

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
