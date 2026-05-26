"""Build and persist direct entity-start paths.

This script saves Disease/Symptom/Unknown -> TaskInstanceSet -> Patient paths.
When no source ID is supplied it processes all available direct sources.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    load_direct_path_cache_settings,
    load_query_settings,
)
from similar_user.data_access.direct_path_cache_store import (  # noqa: E402
    DirectPathCacheStore,
)
from similar_user.data_access.kg_repository import KgRepository  # noqa: E402
from similar_user.data_access.neo4j_client import Neo4jClient  # noqa: E402
from similar_user.data_access.pattern_registry import (  # noqa: E402
    get_path_pattern_spec,
)
from similar_user.domain.graph_schema import PathPattern  # noqa: E402
from similar_user.utils.logger import get_logger  # noqa: E402
from similar_user.utils.pattern_storage import (  # noqa: E402
    build_direct_path_cache_context,
    save_direct_pattern_result,
)


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class DirectSourceRequest:
    """One direct entity source to query and save."""

    pattern: PathPattern
    source_id: str
    source_name: str | None = None


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Build direct Disease/Symptom/Unknown path JSON files."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="YAML config path.",
    )
    parser.add_argument(
        "--disease-id",
        action="append",
        default=[],
        help="Disease ID to build. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--symptom-id",
        action="append",
        default=[],
        help="Symptom ID to build. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--unknown-id",
        action="append",
        default=[],
        help="Unknown ID to build. Can be supplied multiple times.",
    )
    return parser.parse_args()


def build_direct_entity_paths(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    disease_ids: list[str] | None = None,
    symptom_ids: list[str] | None = None,
    unknown_ids: list[str] | None = None,
) -> dict[str, Any]:
    """Build direct entity paths and update the direct path index."""
    resolved_config_path = Path(config_path)
    query_settings = load_query_settings(resolved_config_path)
    direct_settings = query_settings.direct_entity_path
    cache_settings = load_direct_path_cache_settings(resolved_config_path)
    store = DirectPathCacheStore(cache_settings.sqlite_path)
    source_requests = _explicit_source_requests(
        disease_ids=disease_ids or [],
        symptom_ids=symptom_ids or [],
        unknown_ids=unknown_ids or [],
    )
    started_at = time.perf_counter()

    LOGGER.info(
        "Starting direct entity path build: explicit_source_count=%s, sqlite_enabled=%s, window_days=%s, direct_path_limit=%s",
        len(source_requests),
        cache_settings.enabled,
        direct_settings.window_days,
        direct_settings.direct_path_limit,
    )

    if cache_settings.enabled:
        if not store.exists:
            raise ValueError(
                f"direct path SQLite cache does not exist: {cache_settings.sqlite_path}"
            )
        if not source_requests:
            LOGGER.info("Loading direct entity sources from SQLite cache.")
            source_requests = _source_requests_from_sqlite(store)
            LOGGER.info(
                "Loaded direct entity sources from SQLite cache: source_count=%s",
                len(source_requests),
            )
        details = []
        for index, request in enumerate(source_requests, start=1):
            details.append(
                _build_one_source_with_logging(
                    config_path=resolved_config_path,
                    pattern=request.pattern,
                    source_id=request.source_id,
                    source_name=request.source_name,
                    window_days=direct_settings.window_days,
                    direct_path_limit=direct_settings.direct_path_limit,
                    store=store,
                    repository=None,
                    current_index=index,
                    total_count=len(source_requests),
                )
            )
    else:
        with Neo4jClient.from_config(resolved_config_path) as client:
            repository = KgRepository(
                client=client,
                config_path=resolved_config_path,
            )
            if not source_requests:
                LOGGER.info("Loading direct entity sources from Neo4j.")
                source_requests = _source_requests_from_neo4j(repository)
                LOGGER.info(
                    "Loaded direct entity sources from Neo4j: source_count=%s",
                    len(source_requests),
                )
            details = []
            for index, request in enumerate(source_requests, start=1):
                details.append(
                    _build_one_source_with_logging(
                        config_path=resolved_config_path,
                        pattern=request.pattern,
                        source_id=request.source_id,
                        source_name=request.source_name,
                        window_days=direct_settings.window_days,
                        direct_path_limit=direct_settings.direct_path_limit,
                        store=None,
                        repository=repository,
                        current_index=index,
                        total_count=len(source_requests),
                    )
                )

    saved_details = [detail for detail in details if detail["status"] == "saved"]
    skipped_details = [detail for detail in details if detail["status"] != "saved"]
    index_path = _update_direct_entity_path_index(
        direct_settings.index_path,
        saved_details,
        window_days=direct_settings.window_days,
        direct_path_limit=direct_settings.direct_path_limit,
    )
    summary = {
        "processed_count": len(details),
        "saved_count": len(saved_details),
        "skipped_count": len(skipped_details),
        "index_path": str(index_path),
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "details": details,
    }
    LOGGER.info(
        "Completed direct entity path build: processed_count=%s, saved_count=%s, skipped_count=%s, index_path=%s, elapsed_seconds=%s",
        summary["processed_count"],
        summary["saved_count"],
        summary["skipped_count"],
        summary["index_path"],
        summary["elapsed_seconds"],
    )
    return summary


def _build_one_source_with_logging(
    *,
    config_path: Path,
    pattern: PathPattern,
    source_id: str,
    source_name: str | None,
    window_days: int,
    direct_path_limit: int,
    store: DirectPathCacheStore | None,
    repository: KgRepository | None,
    current_index: int,
    total_count: int,
) -> dict[str, Any]:
    LOGGER.info(
        "Building direct entity path: progress=%s/%s, pattern=%s, source_id=%s",
        current_index,
        total_count,
        pattern.value,
        source_id,
    )
    started_at = time.perf_counter()
    detail = _build_one_source(
        config_path=config_path,
        pattern=pattern,
        source_id=source_id,
        source_name=source_name,
        window_days=window_days,
        direct_path_limit=direct_path_limit,
        store=store,
        repository=repository,
    )
    LOGGER.info(
        "Built direct entity path: progress=%s/%s, pattern=%s, source_id=%s, status=%s, path_count=%s, reason=%s, elapsed_seconds=%s",
        current_index,
        total_count,
        pattern.value,
        source_id,
        detail.get("status"),
        detail.get("path_count"),
        detail.get("reason"),
        round(time.perf_counter() - started_at, 3),
    )
    return detail


def _build_one_source(
    *,
    config_path: Path,
    pattern: PathPattern,
    source_id: str,
    source_name: str | None,
    window_days: int,
    direct_path_limit: int,
    store: DirectPathCacheStore | None,
    repository: KgRepository | None,
) -> dict[str, Any]:
    spec = get_path_pattern_spec(pattern)
    latest_training_date = _get_latest_training_date(
        pattern=pattern,
        source_id=source_id,
        store=store,
        repository=repository,
    )
    if latest_training_date is None:
        return _skipped_detail(
            pattern=pattern,
            source_parameter=spec.source_parameter,
            source_id=source_id,
            source_name=source_name,
            reason="no_direct_paths",
        )

    path_window = _build_path_window(latest_training_date, window_days)
    paths = _get_paths(
        pattern=pattern,
        source_id=source_id,
        start_date=path_window["start_date"],
        end_date=path_window["end_date"],
        store=store,
        repository=repository,
    )[:direct_path_limit]
    if not paths:
        return _skipped_detail(
            pattern=pattern,
            source_parameter=spec.source_parameter,
            source_id=source_id,
            source_name=source_name,
            reason="empty_paths",
            base_date=path_window["base_date"],
            path_window=path_window,
        )

    cache_context = build_direct_path_cache_context(
        base_date=path_window["base_date"],
        window_days=window_days,
        direct_path_limit=direct_path_limit,
    )
    result = {
        "source_id": source_id,
        "source_parameter": spec.source_parameter,
        spec.source_parameter: source_id,
        "pattern": pattern.value,
        "retrieval_context": {
            "base_date": path_window["base_date"],
            "query_family": None,
            "path_window": {
                "start_date": path_window["start_date"],
                "end_date": path_window["end_date"],
            },
            "paths": paths,
        },
    }
    output_path = save_direct_pattern_result(
        result,
        config_path,
        path_context=cache_context,
    )
    return {
        "status": "saved",
        "pattern": pattern.value,
        "source_parameter": spec.source_parameter,
        "source_id": source_id,
        "source_name": source_name,
        "base_date": path_window["base_date"],
        "start_date": path_window["start_date"],
        "end_date": path_window["end_date"],
        "window_days": window_days,
        "direct_path_limit": direct_path_limit,
        "path_key": cache_context["path_key"],
        "path_count": len(paths),
        "output_path": str(output_path),
    }


def _explicit_source_requests(
    *,
    disease_ids: list[str],
    symptom_ids: list[str],
    unknown_ids: list[str],
) -> list[DirectSourceRequest]:
    requests: list[DirectSourceRequest] = []
    for source_id in disease_ids:
        normalized = _normalize_optional_source_id(source_id)
        if normalized is not None:
            requests.append(
                DirectSourceRequest(
                    pattern=PathPattern.DISEASE_TASKSET_PATIENT,
                    source_id=normalized,
                )
            )
    for source_id in symptom_ids:
        normalized = _normalize_optional_source_id(source_id)
        if normalized is not None:
            requests.append(
                DirectSourceRequest(
                    pattern=PathPattern.SYMPTOM_TASKSET_PATIENT,
                    source_id=normalized,
                )
            )
    for source_id in unknown_ids:
        normalized = _normalize_optional_source_id(source_id)
        if normalized is not None:
            requests.append(
                DirectSourceRequest(
                    pattern=PathPattern.UNKNOWN_TASKSET_PATIENT,
                    source_id=normalized,
                )
            )
    return requests


def _source_requests_from_sqlite(
    store: DirectPathCacheStore,
) -> list[DirectSourceRequest]:
    requests: list[DirectSourceRequest] = []
    for pattern in _direct_patterns():
        LOGGER.info("Loading SQLite direct source summary: pattern=%s", pattern.value)
        rows = store.list_sources(pattern)
        LOGGER.info(
            "Loaded SQLite direct source summary: pattern=%s, source_count=%s",
            pattern.value,
            len(rows),
        )
        for row in rows:
            source_id = _normalize_optional_source_id(row.get("source_id"))
            if source_id is not None:
                requests.append(
                    DirectSourceRequest(
                        pattern=pattern,
                        source_id=source_id,
                        source_name=_optional_string(row.get("source_name")),
                    )
                )
    return requests


def _source_requests_from_neo4j(
    repository: KgRepository,
) -> list[DirectSourceRequest]:
    requests: list[DirectSourceRequest] = []
    for pattern in _direct_patterns():
        LOGGER.info("Loading Neo4j direct source summary: pattern=%s", pattern.value)
        started_at = time.perf_counter()
        rows = repository.get_direct_taskset_patient_source_summaries(pattern)
        LOGGER.info(
            "Loaded Neo4j direct source summary: pattern=%s, source_count=%s, elapsed_seconds=%s",
            pattern.value,
            len(rows),
            round(time.perf_counter() - started_at, 3),
        )
        for row in rows:
            source_id = _normalize_optional_source_id(row.get("source_id"))
            if source_id is not None:
                requests.append(
                    DirectSourceRequest(
                        pattern=pattern,
                        source_id=source_id,
                        source_name=_optional_string(row.get("source_name")),
                    )
                )
    return requests


def _get_latest_training_date(
    *,
    pattern: PathPattern,
    source_id: str,
    store: DirectPathCacheStore | None,
    repository: KgRepository | None,
) -> str | None:
    if store is not None:
        return store.get_latest_training_date(pattern, source_id)
    if repository is None:
        raise ValueError("repository is required when SQLite store is not supplied.")
    return repository.get_direct_taskset_patient_latest_training_date(pattern, source_id)


def _get_paths(
    *,
    pattern: PathPattern,
    source_id: str,
    start_date: str,
    end_date: str,
    store: DirectPathCacheStore | None,
    repository: KgRepository | None,
) -> list[dict[str, Any]]:
    if store is not None:
        return store.get_paths(
            pattern,
            source_id,
            start_date=start_date,
            end_date=end_date,
        )
    if repository is None:
        raise ValueError("repository is required when SQLite store is not supplied.")
    if pattern == PathPattern.DISEASE_TASKSET_PATIENT:
        return repository.get_disease_taskset_patient_randomized_paths(
            source_id,
            start_date=start_date,
            end_date=end_date,
        )
    if pattern == PathPattern.SYMPTOM_TASKSET_PATIENT:
        return repository.get_symptom_taskset_patient_randomized_paths(
            source_id,
            start_date=start_date,
            end_date=end_date,
        )
    if pattern == PathPattern.UNKNOWN_TASKSET_PATIENT:
        return repository.get_unknown_taskset_patient_randomized_paths(
            source_id,
            start_date=start_date,
            end_date=end_date,
        )
    raise ValueError(f"Unsupported direct path pattern: {pattern.value}")


def _build_path_window(base_date: str, window_days: int) -> dict[str, str]:
    parsed_base_date = date.fromisoformat(base_date)
    end_date = parsed_base_date + timedelta(days=1)
    start_date = end_date - timedelta(days=window_days)
    return {
        "base_date": parsed_base_date.isoformat(),
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
    }


def _update_direct_entity_path_index(
    index_path: str | Path,
    saved_details: list[dict[str, Any]],
    *,
    window_days: int,
    direct_path_limit: int,
) -> Path:
    path = Path(index_path)
    existing = _read_index(path)
    entries = {
        _index_entry_key(entry): entry
        for entry in existing.get("entries", [])
        if isinstance(entry, dict)
    }
    for detail in saved_details:
        entries[_index_entry_key(detail)] = {
            "pattern": detail["pattern"],
            "source_parameter": detail["source_parameter"],
            "source_id": detail["source_id"],
            "source_name": detail.get("source_name"),
            "base_date": detail["base_date"],
            "start_date": detail["start_date"],
            "end_date": detail["end_date"],
            "window_days": detail["window_days"],
            "direct_path_limit": detail["direct_path_limit"],
            "path_key": detail["path_key"],
            "path_count": detail["path_count"],
            "output_path": detail["output_path"],
        }
    payload = {
        "cache_type": "direct_entity_path_index",
        "updated_at": datetime.utcnow().isoformat(),
        "window_days": window_days,
        "direct_path_limit": direct_path_limit,
        "entries": sorted(
            entries.values(),
            key=lambda item: (str(item.get("pattern")), str(item.get("source_id"))),
        ),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path


def _read_index(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"entries": []}
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return data if isinstance(data, dict) else {"entries": []}


def _index_entry_key(entry: dict[str, Any]) -> str:
    return f"{entry.get('pattern')}::{entry.get('source_id')}"


def _skipped_detail(
    *,
    pattern: PathPattern,
    source_parameter: str,
    source_id: str,
    source_name: str | None,
    reason: str,
    base_date: str | None = None,
    path_window: dict[str, str] | None = None,
) -> dict[str, Any]:
    return {
        "status": "skipped",
        "reason": reason,
        "pattern": pattern.value,
        "source_parameter": source_parameter,
        "source_id": source_id,
        "source_name": source_name,
        "base_date": base_date,
        "path_window": path_window,
    }


def _direct_patterns() -> tuple[PathPattern, ...]:
    return (
        PathPattern.DISEASE_TASKSET_PATIENT,
        PathPattern.SYMPTOM_TASKSET_PATIENT,
        PathPattern.UNKNOWN_TASKSET_PATIENT,
    )


def _normalize_optional_source_id(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _optional_string(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def main() -> int:
    """CLI entrypoint."""
    args = parse_args()
    try:
        summary = build_direct_entity_paths(
            config_path=args.config,
            disease_ids=args.disease_id,
            symptom_ids=args.symptom_id,
            unknown_ids=args.unknown_id,
        )
    except Exception:
        LOGGER.exception("Direct entity path build failed: config_path=%s", args.config)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
