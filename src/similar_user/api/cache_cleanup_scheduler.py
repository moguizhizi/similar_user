"""Background scheduling for user-cache cleanup in FastAPI workers."""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from datetime import datetime, timedelta
import fcntl
from pathlib import Path
from typing import Iterator
from zoneinfo import ZoneInfo

from config.settings import DEFAULT_CONFIG_PATH, load_user_cache_settings
from scripts.cleanup_user_cache import cleanup_user_cache
from similar_user.utils.logger import get_logger


LOGGER = get_logger(__name__)


def seconds_until_next_daily_run(
    *,
    now: datetime,
    hour: int,
    minute: int,
    timezone_name: str,
) -> float:
    """Return seconds from now until the next configured local run time."""
    timezone = ZoneInfo(timezone_name)
    localized_now = now.astimezone(timezone)
    next_run = localized_now.replace(
        hour=hour,
        minute=minute,
        second=0,
        microsecond=0,
    )
    if next_run <= localized_now:
        next_run += timedelta(days=1)
    return (next_run - localized_now).total_seconds()


async def run_user_cache_cleanup_daily(config_path: str | Path = DEFAULT_CONFIG_PATH) -> None:
    """Run user-cache cleanup once per day at the configured local time."""
    settings = load_user_cache_settings(config_path)
    if not settings.cleanup_background_enabled:
        LOGGER.info("User cache background cleanup is disabled.")
        return

    while True:
        sleep_seconds = seconds_until_next_daily_run(
            now=datetime.now(tz=ZoneInfo("UTC")),
            hour=settings.cleanup_run_hour,
            minute=settings.cleanup_run_minute,
            timezone_name=settings.cleanup_timezone,
        )
        LOGGER.info(
            "Next user cache cleanup is scheduled in %.0f seconds at %02d:%02d %s.",
            sleep_seconds,
            settings.cleanup_run_hour,
            settings.cleanup_run_minute,
            settings.cleanup_timezone,
        )
        await asyncio.sleep(sleep_seconds)
        try:
            await asyncio.to_thread(_cleanup_once_with_lock, config_path)
        except Exception as exc:
            LOGGER.exception("Scheduled user cache cleanup failed: %s", exc)


def _cleanup_once_with_lock(config_path: str | Path) -> None:
    settings = load_user_cache_settings(config_path)
    lock_path = Path(settings.cleanup_lock_path)
    with _nonblocking_file_lock(lock_path) as acquired:
        if not acquired:
            LOGGER.info(
                "Skipped user cache cleanup because another worker holds lock: %s",
                lock_path,
            )
            return
        summary = cleanup_user_cache(config_path=config_path)
        LOGGER.info("Completed scheduled user cache cleanup: %s", summary)


@contextmanager
def _nonblocking_file_lock(lock_path: Path) -> Iterator[bool]:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+", encoding="utf-8") as lock_file:
        try:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            yield False
            return
        try:
            yield True
        finally:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
