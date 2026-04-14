"""Application entrypoint for HTTP serving."""

from __future__ import annotations

import json
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from ..data_access.neo4j_client import Neo4jClient
from ..utils.logger import get_logger


DEFAULT_CONFIG_PATH = Path("config/neo4j.yaml")
LOGGER = get_logger(__name__)


def build_neo4j_health_payload(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> tuple[dict[str, Any], HTTPStatus]:
    """Build a small health payload based on Neo4j reachability."""
    try:
        with Neo4jClient.from_config(config_path) as client:
            records = client.run_query(
                "RETURN 1 AS ok, 'neo4j connected' AS message"
            )
    except Exception as exc:
        return {
            "status": "error",
            "database": "neo4j",
            "detail": str(exc),
        }, HTTPStatus.SERVICE_UNAVAILABLE

    return {
        "status": "ok",
        "database": "neo4j",
        "result": records,
    }, HTTPStatus.OK


def build_query_payload(
    body: bytes,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> tuple[dict[str, Any], HTTPStatus]:
    """Validate request JSON, run Cypher, and return a response payload."""
    try:
        payload = json.loads(body.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {
            "status": "error",
            "detail": "Request body must be valid UTF-8 JSON.",
        }, HTTPStatus.BAD_REQUEST

    if not isinstance(payload, dict):
        return {
            "status": "error",
            "detail": "Request JSON must be an object.",
        }, HTTPStatus.BAD_REQUEST

    query = payload.get("query")
    parameters = payload.get("parameters", {})
    database = payload.get("database")

    if not isinstance(query, str) or not query.strip():
        return {
            "status": "error",
            "detail": "Field 'query' must be a non-empty string.",
        }, HTTPStatus.BAD_REQUEST

    if not isinstance(parameters, dict):
        return {
            "status": "error",
            "detail": "Field 'parameters' must be an object when provided.",
        }, HTTPStatus.BAD_REQUEST

    if database is not None and not isinstance(database, str):
        return {
            "status": "error",
            "detail": "Field 'database' must be a string when provided.",
        }, HTTPStatus.BAD_REQUEST

    try:
        with Neo4jClient.from_config(config_path) as client:
            records = client.run_query(
                query=query,
                parameters=parameters,
                database=database,
            )
    except Exception as exc:
        return {
            "status": "error",
            "detail": str(exc),
        }, HTTPStatus.BAD_REQUEST

    return {
        "status": "ok",
        "result": records,
        "count": len(records),
    }, HTTPStatus.OK


class SimilarUserRequestHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler for service health endpoints."""

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/health/neo4j":
            self._send_json_response(*build_neo4j_health_payload())
            return

        self._send_json_response(
            {
                "status": "not_found",
                "detail": f"Unsupported path: {self.path}",
            },
            HTTPStatus.NOT_FOUND,
        )

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/query":
            self._send_json_response(
                {
                    "status": "not_found",
                    "detail": f"Unsupported path: {self.path}",
                },
                HTTPStatus.NOT_FOUND,
            )
            return

        content_length = self.headers.get("Content-Length", "0")
        try:
            length = int(content_length)
        except ValueError:
            self._send_json_response(
                {
                    "status": "error",
                    "detail": "Invalid Content-Length header.",
                },
                HTTPStatus.BAD_REQUEST,
            )
            return

        request_body = self.rfile.read(length)
        self._send_json_response(*build_query_payload(request_body))

    def log_message(self, format: str, *args: Any) -> None:
        """Keep default server output quiet during local checks and tests."""
        return None

    def _send_json_response(
        self,
        payload: dict[str, Any],
        status: HTTPStatus,
    ) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run_server(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the local HTTP server."""
    server = ThreadingHTTPServer((host, port), SimilarUserRequestHandler)
    LOGGER.info("Serving on http://%s:%s", host, port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
