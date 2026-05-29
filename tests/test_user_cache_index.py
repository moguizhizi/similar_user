"""Tests for patient-centered user cache index storage."""

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
                        "  raw_paths_valid_days: 21",
                        "  scored_paths_valid_days: 10",
                        "  topk_candidates_valid_days: 5",
                        "  cleanup_max_age_days: 21",
                        "  keep_latest_per_user: 3",
                    ]
                ),
                encoding="utf-8",
            )

            settings = load_user_cache_settings(config_path)

            self.assertTrue(settings.enabled)
            self.assertEqual(settings.sqlite_path, str(sqlite_path))
            self.assertEqual(settings.raw_paths_valid_days, 21)
            self.assertEqual(settings.scored_paths_valid_days, 10)
            self.assertEqual(settings.topk_candidates_valid_days, 5)
            self.assertEqual(settings.cleanup_max_age_days, 21)
            self.assertEqual(settings.keep_latest_per_user, 3)

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


class UserCacheIndexStoreTest(unittest.TestCase):
    def test_find_latest_valid_entry_returns_newest_unexpired_match(self) -> None:
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

            found = store.find_latest_valid_entry(
                cache_type="topk_candidates",
                patient_id="30012345",
                query_family="training_order_dual_window",
                window_days=90,
                config_hash="abc12345",
                request_base_date="2026-05-29",
            )

            self.assertIsNotNone(found)
            assert found is not None
            self.assertEqual(found.cached_base_date, "2026-05-25")
            self.assertEqual(found.data_path, "data/user_cache/30012345/new.json")

    def test_find_latest_valid_entry_ignores_expired_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = UserCacheIndexStore(Path(temp_dir) / "cache.sqlite")
            store.upsert_entry(
                _entry(
                    cached_base_date="2026-05-20",
                    valid_days=3,
                    data_path="data/user_cache/30012345/expired.json",
                )
            )

            found = store.find_latest_valid_entry(
                cache_type="topk_candidates",
                patient_id="30012345",
                query_family="training_order_dual_window",
                window_days=90,
                config_hash="abc12345",
                request_base_date="2026-05-29",
            )

            self.assertIsNone(found)

    def test_find_latest_valid_entry_requires_matching_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = UserCacheIndexStore(Path(temp_dir) / "cache.sqlite")
            store.upsert_entry(_entry(config_hash="abc12345"))

            found = store.find_latest_valid_entry(
                cache_type="topk_candidates",
                patient_id="30012345",
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
                store.find_latest_valid_entry(
                    cache_type="topk_candidates",
                    patient_id="30012345",
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
    )


if __name__ == "__main__":
    unittest.main()
