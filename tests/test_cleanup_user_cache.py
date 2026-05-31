"""Tests for source-centered user cache cleanup."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.cleanup_user_cache import cleanup_user_cache
from src.similar_user.data_access.user_cache_index import (
    UserCacheEntry,
    UserCacheIndexStore,
)


class CleanupUserCacheTest(unittest.TestCase):
    def test_cleanup_user_cache_deletes_old_indexed_files_but_keeps_recent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_config(root)
            store = UserCacheIndexStore(root / "user_cache" / "cache.sqlite")
            old_detail = root / "cache" / "old.detail.json"
            old_summary = root / "cache" / "old.summary.json"
            recent_detail = root / "cache" / "recent.detail.json"
            kept_detail = root / "cache" / "kept.detail.json"
            for path in (old_detail, old_summary, recent_detail, kept_detail):
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}", encoding="utf-8")

            old_entry = store.upsert_entry(
                _entry(
                    cached_base_date="2026-04-01",
                    data_path=str(old_detail),
                    summary_path=str(old_summary),
                )
            )
            recent_entry = store.upsert_entry(
                _entry(
                    cached_base_date="2026-05-25",
                    data_path=str(recent_detail),
                )
            )
            kept_entry = store.upsert_entry(
                _entry(
                    cached_base_date="2026-05-20",
                    data_path=str(kept_detail),
                )
            )

            summary = cleanup_user_cache(
                config_path=config_path,
                as_of_date="2026-05-31",
            )
            entries = store.list_entries()

            self.assertEqual(summary["scanned_entries"], 3)
            self.assertEqual(summary["candidate_entries"], 1)
            self.assertEqual(summary["deleted_entries"], 1)
            self.assertEqual(summary["deleted_files"], 2)
            self.assertFalse(old_detail.exists())
            self.assertFalse(old_summary.exists())
            self.assertTrue(recent_detail.exists())
            self.assertTrue(kept_detail.exists())
            self.assertNotIn(old_entry.data_path, {entry.data_path for entry in entries})
            self.assertIn(recent_entry.data_path, {entry.data_path for entry in entries})
            self.assertIn(kept_entry.data_path, {entry.data_path for entry in entries})

    def test_cleanup_user_cache_dry_run_keeps_files_and_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_config(root)
            store = UserCacheIndexStore(root / "user_cache" / "cache.sqlite")
            detail = root / "cache" / "old.detail.json"
            detail.parent.mkdir(parents=True, exist_ok=True)
            detail.write_text("{}", encoding="utf-8")
            store.upsert_entry(
                _entry(
                    cached_base_date="2026-04-01",
                    data_path=str(detail),
                )
            )
            for index, cached_base_date in enumerate(("2026-05-25", "2026-05-20")):
                recent = root / "cache" / f"recent-{index}.detail.json"
                recent.write_text("{}", encoding="utf-8")
                store.upsert_entry(
                    _entry(
                        cached_base_date=cached_base_date,
                        data_path=str(recent),
                    )
                )

            summary = cleanup_user_cache(
                config_path=config_path,
                dry_run=True,
                as_of_date="2026-05-31",
            )
            entries = store.list_entries()

            self.assertEqual(summary["candidate_entries"], 1)
            self.assertEqual(summary["deleted_entries"], 1)
            self.assertTrue(detail.exists())
            self.assertEqual(len(entries), 3)


def _write_config(root: Path) -> Path:
    config_path = root / "settings.yaml"
    config_path.write_text(
        "\n".join(
            [
                "user_cache:",
                "  enabled: true",
                f'  sqlite_path: "{root / "user_cache" / "cache.sqlite"}"',
                "  cleanup_max_age_days: 30",
                "  keep_latest_per_source: 2",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _entry(
    *,
    cached_base_date: str,
    data_path: str,
    summary_path: str | None = None,
) -> UserCacheEntry:
    payload = {"candidate_key": "candidate"}
    if summary_path is not None:
        payload["summary_path"] = summary_path
    return UserCacheEntry(
        cache_type="topk_candidates",
        patient_id="30012345",
        source_type="patient",
        source_id="30012345",
        query_family="training_order_dual_window",
        window_days=90,
        config_hash="abc12345",
        cached_base_date=cached_base_date,
        valid_days=7,
        data_path=data_path,
        payload=payload,
    )


if __name__ == "__main__":
    unittest.main()
