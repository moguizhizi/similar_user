"""Tests for Neo4j client behavior."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from config.settings import load_neo4j_settings
from scripts.build_pattern_paths import parse_args
from scripts.build_pattern_paths import main as pattern_path_main
from scripts.build_pattern_paths import (
    run_configured_pattern_path_flows,
    run_pattern_path_flow,
)
from scripts.debug_query import main, run_debug_query
from src.similar_user.data_access.neo4j_client import Neo4jClient


class LoadNeo4jSettingsTest(unittest.TestCase):
    def test_load_neo4j_settings_from_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
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
        client = Neo4jClient.from_config("config/settings.yaml")
        settings = load_neo4j_settings("config/settings.yaml")

        client.connect()

        mock_driver_factory.assert_called_once_with(
            settings.uri,
            auth=(settings.username, settings.password),
        )
        mock_driver.verify_connectivity.assert_called_once_with()

    @patch("src.similar_user.data_access.neo4j_client.GraphDatabase.driver")
    def test_run_query_returns_plain_dicts(self, mock_driver_factory: Mock) -> None:
        mock_driver = Mock()
        mock_record = Mock()
        mock_record.data.return_value = {"ok": 1}
        mock_driver.execute_query.return_value = ([mock_record], None, None)
        mock_driver_factory.return_value = mock_driver
        client = Neo4jClient.from_config("config/settings.yaml")

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
        client = Neo4jClient.from_config("config/settings.yaml")

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

    @patch("scripts.debug_query.LOGGER")
    @patch("scripts.debug_query.run_debug_query")
    def test_main_logs_json_on_success(
        self,
        mock_run_debug_query: Mock,
        mock_logger: Mock,
    ) -> None:
        mock_run_debug_query.return_value = [{"ok": 1, "message": "neo4j connected"}]

        exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_logger.info.assert_called_once_with(
            json.dumps(
                [{"ok": 1, "message": "neo4j connected"}],
                ensure_ascii=False,
                indent=2,
            )
        )


class DebugPatternPathsScriptTest(unittest.TestCase):
    @patch(
        "sys.argv",
        [
            "build_pattern_paths.py",
            "--source-id",
            "30010096",
            "--pattern",
            "patient_disease_patient",
            "--base-date",
            "2022-05-22",
            "--window-days",
            "14",
        ],
    )
    def test_parse_args_accepts_registered_pattern_alias(self) -> None:
        args = parse_args()

        self.assertEqual(args.source_id, "30010096")
        self.assertEqual(args.pattern, "patient_disease_patient")

    @patch(
        "sys.argv",
        [
            "build_pattern_paths.py",
            "--source-id",
            "30010096",
            "--pattern",
            "patient_dis_patient",
            "--base-date",
            "2022-05-22",
            "--window-days",
            "14",
        ],
    )
    def test_parse_args_rejects_unregistered_pattern_alias(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args()

    @patch(
        "sys.argv",
        [
            "build_pattern_paths.py",
            "30010096",
            "--pattern",
            "patient_game_patient",
            "--base-date",
            "2022-05-22",
            "--window-days",
            "14",
        ],
    )
    def test_parse_args_rejects_positional_source_id(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args()

    @patch(
        "sys.argv",
        [
            "build_pattern_paths.py",
            "--source-id",
            "30010096",
            "--base-date",
            "2022-05-22",
            "--window-days",
            "14",
        ],
    )
    def test_parse_args_requires_pattern_option(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args()

    @patch(
        "sys.argv",
        [
            "build_pattern_paths.py",
            "--source-id",
            "30010096",
            "--patterns-from-config",
            "--base-date",
            "2022-05-22",
            "--window-days",
            "14",
        ],
    )
    def test_parse_args_accepts_patterns_from_config(self) -> None:
        args = parse_args()

        self.assertEqual(args.source_id, "30010096")
        self.assertTrue(args.patterns_from_config)
        self.assertIsNone(args.pattern)

    @patch(
        "sys.argv",
        [
            "build_pattern_paths.py",
            "--source-id",
            "30010096",
            "--pattern",
            "patient_game_patient",
            "--patterns-from-config",
            "--base-date",
            "2022-05-22",
            "--window-days",
            "14",
        ],
    )
    def test_parse_args_rejects_pattern_with_patterns_from_config(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args()

    @patch("scripts.build_pattern_paths.LOGGER")
    @patch("scripts.build_pattern_paths.save_pattern_result")
    @patch("scripts.build_pattern_paths.Neo4jClient.from_config")
    def test_run_pattern_path_flow_returns_service_result(
        self,
        mock_from_config: Mock,
        mock_save_pattern_result: Mock,
        mock_logger: Mock,
    ) -> None:
        mock_client = Mock()
        mock_from_config.return_value.__enter__.return_value = mock_client
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_service = Mock()
        mock_service.get_pattern_paths.return_value = {
            "source_id": "30010096",
            "source_parameter": "patient_id",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "retrieval_context": None,
        }
        mock_save_pattern_result.return_value = Path(
            "data/pattern_paths/PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT/30/30010096.json"
        )

        with patch(
                "scripts.build_pattern_paths.KgRepository",
            return_value=mock_repository,
        ) as mock_repository_cls, patch(
                "scripts.build_pattern_paths.UserService",
            return_value=mock_service,
        ) as mock_service_cls:
            result = run_pattern_path_flow(
                "30010096",
                base_date="2022-05-22",
                window_days=14,
            )

        self.assertEqual(
            result,
            {
                "source_id": "30010096",
                "source_parameter": "patient_id",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "retrieval_context": None,
            },
        )
        mock_repository_cls.assert_called_once_with(
            client=mock_client,
            config_path=Path("config/settings.yaml"),
        )
        mock_service_cls.assert_called_once_with(kg_repository=mock_repository)
        mock_service.get_pattern_paths.assert_called_once_with(
            "30010096",
            base_date="2022-05-22",
            window_days=14,
            pattern="patient_game_patient",
            query_family="training_order",
        )
        mock_save_pattern_result.assert_called_once_with(
            {
                "source_id": "30010096",
                "source_parameter": "patient_id",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "retrieval_context": None,
            },
            "config/settings.yaml",
        )
        mock_logger.info.assert_called()

    @patch("scripts.build_pattern_paths.save_pattern_result")
    @patch("scripts.build_pattern_paths.Neo4jClient.from_config")
    def test_run_pattern_path_flow_preserves_none_query_family_for_direct_pattern(
        self,
        mock_from_config: Mock,
        mock_save_pattern_result: Mock,
    ) -> None:
        mock_client = Mock()
        mock_from_config.return_value.__enter__.return_value = mock_client
        mock_repository = Mock()
        mock_repository.config_path = "config/settings.yaml"
        mock_service = Mock()
        mock_service.get_pattern_paths.return_value = {
            "source_id": "AU_DIS_0013",
            "source_parameter": "disease_id",
            "pattern": "DISEASE_TASKSET_PATIENT",
            "retrieval_context": None,
        }
        mock_save_pattern_result.return_value = Path(
            "data/pattern_paths/DISEASE_TASKSET_PATIENT/AU/AU_DIS_0013.json"
        )

        with patch(
            "scripts.build_pattern_paths.KgRepository",
            return_value=mock_repository,
        ), patch(
            "scripts.build_pattern_paths.UserService",
            return_value=mock_service,
        ):
            run_pattern_path_flow(
                "AU_DIS_0013",
                base_date="2022-05-22",
                window_days=14,
                pattern="disease_patient",
            )

        mock_service.get_pattern_paths.assert_called_once_with(
            "AU_DIS_0013",
            base_date="2022-05-22",
            window_days=14,
            pattern="disease_patient",
            query_family=None,
        )

    @patch("scripts.build_pattern_paths.run_pattern_path_flow")
    def test_run_configured_pattern_path_flows_uses_yaml_patterns(
        self,
        mock_run_flow: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "candidate_ranking:",
                        "  patterns:",
                        "    - patient_game_patient",
                        "    - patient_disease_patient",
                        "  candidate_top_k: 10",
                    ]
                ),
                encoding="utf-8",
            )
            mock_run_flow.side_effect = [
                {"pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"},
                {"pattern": "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT"},
            ]

            results = run_configured_pattern_path_flows(
                "30010096",
                config_path=config_path,
                base_date="2022-05-22",
                window_days=14,
                query_family="date_window",
            )

        self.assertEqual(
            results,
            [
                {"pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"},
                {"pattern": "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT"},
            ],
        )
        self.assertEqual(mock_run_flow.call_count, 2)
        mock_run_flow.assert_any_call(
            "30010096",
            config_path=config_path,
            base_date="2022-05-22",
            window_days=14,
            pattern="patient_game_patient",
            query_family="date_window",
        )
        mock_run_flow.assert_any_call(
            "30010096",
            config_path=config_path,
            base_date="2022-05-22",
            window_days=14,
            pattern="patient_disease_patient",
            query_family="date_window",
        )

    def test_run_configured_pattern_path_flows_rejects_direct_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "candidate_ranking:",
                        "  patterns:",
                        "    - disease_patient",
                        "  candidate_top_k: 10",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "patient-source patterns"):
                run_configured_pattern_path_flows(
                    "AU_DIS_0013",
                    config_path=config_path,
                    base_date="2022-05-22",
                    window_days=14,
                )

    @patch("scripts.build_pattern_paths.LOGGER")
    @patch("scripts.build_pattern_paths.run_pattern_path_flow")
    @patch("scripts.build_pattern_paths.parse_args")
    def test_main_returns_zero_on_success_without_logging_error(
        self,
        mock_parse_args: Mock,
        mock_run_flow: Mock,
        mock_logger: Mock,
    ) -> None:
        mock_parse_args.return_value = Mock(
            source_id="30010096",
            config="config/settings.yaml",
            base_date="2022-05-22",
            window_days=14,
            pattern="patient_game_patient",
            query_family="date_window",
        )
        mock_run_flow.return_value = {
            "source_id": "30010096",
            "source_parameter": "patient_id",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "retrieval_context": None,
        }

        exit_code = pattern_path_main()

        self.assertEqual(exit_code, 0)
        mock_run_flow.assert_called_once_with(
            "30010096",
            config_path="config/settings.yaml",
            base_date="2022-05-22",
            window_days=14,
            pattern="patient_game_patient",
            query_family="date_window",
        )
        mock_logger.exception.assert_not_called()

    @patch("scripts.build_pattern_paths.LOGGER")
    @patch("scripts.build_pattern_paths.run_configured_pattern_path_flows")
    @patch("scripts.build_pattern_paths.parse_args")
    def test_main_runs_configured_pattern_flows(
        self,
        mock_parse_args: Mock,
        mock_run_configured: Mock,
        mock_logger: Mock,
    ) -> None:
        mock_parse_args.return_value = Mock(
            source_id="30010096",
            config="config/settings.yaml",
            base_date="2022-05-22",
            window_days=14,
            pattern=None,
            patterns_from_config=True,
            query_family="date_window",
        )

        exit_code = pattern_path_main()

        self.assertEqual(exit_code, 0)
        mock_run_configured.assert_called_once_with(
            "30010096",
            config_path="config/settings.yaml",
            base_date="2022-05-22",
            window_days=14,
            query_family="date_window",
        )
        mock_logger.exception.assert_not_called()


if __name__ == "__main__":
    unittest.main()
