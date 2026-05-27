"""Sync direct source-taskset-patient paths from Neo4j into SQLite cache.

Examples:
    python scripts/sync_direct_path_cache.py
    python scripts/sync_direct_path_cache.py --pattern disease_patient
    python scripts/sync_direct_path_cache.py --pattern symptom_patient
    python scripts/sync_direct_path_cache.py --pattern unknown_patient
    python scripts/sync_direct_path_cache.py --pattern disease_patient --force-full-refresh
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import date, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    load_direct_path_cache_settings,
)
from similar_user.data_access.direct_path_cache_store import (  # noqa: E402
    DirectPathCacheStore,
)
from similar_user.data_access.kg_repository import KgRepository  # noqa: E402
from similar_user.data_access.neo4j_client import Neo4jClient  # noqa: E402
from similar_user.data_access.pattern_registry import (  # noqa: E402
    available_path_pattern_aliases,
    resolve_path_pattern,
)
from similar_user.domain.graph_schema import PathPattern  # noqa: E402
from similar_user.utils.logger import get_logger  # noqa: E402


DIRECT_PATTERN_ALIASES = ("disease_patient", "symptom_patient", "unknown_patient")
LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for direct path cache sync."""
    parser = argparse.ArgumentParser(
        description="Sync direct source-taskset-patient paths into SQLite cache."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="YAML config path.",
    )
    parser.add_argument(
        "--pattern",
        choices=available_path_pattern_aliases(),
        default=None,
        help=(
            "Direct path alias to sync. Defaults to disease_patient, "
            "symptom_patient, and unknown_patient."
        ),
    )
    parser.add_argument(
        "--force-full-refresh",
        action="store_true",
        help="Replace cached rows for the selected pattern(s) with a full Neo4j read.",
    )
    args = parser.parse_args()
    if args.pattern is not None:
        pattern = resolve_path_pattern(args.pattern)
        if pattern not in _direct_patterns():
            supported = ", ".join(DIRECT_PATTERN_ALIASES)
            parser.error(f"--pattern must be one of: {supported}")
    return args


def sync_direct_path_cache(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    pattern: str | None = None,
    force_full_refresh: bool = False,
) -> list[dict[str, object]]:
    """Sync direct path cache for one or all direct patterns."""
    settings = load_direct_path_cache_settings(config_path)
    store = DirectPathCacheStore(settings.sqlite_path)
    selected_patterns = _selected_patterns(pattern)
    started_at = time.perf_counter()
    LOGGER.info(
        "Starting direct path cache sync: patterns=%s, sqlite_path=%s, force_full_refresh=%s, incremental_enabled=%s",
        [selected.value for selected in selected_patterns],
        settings.sqlite_path,
        force_full_refresh,
        settings.incremental_enabled,
    )

    with Neo4jClient.from_config(config_path) as client:
        repository = KgRepository(client=client, config_path=Path(config_path))
        summaries = [
            _sync_one_pattern(
                repository=repository,
                store=store,
                pattern=selected_pattern,
                incremental_enabled=settings.incremental_enabled,
                overlap_days=settings.overlap_days,
                force_full_refresh=force_full_refresh,
            )
            for selected_pattern in selected_patterns
        ]

    LOGGER.info(
        "Completed direct path cache sync: pattern_count=%s, elapsed_seconds=%s",
        len(summaries),
        round(time.perf_counter() - started_at, 3),
    )
    return summaries


def _sync_one_pattern(
    *,
    repository: KgRepository,
    store: DirectPathCacheStore,
    pattern: PathPattern,
    incremental_enabled: bool,
    overlap_days: int,
    force_full_refresh: bool,
) -> dict[str, object]:
    store.initialize()
    last_synced_training_date = store.get_last_synced_training_date(pattern)
    start_date = None
    mode = "full_refresh" if force_full_refresh else "full_initial"
    if force_full_refresh:
        rows = repository.get_direct_taskset_patient_cache_paths(pattern)
        summary = store.replace_pattern_paths(pattern, rows)
    elif last_synced_training_date is None:
        rows = repository.get_direct_taskset_patient_cache_paths(pattern)
        summary = store.upsert_paths(pattern, rows)
    else:
        if not incremental_enabled:
            raise ValueError(
                "direct_path_cache incremental_enabled is false; "
                "use --force-full-refresh to rebuild the cache."
            )
        mode = "incremental"
        start_date = _apply_overlap_days(last_synced_training_date, overlap_days)
        rows = repository.get_direct_taskset_patient_cache_paths(
            pattern,
            start_date=start_date,
        )
        summary = store.upsert_paths(pattern, rows)

    result = {
        "pattern": summary.pattern,
        "mode": mode,
        "start_date": start_date,
        "input_path_count": summary.input_path_count,
        "stored_path_count": summary.stored_path_count,
        "last_synced_training_date": summary.last_synced_training_date,
    }
    LOGGER.info(
        "Synced direct path cache: pattern=%s, mode=%s, start_date=%s, input_path_count=%s, stored_path_count=%s, last_synced_training_date=%s",
        result["pattern"],
        result["mode"],
        result["start_date"],
        result["input_path_count"],
        result["stored_path_count"],
        result["last_synced_training_date"],
    )
    return result


def _apply_overlap_days(training_date: str, overlap_days: int) -> str:
    parsed_date = date.fromisoformat(training_date)
    return (parsed_date - timedelta(days=overlap_days)).isoformat()


def _selected_patterns(pattern: str | None) -> tuple[PathPattern, ...]:
    if pattern is None:
        return _direct_patterns()
    return (resolve_path_pattern(pattern),)


def _direct_patterns() -> tuple[PathPattern, ...]:
    return (
        PathPattern.DISEASE_TASKSET_PATIENT,
        PathPattern.SYMPTOM_TASKSET_PATIENT,
        PathPattern.UNKNOWN_TASKSET_PATIENT,
    )


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    try:
        sync_direct_path_cache(
            config_path=args.config,
            pattern=args.pattern,
            force_full_refresh=args.force_full_refresh,
        )
    except Exception:
        LOGGER.exception("Direct path cache sync failed: config_path=%s", args.config)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
