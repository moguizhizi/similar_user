"""Import legacy pattern path JSON files into the source-centered user cache.

This migrates files produced under ``data/pattern_paths/<path_key>/...`` into
the user cache layout and registers ``raw_paths`` entries in the SQLite cache
index. It does not rebuild paths from Neo4j.

Example:

    python scripts/import_legacy_pattern_paths_to_user_cache.py \
        --source-dir data/pattern_paths/base_2026-05-25_window_14_qf_training_order_dual_window_pathcfg_81f01e6c \
        --config config/settings_window_14.yaml
"""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterator

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import load_yaml_config  # noqa: E402
from similar_user.utils.logger import get_logger  # noqa: E402
from similar_user.utils.pattern_storage import (  # noqa: E402
    PatternResultStore,
    StoredPatternResult,
)


DEFAULT_CONFIG_PATH = Path("config/settings_window_14.yaml")
DEFAULT_SOURCE_DIR = Path(
    "data/pattern_paths/"
    "base_2026-05-25_window_14_qf_training_order_dual_window_pathcfg_81f01e6c"
)
DEFAULT_TARGET_SQLITE_PATH = Path("data/user_cache/cache_index.sqlite")
LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class ImportSummary:
    """Summary returned by one legacy pattern path import."""

    dry_run: bool
    source_dir: str
    config_path: str
    target_sqlite_path: str
    scanned_files: int
    imported_files: int
    failed_files: int
    skipped_files: int


def parse_args() -> argparse.Namespace:
    """Parse CLI args for importing legacy raw path JSON files."""
    parser = argparse.ArgumentParser(
        description=(
            "Import legacy data/pattern_paths JSON files into the main "
            "source-centered user cache."
        )
    )
    parser.add_argument(
        "--source-dir",
        default=str(DEFAULT_SOURCE_DIR),
        help="Legacy path-key directory under data/pattern_paths.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="YAML config used to interpret path metadata.",
    )
    parser.add_argument(
        "--target-sqlite-path",
        default=str(DEFAULT_TARGET_SQLITE_PATH),
        help="Target user-cache SQLite index. Defaults to the main cache.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Read and validate source files without writing cache files or SQLite rows.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Import at most N files. Useful for a small smoke import.",
    )
    parser.add_argument(
        "--stop-on-error",
        action="store_true",
        help="Stop at the first invalid source file instead of continuing.",
    )
    return parser.parse_args()


def import_legacy_pattern_paths_to_user_cache(
    *,
    source_dir: str | Path = DEFAULT_SOURCE_DIR,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    target_sqlite_path: str | Path = DEFAULT_TARGET_SQLITE_PATH,
    dry_run: bool = False,
    limit: int | None = None,
    stop_on_error: bool = False,
) -> dict[str, Any]:
    """Import legacy pattern path JSON files into the user cache."""
    resolved_source_dir = Path(source_dir)
    if not resolved_source_dir.is_dir():
        raise FileNotFoundError(f"Legacy pattern path directory not found: {source_dir}")
    if limit is not None and limit <= 0:
        raise ValueError("limit must be a positive integer when provided.")

    source_files = list(_iter_legacy_json_files(resolved_source_dir, limit=limit))
    effective_config_path = _build_effective_user_cache_config(
        config_path,
        target_sqlite_path=target_sqlite_path,
    )

    imported_files = 0
    failed_files = 0
    skipped_files = 0
    try:
        store = PatternResultStore(effective_config_path)
        for source_file in source_files:
            try:
                result = _load_legacy_result(source_file)
                if dry_run:
                    skipped_files += 1
                    continue
                store.save(result)
                imported_files += 1
            except Exception:
                failed_files += 1
                LOGGER.exception(
                    "Failed to import legacy pattern path file: %s",
                    source_file,
                )
                if stop_on_error:
                    raise
    finally:
        if effective_config_path != Path(config_path):
            effective_config_path.unlink(missing_ok=True)

    summary = ImportSummary(
        dry_run=dry_run,
        source_dir=str(resolved_source_dir),
        config_path=str(config_path),
        target_sqlite_path=str(target_sqlite_path),
        scanned_files=len(source_files),
        imported_files=imported_files,
        failed_files=failed_files,
        skipped_files=skipped_files,
    )
    LOGGER.info("Completed legacy pattern path user-cache import: %s", summary)
    return asdict(summary)


def _iter_legacy_json_files(source_dir: Path, *, limit: int | None) -> Iterator[Path]:
    yielded = 0
    for path in sorted(source_dir.rglob("*.json")):
        if not path.is_file():
            continue
        yield path
        yielded += 1
        if limit is not None and yielded >= limit:
            return


def _load_legacy_result(path: Path) -> StoredPatternResult:
    with path.open("r", encoding="utf-8") as file:
        payload = json.load(file)
    if not isinstance(payload, dict):
        raise ValueError(f"Legacy pattern path JSON must contain an object: {path}")
    return StoredPatternResult.from_dict(payload)


def _build_effective_user_cache_config(
    config_path: str | Path,
    *,
    target_sqlite_path: str | Path,
) -> Path:
    """Create a temporary config with user_cache enabled for the target index."""
    base_config = load_yaml_config(config_path)
    user_cache_config = base_config.get("user_cache")
    if user_cache_config is None:
        user_cache_config = {}
    if not isinstance(user_cache_config, dict):
        raise ValueError("user_cache config section must be a mapping.")
    base_config["user_cache"] = {
        **user_cache_config,
        "enabled": True,
        "sqlite_path": str(target_sqlite_path),
    }

    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        prefix="similar_user_cache_import_",
        suffix=".yaml",
        delete=False,
    ) as temp_file:
        yaml.safe_dump(base_config, temp_file, allow_unicode=True, sort_keys=False)
        return Path(temp_file.name)


def main() -> None:
    """CLI entrypoint."""
    args = parse_args()
    summary = import_legacy_pattern_paths_to_user_cache(
        source_dir=args.source_dir,
        config_path=args.config,
        target_sqlite_path=args.target_sqlite_path,
        dry_run=args.dry_run,
        limit=args.limit,
        stop_on_error=args.stop_on_error,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
