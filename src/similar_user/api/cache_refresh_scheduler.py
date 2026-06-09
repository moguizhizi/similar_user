"""Background scheduling for user-cache refresh jobs in FastAPI workers."""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config.settings import DEFAULT_CONFIG_PATH, load_user_cache_settings
from scripts.refresh_user_cache_jobs import refresh_user_cache_jobs
from similar_user.utils.logger import get_logger

from .cache_cleanup_scheduler import (
    _nonblocking_file_lock,
    seconds_until_next_daily_run,
)


LOGGER = get_logger(__name__)


async def run_user_cache_refresh_jobs_daily(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> None:
    """Run queued user-cache refresh jobs once per day at the configured time."""
    settings = load_user_cache_settings(config_path)
    if not settings.refresh_jobs_background_enabled:
        LOGGER.info("User cache background refresh jobs are disabled.")
        return

    while True:
        sleep_seconds = seconds_until_next_daily_run(
            now=datetime.now(tz=ZoneInfo("UTC")),
            hour=settings.refresh_jobs_run_hour,
            minute=settings.refresh_jobs_run_minute,
            timezone_name=settings.cleanup_timezone,
        )
        LOGGER.info(
            "Next user cache refresh jobs run is scheduled in %.0f seconds at %02d:%02d %s.",
            sleep_seconds,
            settings.refresh_jobs_run_hour,
            settings.refresh_jobs_run_minute,
            settings.cleanup_timezone,
        )
        await asyncio.sleep(sleep_seconds)
        try:
            await asyncio.to_thread(_refresh_jobs_once_with_lock, config_path)
        except Exception as exc:
            LOGGER.exception("Scheduled user cache refresh jobs failed: %s", exc)


def _refresh_jobs_once_with_lock(config_path: str | Path) -> None:
    """Run one refresh-job batch if no other FastAPI worker holds the lock."""
    settings = load_user_cache_settings(config_path)
    lock_path = Path(settings.refresh_jobs_lock_path)
    with _nonblocking_file_lock(lock_path) as acquired:
        if not acquired:
            LOGGER.info(
                "Skipped user cache refresh jobs because another worker holds lock: %s",
                lock_path,
            )
            return
        summary = refresh_user_cache_jobs(
            config_path=config_path,
            limit=settings.refresh_jobs_batch_limit,
        )
        LOGGER.info("Completed scheduled user cache refresh jobs: %s", summary)
