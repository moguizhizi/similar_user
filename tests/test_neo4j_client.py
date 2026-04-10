"""Tests for Neo4j client behavior."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from config.settings import load_neo4j_settings
from scripts.debug_patient_pattern_paths import main as patient_path_main
from scripts.debug_patient_pattern_paths import run_patient_pattern_path_flow
from scripts.debug_query import main, run_debug_query
from src.similar_user.data_access.neo4j_client import Neo4jClient


class LoadNeo4jSettingsTest(unittest.TestCase):
    def test_load_neo4j_settings_from_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "neo4j.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        'uri: "bolt://localhost:7687"',
                        'username: "neo4j"',
                        'password: "secret"',
                        'database: "neo4j"',
                    ]
                ),
                encoding="utf-8",
            )

            settings = load_neo4j_settings(config_path)

        self.assertEqual(settings.uri, "bolt://localhost:7687")
        self.assertEqual(settings.username, "neo4j")
        self.assertEqual(settings.password, "secret")
        self.assertEqual(settings.database, "neo4j")


class Neo4jClientTest(unittest.TestCase):
    @patch("src.similar_user.data_access.neo4j_client.GraphDatabase.driver")
    def test_connect_verifies_connectivity(self, mock_driver_factory: Mock) -> None:
        mock_driver = Mock()
        mock_driver_factory.return_value = mock_driver
        client = Neo4jClient.from_config("config/neo4j.yaml")

        client.connect()

        mock_driver_factory.assert_called_once_with(
            "bolt://localhost:7687",
            auth=("neo4j", "password"),
        )
        mock_driver.verify_connectivity.assert_called_once_with()

    @patch("src.similar_user.data_access.neo4j_client.GraphDatabase.driver")
    def test_run_query_returns_plain_dicts(self, mock_driver_factory: Mock) -> None:
        mock_driver = Mock()
        mock_record = Mock()
        mock_record.data.return_value = {"ok": 1}
        mock_driver.execute_query.return_value = ([mock_record], None, None)
        mock_driver_factory.return_value = mock_driver
        client = Neo4jClient.from_config("config/neo4j.yaml")

        result = client.run_query("RETURN 1 AS ok")

        self.assertEqual(result, [{"ok": 1}])
        mock_driver.execute_query.assert_called_once_with(
            "RETURN 1 AS ok",
            parameters_={},
            database_="neo4j",
        )

    @patch("src.similar_user.data_access.neo4j_client.GraphDatabase.driver")
    def test_health_check_uses_simple_query(self, mock_driver_factory: Mock) -> None:
        mock_driver = Mock()
        mock_record = Mock()
        mock_record.data.return_value = {"ok": 1}
        mock_driver.execute_query.return_value = ([mock_record], None, None)
        mock_driver_factory.return_value = mock_driver
        client = Neo4jClient.from_config("config/neo4j.yaml")

        self.assertTrue(client.health_check())


class DebugQueryScriptTest(unittest.TestCase):
    @patch("scripts.debug_query.Neo4jClient.from_config")
    def test_run_debug_query_returns_query_result(
        self,
        mock_from_config: Mock,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"ok": 1, "message": "neo4j connected"}]
        mock_from_config.return_value.__enter__.return_value = mock_client

        result = run_debug_query()

        self.assertEqual(result, [{"ok": 1, "message": "neo4j connected"}])
        mock_client.run_query.assert_called_once_with(
            "RETURN 1 AS ok, 'neo4j connected' AS message"
        )

    @patch("scripts.debug_query.run_debug_query")
    @patch("builtins.print")
    def test_main_prints_json_on_success(
        self,
        mock_print: Mock,
        mock_run_debug_query: Mock,
    ) -> None:
        mock_run_debug_query.return_value = [{"ok": 1, "message": "neo4j connected"}]

        exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_print.assert_called_once_with(
            json.dumps(
                [{"ok": 1, "message": "neo4j connected"}],
                ensure_ascii=False,
                indent=2,
            )
        )


class DebugPatientPatternPathsScriptTest(unittest.TestCase):
    @patch("scripts.debug_patient_pattern_paths.LOGGER")
    @patch("scripts.debug_patient_pattern_paths.append_pattern_result")
    @patch("scripts.debug_patient_pattern_paths.Neo4jClient.from_config")
    def test_run_patient_pattern_path_flow_returns_service_result(
        self,
        mock_from_config: Mock,
        mock_append_pattern_result: Mock,
        mock_logger: Mock,
    ) -> None:
        mock_client = Mock()
        mock_from_config.return_value.__enter__.return_value = mock_client
        mock_repository = Mock()
        mock_repository.query_config_path = "config/query.yaml"
        mock_service = Mock()
        mock_service.get_patient_pattern_paths.return_value = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "paths": [],
        }
        mock_append_pattern_result.return_value = Path(
            "data/pattern_paths/PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT.jsonl"
        )

        with patch(
            "scripts.debug_patient_pattern_paths.KgRepository",
            return_value=mock_repository,
        ) as mock_repository_cls, patch(
            "scripts.debug_patient_pattern_paths.UserService",
            return_value=mock_service,
        ) as mock_service_cls:
            result = run_patient_pattern_path_flow("30010096")

        self.assertEqual(
            result,
            {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "paths": [],
            },
        )
        mock_repository_cls.assert_called_once_with(client=mock_client)
        mock_service_cls.assert_called_once_with(kg_repository=mock_repository)
        mock_service.get_patient_pattern_paths.assert_called_once_with("30010096")
        mock_append_pattern_result.assert_called_once_with(
            {"patient_id": "30010096", "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT", "paths": []},
            "config/query.yaml",
        )
        mock_logger.info.assert_called()

    @patch("scripts.debug_patient_pattern_paths.run_patient_pattern_path_flow")
    @patch("scripts.debug_patient_pattern_paths.parse_args")
    @patch("builtins.print")
    def test_main_prints_json_on_success(
        self,
        mock_print: Mock,
        mock_parse_args: Mock,
        mock_run_flow: Mock,
    ) -> None:
        mock_parse_args.return_value = Mock(
            patient_id="30010096",
            config="config/neo4j.yaml",
            undated=False,
        )
        mock_run_flow.return_value = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "paths": [],
        }

        exit_code = patient_path_main()

        self.assertEqual(exit_code, 0)
        mock_print.assert_called_once_with(
            json.dumps(
                {
                    "patient_id": "30010096",
                    "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                    "paths": [],
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    unittest.main()
