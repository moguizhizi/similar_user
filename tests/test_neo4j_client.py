"""Tests for Neo4j client behavior."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from config.settings import load_neo4j_settings
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


if __name__ == "__main__":
    unittest.main()
