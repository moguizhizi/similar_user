"""Tests for HTTP app behavior."""

from __future__ import annotations

import json
import unittest
from http import HTTPStatus
from unittest.mock import Mock, patch

from src.similar_user.api.app import build_neo4j_health_payload, build_query_payload


class ApiAppTest(unittest.TestCase):
    @patch("src.similar_user.api.app.Neo4jClient.from_config")
    def test_build_neo4j_health_payload_returns_ok_result(
        self,
        mock_from_config: Mock,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"ok": 1, "message": "neo4j connected"}]
        mock_from_config.return_value.__enter__.return_value = mock_client

        payload, status = build_neo4j_health_payload()

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(
            payload,
            {
                "status": "ok",
                "database": "neo4j",
                "result": [{"ok": 1, "message": "neo4j connected"}],
            },
        )

    @patch("src.similar_user.api.app.Neo4jClient.from_config")
    def test_build_neo4j_health_payload_returns_error_detail(
        self,
        mock_from_config: Mock,
    ) -> None:
        mock_from_config.side_effect = RuntimeError("connection failed")

        payload, status = build_neo4j_health_payload()

        self.assertEqual(status, HTTPStatus.SERVICE_UNAVAILABLE)
        self.assertEqual(
            payload,
            {
                "status": "error",
                "database": "neo4j",
                "detail": "connection failed",
            },
        )

    @patch("src.similar_user.api.app.Neo4jClient.from_config")
    def test_build_query_payload_returns_query_result(
        self,
        mock_from_config: Mock,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"name": "Alice"}]
        mock_from_config.return_value.__enter__.return_value = mock_client

        payload, status = build_query_payload(
            json.dumps(
                {
                    "query": "RETURN $name AS name",
                    "parameters": {"name": "Alice"},
                }
            ).encode("utf-8")
        )

        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(
            payload,
            {
                "status": "ok",
                "result": [{"name": "Alice"}],
                "count": 1,
            },
        )
        mock_client.run_query.assert_called_once_with(
            query="RETURN $name AS name",
            parameters={"name": "Alice"},
            database=None,
        )

    def test_build_query_payload_rejects_invalid_json(self) -> None:
        payload, status = build_query_payload(b"{bad json")

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            payload,
            {
                "status": "error",
                "detail": "Request body must be valid UTF-8 JSON.",
            },
        )

    def test_build_query_payload_rejects_blank_query(self) -> None:
        payload, status = build_query_payload(
            json.dumps({"query": "   "}).encode("utf-8")
        )

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            payload,
            {
                "status": "error",
                "detail": "Field 'query' must be a non-empty string.",
            },
        )

    def test_build_query_payload_rejects_non_object_parameters(self) -> None:
        payload, status = build_query_payload(
            json.dumps(
                {
                    "query": "RETURN 1 AS ok",
                    "parameters": ["bad"],
                }
            ).encode("utf-8")
        )

        self.assertEqual(status, HTTPStatus.BAD_REQUEST)
        self.assertEqual(
            payload,
            {
                "status": "error",
                "detail": "Field 'parameters' must be an object when provided.",
            },
        )


class JsonFormatTest(unittest.TestCase):
    def test_payload_can_be_serialized(self) -> None:
        payload = {
            "status": "ok",
            "database": "neo4j",
            "result": [{"ok": 1, "message": "neo4j connected"}],
        }

        body = json.dumps(payload, ensure_ascii=False)

        self.assertIn('"status": "ok"', body)
