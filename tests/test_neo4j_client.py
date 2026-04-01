"""Tests for Neo4j client behavior."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from config.settings import load_neo4j_settings
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


if __name__ == "__main__":
    unittest.main()
