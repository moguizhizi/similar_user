"""Tests for FastAPI user-cache cleanup scheduling helpers."""

from __future__ import annotations

from datetime import datetime, timezone
import tempfile
import unittest
from pathlib import Path

from src.similar_user.api.cache_cleanup_scheduler import (
    _nonblocking_file_lock,
    seconds_until_next_daily_run,
)


class CacheCleanupSchedulerTest(unittest.TestCase):
    def test_seconds_until_next_daily_run_uses_beijing_time(self) -> None:
        seconds = seconds_until_next_daily_run(
            now=datetime(2026, 6, 2, 16, 30, tzinfo=timezone.utc),
            hour=1,
            minute=0,
            timezone_name="Asia/Shanghai",
        )

        self.assertEqual(seconds, 30 * 60)

    def test_seconds_until_next_daily_run_rolls_to_next_day(self) -> None:
        seconds = seconds_until_next_daily_run(
            now=datetime(2026, 6, 2, 17, 30, tzinfo=timezone.utc),
            hour=1,
            minute=0,
            timezone_name="Asia/Shanghai",
        )

        self.assertEqual(seconds, 23.5 * 60 * 60)

    def test_nonblocking_file_lock_allows_only_one_holder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            lock_path = Path(temp_dir) / "cache" / "cleanup.lock"
            with _nonblocking_file_lock(lock_path) as first_acquired:
                with _nonblocking_file_lock(lock_path) as second_acquired:
                    self.assertTrue(first_acquired)
                    self.assertFalse(second_acquired)


if __name__ == "__main__":
    unittest.main()
