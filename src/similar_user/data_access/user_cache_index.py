"""SQLite index for source-centered pipeline cache entries."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


SUPPORTED_USER_CACHE_TYPES = frozenset(
    {
        "raw_paths",
        "scored_paths",
        "scored_direct_entity_paths",
        "topk_candidates",
        "profile_candidate_tasks",
    }
)
SQLITE_BUSY_TIMEOUT_SECONDS = 30.0
SQLITE_BUSY_TIMEOUT_MILLISECONDS = int(SQLITE_BUSY_TIMEOUT_SECONDS * 1000)


@dataclass(frozen=True)
class UserCacheEntry:
    """One source-centered cache index entry."""

    cache_type: str
    patient_id: str
    query_family: str
    window_days: int
    config_hash: str
    cached_base_date: str
    valid_days: int
    data_path: str
    payload: dict[str, Any]
    created_at: str | None = None
    updated_at: str | None = None
    source_type: str = "patient"
    source_id: str | None = None

    def is_valid_for(self, request_base_date: str) -> bool:
        """Return whether the entry can be reused for request_base_date."""
        request_date = _parse_iso_date(request_base_date, "request_base_date")
        cached_date = _parse_iso_date(self.cached_base_date, "cached_base_date")
        return timedelta(days=0) <= request_date - cached_date <= timedelta(
            days=self.valid_days
        )


@dataclass(frozen=True)
class UserCacheLookupResult:
    """One reusable cache lookup result and its freshness state."""

    entry: UserCacheEntry
    state: str


class UserCacheIndexStore:
    """Read and write source-centered cache index entries."""

    def __init__(self, sqlite_path: str | Path) -> None:
        self.sqlite_path = Path(sqlite_path)

    @property
    def exists(self) -> bool:
        """Return whether the SQLite index file already exists."""
        return self.sqlite_path.exists()

    def initialize(self) -> None:
        """Create cache index tables and indexes when missing."""
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS user_cache_entries (
                    cache_type TEXT NOT NULL,
                    patient_id TEXT NOT NULL,
                    source_type TEXT NOT NULL DEFAULT 'patient',
                    source_id TEXT NOT NULL DEFAULT '',
                    query_family TEXT NOT NULL,
                    window_days INTEGER NOT NULL,
                    config_hash TEXT NOT NULL,
                    cached_base_date TEXT NOT NULL,
                    valid_days INTEGER NOT NULL,
                    data_path TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (
                        cache_type,
                        patient_id,
                        query_family,
                        window_days,
                        config_hash,
                        cached_base_date,
                        data_path
                    )
                )
                """.strip()
            )
            self._ensure_source_columns(connection)
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_cache_lookup
                ON user_cache_entries (
                    cache_type,
                    patient_id,
                    query_family,
                    window_days,
                    config_hash,
                    cached_base_date
                )
                """.strip()
            )
            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_user_cache_source_lookup
                ON user_cache_entries (
                    cache_type,
                    source_type,
                    source_id,
                    query_family,
                    window_days,
                    config_hash,
                    cached_base_date
                )
                """.strip()
            )

    def upsert_entry(self, entry: UserCacheEntry) -> UserCacheEntry:
        """Insert or update one cache index entry."""
        normalized = _normalize_entry(entry)
        self.initialize()
        now = _utc_now()
        created_at = normalized.created_at or now
        updated_at = now
        payload_json = json.dumps(
            normalized.payload,
            ensure_ascii=False,
            sort_keys=True,
            default=str,
        )
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO user_cache_entries (
                    cache_type,
                    patient_id,
                    source_type,
                    source_id,
                    query_family,
                    window_days,
                    config_hash,
                    cached_base_date,
                    valid_days,
                    data_path,
                    payload_json,
                    created_at,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (
                    cache_type,
                    patient_id,
                    query_family,
                    window_days,
                    config_hash,
                    cached_base_date,
                    data_path
                )
                DO UPDATE SET
                    source_type = excluded.source_type,
                    source_id = excluded.source_id,
                    valid_days = excluded.valid_days,
                    payload_json = excluded.payload_json,
                    updated_at = excluded.updated_at
                """.strip(),
                (
                    normalized.cache_type,
                    normalized.patient_id,
                    normalized.source_type,
                    normalized.source_id,
                    normalized.query_family,
                    normalized.window_days,
                    normalized.config_hash,
                    normalized.cached_base_date,
                    normalized.valid_days,
                    normalized.data_path,
                    payload_json,
                    created_at,
                    updated_at,
                ),
            )
        return UserCacheEntry(
            cache_type=normalized.cache_type,
            patient_id=normalized.patient_id,
            query_family=normalized.query_family,
            window_days=normalized.window_days,
            config_hash=normalized.config_hash,
            cached_base_date=normalized.cached_base_date,
            valid_days=normalized.valid_days,
            data_path=normalized.data_path,
            payload=normalized.payload,
            created_at=created_at,
            updated_at=updated_at,
            source_type=normalized.source_type,
            source_id=normalized.source_id,
        )

    def find_latest_valid_source_entry(
        self,
        *,
        cache_type: str,
        source_type: str,
        source_id: str,
        query_family: str,
        window_days: int,
        config_hash: str,
        request_base_date: str,
    ) -> UserCacheEntry | None:
        """Return the newest unexpired entry matching source and config."""
        if not self.exists:
            return None
        self.initialize()
        normalized_cache_type = _normalize_cache_type(cache_type)
        normalized_source_type = _normalize_required_text(source_type, "source_type")
        normalized_source_id = _normalize_required_text(source_id, "source_id")
        normalized_query_family = _normalize_required_text(query_family, "query_family")
        normalized_window_days = _normalize_positive_int(window_days, "window_days")
        normalized_config_hash = _normalize_required_text(config_hash, "config_hash")
        request_date = _parse_iso_date(request_base_date, "request_base_date")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM user_cache_entries
                WHERE cache_type = ?
                  AND source_type = ?
                  AND source_id = ?
                  AND query_family = ?
                  AND window_days = ?
                  AND config_hash = ?
                  AND cached_base_date <= ?
                ORDER BY cached_base_date DESC, updated_at DESC
                """.strip(),
                (
                    normalized_cache_type,
                    normalized_source_type,
                    normalized_source_id,
                    normalized_query_family,
                    normalized_window_days,
                    normalized_config_hash,
                    request_date.isoformat(),
                ),
            ).fetchall()
        for row in rows:
            entry = _entry_from_row(row)
            if entry.is_valid_for(request_date.isoformat()):
                return entry
        return None

    def find_latest_reusable_source_entry(
        self,
        *,
        cache_type: str,
        source_type: str,
        source_id: str,
        query_family: str,
        window_days: int,
        config_hash: str,
        request_base_date: str,
        stale_valid_days: int,
    ) -> UserCacheLookupResult | None:
        """Return the newest fresh or stale entry matching source and config."""
        if not self.exists:
            return None
        self.initialize()
        normalized_cache_type = _normalize_cache_type(cache_type)
        normalized_source_type = _normalize_required_text(source_type, "source_type")
        normalized_source_id = _normalize_required_text(source_id, "source_id")
        normalized_query_family = _normalize_required_text(query_family, "query_family")
        normalized_window_days = _normalize_positive_int(window_days, "window_days")
        normalized_config_hash = _normalize_required_text(config_hash, "config_hash")
        normalized_stale_valid_days = _normalize_non_negative_int(
            stale_valid_days,
            "stale_valid_days",
        )
        request_date = _parse_iso_date(request_base_date, "request_base_date")
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM user_cache_entries
                WHERE cache_type = ?
                  AND source_type = ?
                  AND source_id = ?
                  AND query_family = ?
                  AND window_days = ?
                  AND config_hash = ?
                  AND cached_base_date <= ?
                ORDER BY cached_base_date DESC, updated_at DESC
                """.strip(),
                (
                    normalized_cache_type,
                    normalized_source_type,
                    normalized_source_id,
                    normalized_query_family,
                    normalized_window_days,
                    normalized_config_hash,
                    request_date.isoformat(),
                ),
            ).fetchall()
        for row in rows:
            entry = _entry_from_row(row)
            age = request_date - _parse_iso_date(
                entry.cached_base_date,
                "cached_base_date",
            )
            if age < timedelta(days=0):
                continue
            if age <= timedelta(days=entry.valid_days):
                return UserCacheLookupResult(entry=entry, state="fresh")
            if age <= timedelta(days=normalized_stale_valid_days):
                return UserCacheLookupResult(entry=entry, state="stale")
        return None

    def list_entries(self) -> list[UserCacheEntry]:
        """Return all indexed cache entries ordered by source and cached date."""
        if not self.exists:
            return []
        self.initialize()
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT *
                FROM user_cache_entries
                ORDER BY
                    cache_type,
                    source_type,
                    source_id,
                    query_family,
                    window_days,
                    config_hash,
                    cached_base_date DESC,
                    updated_at DESC
                """.strip()
            ).fetchall()
        return [_entry_from_row(row) for row in rows]

    def delete_entry(self, entry: UserCacheEntry) -> int:
        """Delete a single cache index entry and return affected row count."""
        normalized = _normalize_entry(entry)
        if not self.exists:
            return 0
        with self._connect() as connection:
            cursor = connection.execute(
                """
                DELETE FROM user_cache_entries
                WHERE cache_type = ?
                  AND patient_id = ?
                  AND query_family = ?
                  AND window_days = ?
                  AND config_hash = ?
                  AND cached_base_date = ?
                  AND data_path = ?
                """.strip(),
                (
                    normalized.cache_type,
                    normalized.patient_id,
                    normalized.query_family,
                    normalized.window_days,
                    normalized.config_hash,
                    normalized.cached_base_date,
                    normalized.data_path,
                ),
            )
            return int(cursor.rowcount)

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(
            self.sqlite_path,
            timeout=SQLITE_BUSY_TIMEOUT_SECONDS,
        )
        connection.execute(f"PRAGMA busy_timeout = {SQLITE_BUSY_TIMEOUT_MILLISECONDS}")
        connection.row_factory = sqlite3.Row
        return connection

    def _ensure_source_columns(self, connection: sqlite3.Connection) -> None:
        columns = {
            str(row["name"])
            for row in connection.execute("PRAGMA table_info(user_cache_entries)")
        }
        if "source_type" not in columns:
            connection.execute(
                "ALTER TABLE user_cache_entries ADD COLUMN source_type TEXT NOT NULL DEFAULT 'patient'"
            )
        if "source_id" not in columns:
            connection.execute(
                "ALTER TABLE user_cache_entries ADD COLUMN source_id TEXT NOT NULL DEFAULT ''"
            )
            connection.execute(
                "UPDATE user_cache_entries SET source_id = patient_id WHERE source_id = ''"
            )


def _normalize_entry(entry: UserCacheEntry) -> UserCacheEntry:
    normalized_patient_id = _normalize_required_text(entry.patient_id, "patient_id")
    normalized_source_id = _normalize_required_text(
        entry.source_id or normalized_patient_id,
        "source_id",
    )
    return UserCacheEntry(
        cache_type=_normalize_cache_type(entry.cache_type),
        patient_id=normalized_patient_id,
        query_family=_normalize_required_text(entry.query_family, "query_family"),
        window_days=_normalize_positive_int(entry.window_days, "window_days"),
        config_hash=_normalize_required_text(entry.config_hash, "config_hash"),
        cached_base_date=_parse_iso_date(
            entry.cached_base_date,
            "cached_base_date",
        ).isoformat(),
        valid_days=_normalize_non_negative_int(entry.valid_days, "valid_days"),
        data_path=_normalize_required_text(entry.data_path, "data_path"),
        payload=dict(entry.payload),
        created_at=entry.created_at,
        updated_at=entry.updated_at,
        source_type=_normalize_required_text(entry.source_type, "source_type"),
        source_id=normalized_source_id,
    )


def _entry_from_row(row: sqlite3.Row) -> UserCacheEntry:
    payload = json.loads(row["payload_json"])
    if not isinstance(payload, dict):
        raise ValueError("user cache payload_json must decode to an object.")
    return UserCacheEntry(
        cache_type=str(row["cache_type"]),
        patient_id=str(row["patient_id"]),
        query_family=str(row["query_family"]),
        window_days=int(row["window_days"]),
        config_hash=str(row["config_hash"]),
        cached_base_date=str(row["cached_base_date"]),
        valid_days=int(row["valid_days"]),
        data_path=str(row["data_path"]),
        payload=payload,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
        source_type=str(row["source_type"]) if "source_type" in row.keys() else "patient",
        source_id=(
            str(row["source_id"])
            if "source_id" in row.keys() and row["source_id"]
            else str(row["patient_id"])
        ),
    )


def _normalize_cache_type(value: str) -> str:
    normalized = _normalize_required_text(value, "cache_type")
    if normalized not in SUPPORTED_USER_CACHE_TYPES:
        supported = ", ".join(sorted(SUPPORTED_USER_CACHE_TYPES))
        raise ValueError(f"cache_type must be one of: {supported}.")
    return normalized


def _normalize_required_text(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _normalize_positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _normalize_non_negative_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _parse_iso_date(value: str, field_name: str) -> date:
    text = _normalize_required_text(value, field_name)
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO date.") from exc


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
