"""SQLite-backed cache for direct source-taskset-patient paths."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

from .direct_path_cache_queries import (
    DIRECT_PATH_ALL_SQL_VARIANTS,
    DIRECT_PATH_RANDOMIZED_SQL_VARIANTS,
    direct_path_sql_parameters,
)
from .pattern_registry import QueryDateWindow
from ..domain.graph_schema import PathPattern


DIRECT_PATH_SOURCE_FIELDS: dict[PathPattern, tuple[str, str]] = {
    PathPattern.DISEASE_TASKSET_PATIENT: ("disease", "d"),
    PathPattern.SYMPTOM_TASKSET_PATIENT: ("symptom", "sym"),
    PathPattern.UNKNOWN_TASKSET_PATIENT: ("unknown", "un"),
}


@dataclass(frozen=True)
class DirectPathCacheSyncSummary:
    """Summary for one cache write/sync operation."""

    pattern: str
    input_path_count: int
    stored_path_count: int
    last_synced_training_date: str | None


@dataclass(frozen=True)
class DirectPathCacheRecord:
    """Normalized cache rows split into path and node payloads."""

    path: tuple[object, ...]
    source_node: tuple[object, ...]
    taskset_node: tuple[object, ...]
    patient_node: tuple[object, ...]

    @property
    def training_date(self) -> str:
        """Return the TaskInstanceSet training date used as sync watermark."""
        return str(self.path[5])


class DirectPathCacheStore:
    """Read and write direct pattern paths in a local SQLite database."""

    def __init__(self, sqlite_path: str | Path) -> None:
        self.sqlite_path = Path(sqlite_path)

    @property
    def exists(self) -> bool:
        """Return whether the SQLite file already exists."""
        return self.sqlite_path.exists()

    def initialize(self) -> None:
        """Create cache tables and indexes when missing."""
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            _ensure_no_legacy_direct_paths_table(connection, self.sqlite_path)
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS direct_paths (
                    pattern TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    taskset_id TEXT NOT NULL,
                    patient_id TEXT NOT NULL,
                    training_date TEXT,
                    PRIMARY KEY (
                        pattern,
                        source_type,
                        source_id,
                        taskset_id,
                        patient_id
                    )
                )
                """.strip()
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS source_nodes (
                    source_type TEXT NOT NULL,
                    source_id TEXT NOT NULL,
                    source_json TEXT NOT NULL,
                    PRIMARY KEY (source_type, source_id)
                )
                """.strip()
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS taskset_nodes (
                    taskset_id TEXT PRIMARY KEY,
                    taskset_json TEXT NOT NULL
                )
                """.strip()
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS patient_nodes (
                    patient_id TEXT PRIMARY KEY,
                    patient_json TEXT NOT NULL
                )
                """.strip()
            )
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS direct_path_sync_state (
                    pattern TEXT PRIMARY KEY,
                    last_synced_training_date TEXT,
                    updated_at TEXT NOT NULL
                )
                """.strip()
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_direct_paths_source_window
                ON direct_paths (
                    pattern,
                    source_type,
                    source_id,
                    training_date
                )
                """.strip()
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_direct_paths_window
                ON direct_paths (
                    pattern,
                    source_type,
                    training_date
                )
                """.strip()
            )

    def replace_pattern_paths(
        self,
        pattern: PathPattern,
        rows: Iterable[dict[str, Any]],
    ) -> DirectPathCacheSyncSummary:
        """Replace all cached rows for a pattern and write the supplied rows."""
        self.initialize()
        with self._connect() as connection:
            old_rows = connection.execute(
                """
                SELECT DISTINCT source_type, source_id, taskset_id, patient_id
                FROM direct_paths
                WHERE pattern = ?
                """.strip(),
                (pattern.value,),
            ).fetchall()
            connection.execute(
                "DELETE FROM direct_paths WHERE pattern = ?",
                (pattern.value,),
            )
            connection.execute(
                "DELETE FROM direct_path_sync_state WHERE pattern = ?",
                (pattern.value,),
            )
            self._delete_orphan_nodes(connection, old_rows)
        return self.upsert_paths(pattern, rows)

    def upsert_paths(
        self,
        pattern: PathPattern,
        rows: Iterable[dict[str, Any]],
    ) -> DirectPathCacheSyncSummary:
        """Insert or update cached rows for one direct path pattern."""
        self.initialize()
        records = [_build_cache_record(pattern, row) for row in rows]
        max_training_date = _max_training_date(records)
        with self._connect() as connection:
            connection.executemany(
                """
                INSERT INTO source_nodes (
                    source_type,
                    source_id,
                    source_json
                )
                VALUES (?, ?, ?)
                ON CONFLICT (source_type, source_id)
                DO UPDATE SET
                    source_json = excluded.source_json
                """.strip(),
                [record.source_node for record in records],
            )
            connection.executemany(
                """
                INSERT INTO taskset_nodes (
                    taskset_id,
                    taskset_json
                )
                VALUES (?, ?)
                ON CONFLICT (taskset_id)
                DO UPDATE SET
                    taskset_json = excluded.taskset_json
                """.strip(),
                [record.taskset_node for record in records],
            )
            connection.executemany(
                """
                INSERT INTO patient_nodes (
                    patient_id,
                    patient_json
                )
                VALUES (?, ?)
                ON CONFLICT (patient_id)
                DO UPDATE SET
                    patient_json = excluded.patient_json
                """.strip(),
                [record.patient_node for record in records],
            )
            connection.executemany(
                """
                INSERT INTO direct_paths (
                    pattern,
                    source_type,
                    source_id,
                    taskset_id,
                    patient_id,
                    training_date
                )
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT (
                    pattern,
                    source_type,
                    source_id,
                    taskset_id,
                    patient_id
                )
                DO UPDATE SET
                    training_date = excluded.training_date
                """.strip(),
                [record.path for record in records],
            )
            if max_training_date is not None:
                self._update_last_synced_training_date(
                    connection,
                    pattern,
                    max_training_date,
                )
            stored_row = connection.execute(
                "SELECT count(*) AS path_count FROM direct_paths WHERE pattern = ?",
                (pattern.value,),
            ).fetchone()
            stored_count = int(
                stored_row["path_count"] if stored_row is not None else 0
            )

        return DirectPathCacheSyncSummary(
            pattern=pattern.value,
            input_path_count=len(records),
            stored_path_count=stored_count,
            last_synced_training_date=self.get_last_synced_training_date(pattern),
        )

    def get_paths(
        self,
        pattern: PathPattern,
        source_id: str,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
        one_path_per_patient: bool = True,
    ) -> list[dict[str, Any]]:
        """Return cached paths matching the source ID and optional date window."""
        self.initialize()
        source_type, source_field = _source_contract(pattern)
        date_window = QueryDateWindow(
            start_date=_optional_string(start_date),
            end_date=_optional_string(end_date),
        )
        if one_path_per_patient:
            query = DIRECT_PATH_RANDOMIZED_SQL_VARIANTS.select(date_window)
        else:
            query = DIRECT_PATH_ALL_SQL_VARIANTS.select(date_window)
        parameters = direct_path_sql_parameters(
            pattern=pattern.value,
            source_type=source_type,
            source_id=source_id.strip(),
            window=date_window,
        )

        with self._connect() as connection:
            rows = connection.execute(query, parameters).fetchall()

        return [
            {
                "row": {
                    source_field: json.loads(row["source_json"]),
                    "s": json.loads(row["taskset_json"]),
                    "p": json.loads(row["patient_json"]),
                }
            }
            for row in rows
        ]

    def count_paths(self, pattern: PathPattern) -> int:
        """Return the number of cached paths for a pattern."""
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                "SELECT count(*) AS path_count FROM direct_paths WHERE pattern = ?",
                (pattern.value,),
            ).fetchone()
        return int(row["path_count"] if row is not None else 0)

    def get_last_synced_training_date(self, pattern: PathPattern) -> str | None:
        """Return the stored training-date watermark for a pattern."""
        self.initialize()
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT last_synced_training_date
                FROM direct_path_sync_state
                WHERE pattern = ?
                """.strip(),
                (pattern.value,),
            ).fetchone()
        if row is None:
            return None
        value = row["last_synced_training_date"]
        return str(value) if value is not None else None

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.sqlite_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _update_last_synced_training_date(
        self,
        connection: sqlite3.Connection,
        pattern: PathPattern,
        training_date: str,
    ) -> None:
        connection.execute(
            """
            INSERT INTO direct_path_sync_state (
                pattern,
                last_synced_training_date,
                updated_at
            )
            VALUES (?, ?, ?)
            ON CONFLICT(pattern)
            DO UPDATE SET
                last_synced_training_date = excluded.last_synced_training_date,
                updated_at = excluded.updated_at
            """.strip(),
            (pattern.value, training_date, datetime.utcnow().isoformat()),
        )

    def _delete_orphan_nodes(
        self,
        connection: sqlite3.Connection,
        rows: list[sqlite3.Row],
    ) -> None:
        """Delete nodes no longer referenced after a pattern replacement."""
        for row in rows:
            source_type = row["source_type"]
            source_id = row["source_id"]
            taskset_id = row["taskset_id"]
            patient_id = row["patient_id"]
            if not _path_references_source(connection, source_type, source_id):
                connection.execute(
                    """
                    DELETE FROM source_nodes
                    WHERE source_type = ? AND source_id = ?
                    """.strip(),
                    (source_type, source_id),
                )
            if not _path_references_taskset(connection, taskset_id):
                connection.execute(
                    "DELETE FROM taskset_nodes WHERE taskset_id = ?",
                    (taskset_id,),
                )
            if not _path_references_patient(connection, patient_id):
                connection.execute(
                    "DELETE FROM patient_nodes WHERE patient_id = ?",
                    (patient_id,),
                )


def _build_cache_record(
    pattern: PathPattern,
    row: dict[str, Any],
) -> DirectPathCacheRecord:
    source_type, source_field = _source_contract(pattern)
    payload = row.get("row") if isinstance(row.get("row"), dict) else row
    if not isinstance(payload, dict):
        raise ValueError("direct path row must contain a mapping row.")

    source_node = _require_node(payload.get(source_field), source_field)
    taskset_node = _require_node(payload.get("s"), "s")
    patient_node = _require_node(payload.get("p"), "p")
    source_id = _require_node_id(source_node, source_field)
    taskset_id = _require_node_id(taskset_node, "s")
    patient_id = _require_node_id(patient_node, "p")
    training_date = _optional_string(taskset_node.get("训练日期"))
    if training_date is None:
        raise ValueError("direct path TaskInstanceSet node must define 训练日期.")

    return DirectPathCacheRecord(
        path=(
            pattern.value,
            source_type,
            source_id,
            taskset_id,
            patient_id,
            training_date,
        ),
        source_node=(
            source_type,
            source_id,
            json.dumps(source_node, ensure_ascii=False, sort_keys=True),
        ),
        taskset_node=(
            taskset_id,
            json.dumps(taskset_node, ensure_ascii=False, sort_keys=True),
        ),
        patient_node=(
            patient_id,
            json.dumps(patient_node, ensure_ascii=False, sort_keys=True),
        ),
    )


def _source_contract(pattern: PathPattern) -> tuple[str, str]:
    try:
        return DIRECT_PATH_SOURCE_FIELDS[pattern]
    except KeyError as exc:
        raise ValueError(f"Unsupported direct path cache pattern: {pattern.value}") from exc


def _require_node(value: object, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"direct path row field {field_name} must be a mapping.")
    return value


def _require_node_id(node: dict[str, Any], field_name: str) -> str:
    value = node.get("id")
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"direct path node {field_name}.id must be a non-empty string.")
    return value.strip()


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _max_training_date(records: list[DirectPathCacheRecord]) -> str | None:
    dates = [record.training_date for record in records]
    return max(dates) if dates else None


def _path_references_source(
    connection: sqlite3.Connection,
    source_type: str,
    source_id: str,
) -> bool:
    row = connection.execute(
        """
        SELECT 1 FROM direct_paths
        WHERE source_type = ? AND source_id = ?
        LIMIT 1
        """.strip(),
        (source_type, source_id),
    ).fetchone()
    return row is not None


def _path_references_taskset(
    connection: sqlite3.Connection,
    taskset_id: str,
) -> bool:
    row = connection.execute(
        "SELECT 1 FROM direct_paths WHERE taskset_id = ? LIMIT 1",
        (taskset_id,),
    ).fetchone()
    return row is not None


def _path_references_patient(
    connection: sqlite3.Connection,
    patient_id: str,
) -> bool:
    row = connection.execute(
        "SELECT 1 FROM direct_paths WHERE patient_id = ? LIMIT 1",
        (patient_id,),
    ).fetchone()
    return row is not None


def _ensure_no_legacy_direct_paths_table(
    connection: sqlite3.Connection,
    sqlite_path: Path,
) -> None:
    row = connection.execute(
        """
        SELECT 1
        FROM sqlite_master
        WHERE type = 'table' AND name = 'direct_paths'
        """.strip()
    ).fetchone()
    if row is None:
        return

    columns = {
        column["name"]
        for column in connection.execute("PRAGMA table_info(direct_paths)").fetchall()
    }
    legacy_columns = {"source_json", "taskset_json", "patient_json"}
    if columns & legacy_columns:
        raise ValueError(
            "Existing direct path cache uses the legacy inline-JSON schema. "
            f"Delete or move the SQLite file before rebuilding: {sqlite_path}"
        )
