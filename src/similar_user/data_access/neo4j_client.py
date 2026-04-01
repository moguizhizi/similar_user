"""Neo4j client wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase
from neo4j.exceptions import Neo4jError

from config.settings import Neo4jSettings, load_neo4j_settings


@dataclass
class Neo4jClient:
    """Thin wrapper around the official Neo4j driver."""

    settings: Neo4jSettings
    driver: Any | None = None

    @classmethod
    def from_config(cls, config_path: str | Path) -> "Neo4jClient":
        """Build a client from a YAML config file."""
        settings = load_neo4j_settings(config_path)
        return cls(settings=settings)

    def connect(self) -> None:
        """Create the Neo4j driver and verify connectivity eagerly."""
        if self.driver is not None:
            return

        self.driver = GraphDatabase.driver(
            self.settings.uri,
            auth=(self.settings.username, self.settings.password),
        )
        try:
            self.driver.verify_connectivity()
        except Exception:
            self.close()
            raise

    def close(self) -> None:
        """Close the underlying driver."""
        if self.driver is not None:
            self.driver.close()
            self.driver = None

    def health_check(self) -> bool:
        """Return True when the database is reachable and queryable."""
        self.connect()
        result = self.run_query("RETURN 1 AS ok")
        return bool(result and result[0].get("ok") == 1)

    def run_query(
        self,
        query: str,
        parameters: dict[str, Any] | None = None,
        database: str | None = None,
    ) -> list[dict[str, Any]]:
        """Run a read query and return plain dictionaries."""
        self.connect()
        target_database = database or self.settings.database

        try:
            records, _, _ = self.driver.execute_query(
                query,
                parameters_=parameters or {},
                database_=target_database,
            )
        except Neo4jError as exc:
            raise RuntimeError(f"Neo4j query failed: {exc.message}") from exc

        return [record.data() for record in records]

    def __enter__(self) -> "Neo4jClient":
        self.connect()
        return self

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self.close()
