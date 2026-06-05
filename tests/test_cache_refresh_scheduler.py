"""Tests for FastAPI user-cache refresh job scheduling helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.similar_user.api.cache_cleanup_scheduler import _nonblocking_file_lock
from src.similar_user.api.cache_refresh_scheduler import _refresh_jobs_once_with_lock


class CacheRefreshSchedulerTest(unittest.TestCase):
    def test_refresh_jobs_once_with_lock_runs_batch(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_config(root)

            with patch(
                "src.similar_user.api.cache_refresh_scheduler.refresh_user_cache_jobs",
                return_value={"completed_jobs": 2},
            ) as mock_refresh:
                _refresh_jobs_once_with_lock(config_path)

        mock_refresh.assert_called_once_with(
            config_path=config_path,
            limit=123,
        )

    def test_refresh_jobs_once_with_lock_skips_when_lock_is_held(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_config(root)
            lock_path = root / "refresh_jobs.lock"

            with (
                _nonblocking_file_lock(lock_path) as acquired,
                patch(
                    "src.similar_user.api.cache_refresh_scheduler.refresh_user_cache_jobs"
                ) as mock_refresh,
            ):
                self.assertTrue(acquired)
                _refresh_jobs_once_with_lock(config_path)

        mock_refresh.assert_not_called()


def _write_config(root: Path) -> Path:
    config_path = root / "settings.yaml"
    config_path.write_text(
        "\n".join(
            [
                "user_cache:",
                "  enabled: true",
                f'  sqlite_path: "{root / "cache_index.sqlite"}"',
                "  refresh_jobs_background_enabled: true",
                "  refresh_jobs_run_hour: 0",
                "  refresh_jobs_run_minute: 30",
                "  refresh_jobs_batch_limit: 123",
                f'  refresh_jobs_lock_path: "{root / "refresh_jobs.lock"}"',
            ]
        ),
        encoding="utf-8",
    )
    return config_path


if __name__ == "__main__":
    unittest.main()
