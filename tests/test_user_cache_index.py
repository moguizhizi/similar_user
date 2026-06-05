"""Tests for source-centered user cache index storage."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from config.settings import load_user_cache_settings
from src.similar_user.data_access.user_cache_index import (
    UserCacheEntry,
    UserCacheIndexStore,
)


class UserCacheSettingsTest(unittest.TestCase):
    def test_load_user_cache_settings_from_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "cache.sqlite"
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "user_cache:",
                        "  enabled: true",
                        f'  sqlite_path: "{sqlite_path}"',
                        "  patient_raw_paths_valid_days: 21",
                        "  direct_raw_paths_valid_days: 60",
                        "  patient_scored_paths_valid_days: 10",
                        "  direct_scored_paths_valid_days: 60",
                        "  topk_candidates_valid_days: 5",
                        "  topk_candidates_stale_valid_days: 9",
                        "  refresh_candidate_base_date_on_hit: false",
                        "  raw_path_build_workers: 2",
                        "  raw_path_build_max_retries: 4",
                        "  raw_path_build_retry_sleep_seconds: 1.5",
                        "  refresh_job_completed_retention_days: 8",
                        "  refresh_job_failed_retention_days: 31",
                        "  cleanup_max_age_days: 21",
                        "  keep_latest_per_source: 3",
                        "  cleanup_background_enabled: true",
                        "  cleanup_run_hour: 1",
                        "  cleanup_run_minute: 0",
                        '  cleanup_timezone: "Asia/Shanghai"',
                        f'  cleanup_lock_path: "{Path(temp_dir) / "cleanup.lock"}"',
                    ]
                ),
                encoding="utf-8",
            )

            settings = load_user_cache_settings(config_path)

            self.assertTrue(settings.enabled)
            self.assertEqual(settings.sqlite_path, str(sqlite_path))
            self.assertEqual(settings.patient_raw_paths_valid_days, 21)
            self.assertEqual(settings.direct_raw_paths_valid_days, 60)
            self.assertEqual(settings.patient_scored_paths_valid_days, 10)
            self.assertEqual(settings.direct_scored_paths_valid_days, 60)
            self.assertEqual(settings.topk_candidates_valid_days, 5)
            self.assertEqual(settings.topk_candidates_stale_valid_days, 9)
            self.assertFalse(settings.refresh_candidate_base_date_on_hit)
            self.assertEqual(settings.raw_path_build_workers, 2)
            self.assertEqual(settings.raw_path_build_max_retries, 4)
            self.assertEqual(settings.raw_path_build_retry_sleep_seconds, 1.5)
            self.assertEqual(settings.refresh_job_completed_retention_days, 8)
            self.assertEqual(settings.refresh_job_failed_retention_days, 31)
            self.assertEqual(settings.cleanup_max_age_days, 21)
            self.assertEqual(settings.keep_latest_per_source, 3)
            self.assertEqual(settings.keep_latest_per_user, 3)
            self.assertTrue(settings.cleanup_background_enabled)
            self.assertEqual(settings.cleanup_run_hour, 1)
            self.assertEqual(settings.cleanup_run_minute, 0)
            self.assertEqual(settings.cleanup_timezone, "Asia/Shanghai")
            self.assertEqual(
                settings.cleanup_lock_path,
                str(Path(temp_dir) / "cleanup.lock"),
            )

    def test_load_user_cache_settings_rejects_invalid_topk_valid_days(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "user_cache:",
                        "  topk_candidates_valid_days: -1",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "topk_candidates_valid_days"):
                load_user_cache_settings(config_path)

    def test_load_user_cache_settings_defaults_stale_topk_days_to_fresh_days(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "user_cache:",
                        "  topk_candidates_valid_days: 6",
                    ]
                ),
                encoding="utf-8",
            )

            settings = load_user_cache_settings(config_path)

        self.assertEqual(settings.topk_candidates_valid_days, 6)
        self.assertEqual(settings.topk_candidates_stale_valid_days, 6)

    def test_load_user_cache_settings_rejects_stale_topk_less_than_fresh(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "user_cache:",
                        "  topk_candidates_valid_days: 7",
                        "  topk_candidates_stale_valid_days: 6",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(
                ValueError,
                "topk_candidates_stale_valid_days",
            ):
                load_user_cache_settings(config_path)


class UserCacheIndexStoreTest(unittest.TestCase):
    def test_find_latest_valid_source_entry_migrates_legacy_index_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "cache.sqlite"
            store = UserCacheIndexStore(sqlite_path)
            with store._connect() as connection:
                connection.execute(
                    """
                    CREATE TABLE user_cache_entries (
                        cache_type TEXT NOT NULL,
                        patient_id TEXT NOT NULL,
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
                connection.execute(
                    """
                    INSERT INTO user_cache_entries (
                        cache_type,
                        patient_id,
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
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """.strip(),
                    (
                        "topk_candidates",
                        "30010096",
                        "training_order_dual_window",
                        14,
                        "cfg",
                        "2026-05-25",
                        7,
                        "detail.json",
                        "{}",
                        "2026-05-25T00:00:00+00:00",
                        "2026-05-25T00:00:00+00:00",
                    ),
                )

            entry = store.find_latest_valid_source_entry(
                cache_type="topk_candidates",
                source_type="patient",
                source_id="30010096",
                query_family="training_order_dual_window",
                window_days=14,
                config_hash="cfg",
                request_base_date="2026-05-26",
            )

        self.assertIsNotNone(entry)
        assert entry is not None
        self.assertEqual(entry.source_type, "patient")
        self.assertEqual(entry.source_id, "30010096")

    def test_find_latest_valid_source_entry_returns_newest_unexpired_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = UserCacheIndexStore(Path(temp_dir) / "cache.sqlite")
            old_entry = _entry(
                cached_base_date="2026-05-20",
                data_path="data/user_cache/30012345/old.json",
            )
            new_entry = _entry(
                cached_base_date="2026-05-25",
                data_path="data/user_cache/30012345/new.json",
            )
            store.upsert_entry(old_entry)
            store.upsert_entry(new_entry)

            found = store.find_latest_valid_source_entry(
                cache_type="topk_candidates",
                source_type="patient",
                source_id="30012345",
                query_family="training_order_dual_window",
                window_days=90,
                config_hash="abc12345",
                request_base_date="2026-05-29",
            )

            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual(found.cached_base_date, "2026-05-25")
            self.assertEqual(found.data_path, "data/user_cache/30012345/new.json")
            self.assertEqual(found.source_type, "patient")
            self.assertEqual(found.source_id, "30012345")

    def test_find_latest_valid_source_entry_matches_non_patient_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = UserCacheIndexStore(Path(temp_dir) / "cache.sqlite")
            store.upsert_entry(
                _entry(
                    cache_type="raw_paths",
                    patient_id="AU_DIS_0029",
                    query_family="direct_entity",
                    window_days=180,
                    config_hash="direct12",
                    cached_base_date="2026-05-25",
                    data_path="data/pattern_paths/direct/D1.json",
                    source_type="disease",
                    source_id="AU_DIS_0029",
                )
            )

            found = store.find_latest_valid_source_entry(
                cache_type="raw_paths",
                source_type="disease",
                source_id="AU_DIS_0029",
                query_family="direct_entity",
                window_days=180,
                config_hash="direct12",
                request_base_date="2026-05-29",
            )

        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.patient_id, "AU_DIS_0029")
        self.assertEqual(found.source_type, "disease")
        self.assertEqual(found.source_id, "AU_DIS_0029")

    def test_find_latest_valid_source_entry_ignores_expired_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = UserCacheIndexStore(Path(temp_dir) / "cache.sqlite")
            store.upsert_entry(
                _entry(
                    cached_base_date="2026-05-20",
                    valid_days=3,
                    data_path="data/user_cache/30012345/expired.json",
                )
            )

            found = store.find_latest_valid_source_entry(
                cache_type="topk_candidates",
                source_type="patient",
                source_id="30012345",
                query_family="training_order_dual_window",
                window_days=90,
                config_hash="abc12345",
                request_base_date="2026-05-29",
            )

            self.assertIsNone(found)

    def test_find_latest_valid_source_entry_requires_matching_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = UserCacheIndexStore(Path(temp_dir) / "cache.sqlite")
            store.upsert_entry(_entry(config_hash="abc12345"))

            found = store.find_latest_valid_source_entry(
                cache_type="topk_candidates",
                source_type="patient",
                source_id="30012345",
                query_family="training_order_dual_window",
                window_days=90,
                config_hash="different",
                request_base_date="2026-05-26",
            )

            self.assertIsNone(found)

    def test_delete_entry_removes_index_row(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = UserCacheIndexStore(Path(temp_dir) / "cache.sqlite")
            entry = store.upsert_entry(_entry())

            self.assertEqual(store.delete_entry(entry), 1)
            self.assertIsNone(
                store.find_latest_valid_source_entry(
                    cache_type="topk_candidates",
                    source_type="patient",
                    source_id="30012345",
                    query_family="training_order_dual_window",
                    window_days=90,
                    config_hash="abc12345",
                    request_base_date="2026-05-26",
                )
            )


def _entry(
    *,
    cache_type: str = "topk_candidates",
    patient_id: str = "30012345",
    query_family: str = "training_order_dual_window",
    window_days: int = 90,
    config_hash: str = "abc12345",
    cached_base_date: str = "2026-05-25",
    valid_days: int = 7,
    data_path: str = "data/user_cache/30012345/topk.json",
    source_type: str = "patient",
    source_id: str | None = None,
) -> UserCacheEntry:
    return UserCacheEntry(
        cache_type=cache_type,
        patient_id=patient_id,
        query_family=query_family,
        window_days=window_days,
        config_hash=config_hash,
        cached_base_date=cached_base_date,
        valid_days=valid_days,
        data_path=data_path,
        payload={
            "candidate_key": "base_2026-05-25_window_90_candcfg_abc12345",
        },
        source_type=source_type,
        source_id=source_id,
    )


if __name__ == "__main__":
    unittest.main()
