"""Refresh stale user-cache entries from queued refresh jobs.

这个脚本消费 user_cache_refresh_jobs 中的 pending 任务。在线请求命中
stale topK 缓存时只负责登记 job；真正重建 topK 缓存由这里异步完成。
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import DEFAULT_CONFIG_PATH, load_query_settings, load_user_cache_settings
from similar_user.data_access.user_cache_index import (
    UserCacheEntry,
    UserCacheIndexStore,
    UserCacheRefreshJob,
)
from similar_user.services.similarity import SimilarUserCandidateService
from similar_user.utils.logger import get_logger

from scripts.build_similar_user_candidates import (
    DEFAULT_CANDIDATES_DIR,
    build_direct_entity_candidate_cache_context,
    build_direct_entity_topk_candidate_user_cache_context,
    build_similar_user_candidates,
    load_saved_direct_entity_scored_results,
    save_similar_user_candidates_result,
)
from scripts.predict_training_tasks_from_direct_entity import (
    _score_direct_entity_paths_with_auto_refresh,
)
from scripts.score_direct_entity_paths import (
    DEFAULT_SCORED_OUTPUT_DIR,
    save_scored_direct_entity_result,
)


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class RefreshJobsSummary:
    """Summary returned by one refresh-job worker run."""

    sqlite_path: str
    requested_limit: int
    claimed_jobs: int
    completed_jobs: int
    failed_jobs: int
    skipped_jobs: int
    cleaned_jobs: int


def parse_args() -> argparse.Namespace:
    """Parse CLI args for refreshing user-cache jobs."""
    parser = argparse.ArgumentParser(
        description="Refresh stale user-cache entries from queued refresh jobs."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--scored-paths-dir",
        default=str(DEFAULT_SCORED_OUTPUT_DIR),
        help="Directory used to store scored path detail files.",
    )
    parser.add_argument(
        "--candidates-dir",
        default=str(DEFAULT_CANDIDATES_DIR),
        help="Directory used to store topK candidate detail files.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Maximum number of pending jobs to claim in this run.",
    )
    parser.add_argument(
        "--no-cleanup",
        action="store_true",
        help="Skip cleanup of old completed/failed refresh job records.",
    )
    return parser.parse_args()


def refresh_user_cache_jobs(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
    candidates_dir: str | Path = DEFAULT_CANDIDATES_DIR,
    limit: int = 20,
    cleanup: bool = True,
) -> dict[str, Any]:
    """领取并执行 pending refresh job，成功写入新缓存，失败记录原因。"""
    settings = load_user_cache_settings(config_path)
    if not settings.enabled:
        return asdict(
            RefreshJobsSummary(
                sqlite_path=settings.sqlite_path,
                requested_limit=limit,
                claimed_jobs=0,
                completed_jobs=0,
                failed_jobs=0,
                skipped_jobs=0,
                cleaned_jobs=0,
            )
        )

    store = UserCacheIndexStore(settings.sqlite_path)
    jobs = store.claim_pending_refresh_jobs(limit=limit)
    completed_jobs = 0
    failed_jobs = 0
    skipped_jobs = 0

    for job in jobs:
        try:
            refreshed = _refresh_one_job(
                job,
                store=store,
                config_path=config_path,
                scored_paths_dir=scored_paths_dir,
                candidates_dir=candidates_dir,
            )
            if refreshed:
                store.mark_refresh_job_completed(_require_job_id(job))
                completed_jobs += 1
            else:
                store.mark_refresh_job_failed(
                    _require_job_id(job),
                    error_message="Refresh job skipped.",
                )
                skipped_jobs += 1
        except Exception as exc:
            store.mark_refresh_job_failed(
                _require_job_id(job),
                error_message=_truncate_error_message(exc),
            )
            failed_jobs += 1
            LOGGER.exception(
                "User-cache refresh job failed: job_id=%s, source_type=%s, source_id=%s, query_family=%s, request_base_date=%s",
                job.id,
                job.source_type,
                job.source_id,
                job.query_family,
                job.request_base_date,
            )

    cleaned_jobs = _cleanup_refresh_jobs(
        store,
        config_path=config_path,
    ) if cleanup else 0
    summary = RefreshJobsSummary(
        sqlite_path=settings.sqlite_path,
        requested_limit=limit,
        claimed_jobs=len(jobs),
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        skipped_jobs=skipped_jobs,
        cleaned_jobs=cleaned_jobs,
    )
    return asdict(summary)


def _refresh_one_job(
    job: UserCacheRefreshJob,
    *,
    store: UserCacheIndexStore,
    config_path: str | Path,
    scored_paths_dir: str | Path,
    candidates_dir: str | Path,
) -> bool:
    """根据 job 的 source_type 刷新对应 topK 缓存。"""
    if job.cache_type != "topk_candidates":
        raise ValueError(f"Unsupported refresh cache_type: {job.cache_type}")
    if job.source_type == "patient":
        _refresh_patient_topk_job(
            job,
            config_path=config_path,
            scored_paths_dir=scored_paths_dir,
            candidates_dir=candidates_dir,
        )
        return True
    if job.source_type == "direct_entity_profile":
        _refresh_direct_entity_topk_job(
            job,
            store=store,
            config_path=config_path,
            scored_paths_dir=scored_paths_dir,
            candidates_dir=candidates_dir,
        )
        return True
    raise ValueError(f"Unsupported refresh source_type: {job.source_type}")


def _refresh_patient_topk_job(
    job: UserCacheRefreshJob,
    *,
    config_path: str | Path,
    scored_paths_dir: str | Path,
    candidates_dir: str | Path,
) -> None:
    """刷新 patient path 对应的 topK candidates 缓存。"""
    result = build_similar_user_candidates(
        job.source_id,
        config_path=config_path,
        scored_paths_dir=scored_paths_dir,
        candidates_dir=candidates_dir,
        base_date=job.request_base_date,
        query_family=None if job.query_family == "default" else job.query_family,
        skip_topk_user_cache_read=True,
    )
    save_similar_user_candidates_result(result, output_dir=candidates_dir)


def _refresh_direct_entity_topk_job(
    job: UserCacheRefreshJob,
    *,
    store: UserCacheIndexStore,
    config_path: str | Path,
    scored_paths_dir: str | Path,
    candidates_dir: str | Path,
) -> None:
    """刷新 direct entity profile 对应的 topK candidates 缓存。"""
    scoring_input = _recover_direct_entity_scoring_input(
        job,
        store=store,
        config_path=config_path,
        scored_paths_dir=scored_paths_dir,
    )
    query_settings = load_query_settings(config_path)
    direct_score_result = _score_direct_entity_paths_with_auto_refresh(
        config_path=config_path,
        patient_id=str(scoring_input.get("patient_id") or job.source_id),
        base_date=job.request_base_date,
        age=_require_scoring_input_value(scoring_input, "age"),
        education=_require_scoring_input_value(scoring_input, "education"),
        gender=_require_scoring_input_value(scoring_input, "gender"),
        disease_ids=_list_scoring_input_values(scoring_input, "disease_ids"),
        symptom_ids=_list_scoring_input_values(scoring_input, "symptom_ids"),
        unknown_ids=_list_scoring_input_values(scoring_input, "unknown_ids"),
        top_k=query_settings.score_pattern_paths.top_k,
    )
    save_scored_direct_entity_result(
        direct_score_result,
        scored_paths_dir,
        config_path=config_path,
    )
    candidate_cache_context = build_direct_entity_candidate_cache_context(
        config_path,
        scored_result=direct_score_result,
        disease_course_window_days=query_settings.candidate_ranking.disease_course_window_days,
    )
    candidate_user_cache_context = build_direct_entity_topk_candidate_user_cache_context(
        config_path,
        source_id=str(direct_score_result.get("source_id") or job.source_id),
        base_date=job.request_base_date,
        candidate_cache_context=candidate_cache_context,
    )
    candidate_result = SimilarUserCandidateService().aggregate_candidates_from_direct_entity_scored_result(
        direct_score_result,
        candidate_top_k=query_settings.candidate_ranking.candidate_top_k,
    )
    candidate_result["cache_context"] = candidate_cache_context
    candidate_result["user_cache_context"] = candidate_user_cache_context
    candidate_result["user_cache_hit"] = False
    save_similar_user_candidates_result(candidate_result, output_dir=candidates_dir)


def _recover_direct_entity_scoring_input(
    job: UserCacheRefreshJob,
    *,
    store: UserCacheIndexStore,
    config_path: str | Path,
    scored_paths_dir: str | Path,
) -> dict[str, Any]:
    """从旧 topK detail 关联的 scored detail 中恢复 direct entity 输入画像。"""
    topk_entry = _find_latest_topk_entry_for_job(store, job)
    if topk_entry is None:
        raise ValueError(
            "Cannot recover direct entity scoring_input: matching topK entry not found."
        )
    topk_detail = _read_json_object(Path(topk_entry.data_path))
    scored_key = _extract_direct_entity_scored_key(topk_detail)
    scored_results = load_saved_direct_entity_scored_results(
        job.source_id,
        scored_paths_dir=scored_paths_dir,
        direct_scored_key=scored_key,
        config_path=config_path,
    )
    for result in scored_results:
        scoring_input = result.get("scoring_input")
        if isinstance(scoring_input, dict):
            return dict(scoring_input)
    raise ValueError(
        "Cannot recover direct entity scoring_input: scored detail missing scoring_input."
    )


def _find_latest_topk_entry_for_job(
    store: UserCacheIndexStore,
    job: UserCacheRefreshJob,
) -> UserCacheEntry | None:
    entries = [
        entry
        for entry in store.list_entries()
        if entry.cache_type == job.cache_type
        and entry.source_type == job.source_type
        and entry.source_id == job.source_id
        and entry.query_family == job.query_family
        and entry.window_days == job.window_days
        and entry.config_hash == job.config_hash
        and entry.cached_base_date <= job.request_base_date
    ]
    entries.sort(
        key=lambda entry: (
            entry.cached_base_date,
            entry.updated_at or "",
        ),
        reverse=True,
    )
    return entries[0] if entries else None


def _extract_direct_entity_scored_key(topk_detail: dict[str, Any]) -> str:
    cache_context = topk_detail.get("cache_context")
    if not isinstance(cache_context, dict):
        raise ValueError("Cached direct entity topK detail is missing cache_context.")
    scored_context = cache_context.get("direct_entity_scored_context")
    if not isinstance(scored_context, dict):
        raise ValueError(
            "Cached direct entity topK detail is missing direct_entity_scored_context."
        )
    scored_key = scored_context.get("scored_key")
    if not isinstance(scored_key, str) or not scored_key.strip():
        raise ValueError("direct_entity_scored_context.scored_key must be non-empty.")
    return scored_key.strip()


def _cleanup_refresh_jobs(
    store: UserCacheIndexStore,
    *,
    config_path: str | Path,
) -> int:
    settings = load_user_cache_settings(config_path)
    now = datetime.now(timezone.utc)
    completed_before = now - timedelta(
        days=settings.refresh_job_completed_retention_days
    )
    failed_before = now - timedelta(days=settings.refresh_job_failed_retention_days)
    return store.cleanup_refresh_jobs(
        completed_before=completed_before.isoformat(timespec="seconds"),
        failed_before=failed_before.isoformat(timespec="seconds"),
    )


def _read_json_object(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Cached detail file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Cached detail must contain a JSON object: {path}")
    return data


def _require_scoring_input_value(scoring_input: dict[str, Any], field_name: str) -> Any:
    value = scoring_input.get(field_name)
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"direct entity scoring_input.{field_name} is required.")
    return value


def _list_scoring_input_values(
    scoring_input: dict[str, Any],
    field_name: str,
) -> list[str]:
    values = scoring_input.get(field_name)
    if not isinstance(values, list):
        return []
    return [str(value).strip() for value in values if str(value).strip()]


def _require_job_id(job: UserCacheRefreshJob) -> int:
    if job.id is None:
        raise ValueError("refresh job id is required.")
    return job.id


def _truncate_error_message(exc: Exception) -> str:
    text = f"{type(exc).__name__}: {exc}"
    return text[:1000]


def main() -> int:
    """Run one refresh-job worker batch and log the summary JSON."""
    args = parse_args()
    try:
        summary = refresh_user_cache_jobs(
            config_path=args.config,
            scored_paths_dir=args.scored_paths_dir,
            candidates_dir=args.candidates_dir,
            limit=args.limit,
            cleanup=not args.no_cleanup,
        )
        LOGGER.info(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    except Exception as exc:
        LOGGER.exception("Refresh user-cache jobs failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
