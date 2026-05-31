"""Clean old source-centered user cache entries.

The cleanup is intentionally conservative: it only deletes files referenced by
the SQLite user-cache index, then removes the corresponding index rows.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import DEFAULT_CONFIG_PATH, load_user_cache_settings  # noqa: E402
from similar_user.data_access.user_cache_index import (  # noqa: E402
    UserCacheEntry,
    UserCacheIndexStore,
)
from similar_user.utils.logger import get_logger  # noqa: E402


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class CleanupSummary:
    """Summary returned by one cleanup run."""

    dry_run: bool
    sqlite_path: str
    as_of_date: str
    max_age_days: int
    keep_latest_per_source: int
    scanned_entries: int
    protected_entries: int
    candidate_entries: int
    deleted_entries: int
    deleted_files: int
    missing_files: int
    pruned_dirs: int


def parse_args() -> argparse.Namespace:
    """Parse CLI args for user cache cleanup."""
    parser = argparse.ArgumentParser(
        description="Delete old files referenced by the source-centered user cache index."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be deleted without deleting files or index rows.",
    )
    parser.add_argument(
        "--as-of-date",
        default=date.today().isoformat(),
        help="Date used to evaluate cache age. Defaults to today.",
    )
    parser.add_argument(
        "--max-age-days",
        type=int,
        help="Override user_cache.cleanup_max_age_days.",
    )
    parser.add_argument(
        "--keep-latest-per-source",
        type=int,
        help="Override user_cache.keep_latest_per_source.",
    )
    return parser.parse_args()


def cleanup_user_cache(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    dry_run: bool = False,
    as_of_date: str | None = None,
    max_age_days: int | None = None,
    keep_latest_per_source: int | None = None,
) -> dict[str, Any]:
    """Delete old indexed cache files and their index rows."""
    settings = load_user_cache_settings(config_path)
    resolved_as_of_date = _parse_date(as_of_date or date.today().isoformat(), "as_of_date")
    resolved_max_age_days = _resolve_non_negative_int(
        max_age_days,
        settings.cleanup_max_age_days,
        "max_age_days",
    )
    resolved_keep_latest = _resolve_positive_int(
        keep_latest_per_source,
        settings.keep_latest_per_source,
        "keep_latest_per_source",
    )
    store = UserCacheIndexStore(settings.sqlite_path)
    entries = store.list_entries()
    protected = _protected_entry_keys(entries, keep_latest_per_source=resolved_keep_latest)
    candidates = [
        entry
        for entry in entries
        if _entry_key(entry) not in protected
        and _is_older_than(
            entry.cached_base_date,
            as_of_date=resolved_as_of_date,
            max_age_days=resolved_max_age_days,
        )
    ]

    deleted_entries = 0
    deleted_files = 0
    missing_files = 0
    pruned_dirs = 0
    for entry in candidates:
        for path in _entry_file_paths(entry):
            if path.exists():
                if not dry_run:
                    path.unlink()
                    pruned_dirs += _prune_empty_parents(path.parent)
                deleted_files += 1
            else:
                missing_files += 1
        if dry_run:
            deleted_entries += 1
        else:
            deleted_entries += store.delete_entry(entry)

    summary = CleanupSummary(
        dry_run=dry_run,
        sqlite_path=str(settings.sqlite_path),
        as_of_date=resolved_as_of_date.isoformat(),
        max_age_days=resolved_max_age_days,
        keep_latest_per_source=resolved_keep_latest,
        scanned_entries=len(entries),
        protected_entries=len(protected),
        candidate_entries=len(candidates),
        deleted_entries=deleted_entries,
        deleted_files=deleted_files,
        missing_files=missing_files,
        pruned_dirs=pruned_dirs,
    )
    LOGGER.info("Completed user cache cleanup: %s", summary)
    return asdict(summary)


def _protected_entry_keys(
    entries: list[UserCacheEntry],
    *,
    keep_latest_per_source: int,
) -> set[tuple[str, str]]:
    grouped: dict[tuple[object, ...], list[UserCacheEntry]] = defaultdict(list)
    for entry in entries:
        grouped[_retention_group_key(entry)].append(entry)

    protected: set[tuple[str, str]] = set()
    for group_entries in grouped.values():
        ordered = sorted(
            group_entries,
            key=lambda entry: (entry.cached_base_date, entry.updated_at or ""),
            reverse=True,
        )
        for entry in ordered[:keep_latest_per_source]:
            protected.add(_entry_key(entry))
    return protected


def _retention_group_key(entry: UserCacheEntry) -> tuple[object, ...]:
    return (
        entry.cache_type,
        entry.source_type,
        entry.source_id or entry.patient_id,
        entry.query_family,
        entry.window_days,
        entry.config_hash,
    )


def _entry_key(entry: UserCacheEntry) -> tuple[str, str]:
    return (entry.cached_base_date, entry.data_path)


def _is_older_than(
    cached_base_date: str,
    *,
    as_of_date: date,
    max_age_days: int,
) -> bool:
    cached_date = _parse_date(cached_base_date, "cached_base_date")
    return (as_of_date - cached_date).days > max_age_days


def _entry_file_paths(entry: UserCacheEntry) -> list[Path]:
    paths = [Path(entry.data_path)]
    summary_path = entry.payload.get("summary_path")
    if isinstance(summary_path, str) and summary_path.strip():
        paths.append(Path(summary_path.strip()))
    return _dedupe_paths(paths)


def _dedupe_paths(paths: list[Path]) -> list[Path]:
    seen: set[str] = set()
    result = []
    for path in paths:
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        result.append(path)
    return result


def _prune_empty_parents(path: Path) -> int:
    pruned = 0
    resolved_stop = PROJECT_ROOT.resolve()
    current = path
    while current != current.parent:
        try:
            resolved_current = current.resolve()
        except FileNotFoundError:
            resolved_current = current.parent.resolve() / current.name
        if resolved_current == resolved_stop or resolved_current == resolved_stop.parent:
            break
        try:
            current.rmdir()
        except OSError:
            break
        pruned += 1
        current = current.parent
    return pruned


def _resolve_non_negative_int(
    value: int | None,
    default: int,
    field_name: str,
) -> int:
    resolved = default if value is None else value
    if not isinstance(resolved, int) or isinstance(resolved, bool) or resolved < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return resolved


def _resolve_positive_int(
    value: int | None,
    default: int,
    field_name: str,
) -> int:
    resolved = default if value is None else value
    if not isinstance(resolved, int) or isinstance(resolved, bool) or resolved <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return resolved


def _parse_date(value: str, field_name: str) -> date:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty ISO date.")
    try:
        return date.fromisoformat(value.strip())
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an ISO date.") from exc


def main() -> int:
    """Run user cache cleanup and print JSON summary."""
    args = parse_args()
    try:
        summary = cleanup_user_cache(
            config_path=args.config,
            dry_run=args.dry_run,
            as_of_date=args.as_of_date,
            max_age_days=args.max_age_days,
            keep_latest_per_source=args.keep_latest_per_source,
        )
    except Exception as exc:
        LOGGER.exception("User cache cleanup failed: %s", exc)
        return 1
    LOGGER.info(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
