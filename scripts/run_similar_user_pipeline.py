"""Run the full similar-user pipeline from cache lookup to candidate ranking.

这个脚本把相似用户候选生成流程串成一个入口：

1. 优先读取 topK candidates 用户缓存。
2. topK candidates 缺失或过期时，读取 scored paths；scored paths 缺失时自动重新评分。
3. raw paths 缺失时自动重新查询 Neo4j 构建并保存。
4. 最后按 `--output-level` 输出候选 ID、候选分数或完整结果。

常用执行方式：

    python scripts/run_similar_user_pipeline.py 40 --base-date 2022-05-22
"""

from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import json
import sys
import threading
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from similar_user.domain.graph_schema import (
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
)
from similar_user.utils.logger import get_logger
from config.settings import load_query_settings, load_user_cache_settings

from scripts.build_similar_user_candidates import (
    build_similar_user_candidates,
    save_similar_user_candidates_result,
)
from scripts.build_pattern_paths import run_configured_pattern_path_flows
from scripts.score_pattern_paths import (
    DEFAULT_CONFIG_PATH,
    score_and_save_configured_pattern_paths,
)
from scripts.score_direct_entity_paths import (
    save_scored_direct_entity_result,
    score_direct_entity_paths,
)


LOGGER = get_logger(__name__)
_RAW_PATH_BUILD_SEMAPHORES: dict[tuple[str, int], threading.BoundedSemaphore] = {}
_RAW_PATH_BUILD_SEMAPHORES_LOCK = threading.Lock()


class EmptyPathResultsError(RuntimeError):
    """Raised when freshly built pattern paths are all empty."""


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the full similar-user pipeline."""
    parser = argparse.ArgumentParser(
        description="Run path retrieval, path scoring, and similar-user candidate ranking."
    )
    parser.add_argument("patient_id", help="Patient identifier used in Neo4j queries.")
    parser.add_argument(
        "--pattern",
        default=PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        help=(
            "Legacy output field. Path build and scoring use "
            "candidate_ranking.patterns from the config."
        ),
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--skip-path-build",
        action="store_true",
        help="Deprecated compatibility flag; cache lookup now decides whether paths are rebuilt.",
    )
    parser.add_argument(
        "--skip-path-scoring",
        action="store_true",
        help="Deprecated compatibility flag; cache lookup now decides whether paths are rescored.",
    )
    parser.add_argument(
        "--query-family",
        default=None,
        choices=(
            "training_order_source_window",
            "date_window",
            "training_order_local_sampling_source_window",
            "training_order_age_source_window",
            "training_order_age_edu_source_window",
            "training_order_age_completed_source_window",
            "training_order_age_edu_completed_source_window",
            "training_order_age_edu_task_completed_source_window",
            "training_order_dual_window",
            "training_order_local_sampling_dual_window",
            "training_order_age_dual_window",
            "training_order_age_edu_dual_window",
            "training_order_age_completed_dual_window",
            "training_order_age_edu_completed_dual_window",
            "training_order_age_edu_task_completed_dual_window",
        ),
        help=(
            "Query family for paired-statistics path building. Defaults to "
            "training_order_source_window enforces s1/s2 training-date order and filters by the s1 date window; date_window only filters by the s1 date window."
        ),
    )
    parser.add_argument(
        "--base-date",
        required=True,
        help="Exclusive window end date used to build paths, for example 2022-05-22.",
    )
    parser.add_argument(
        "--output-level",
        choices=("ids", "scores", "full"),
        default="ids",
        help="Output detail level: ids, scores, or full.",
    )
    return parser.parse_args()


def run_similar_user_pipeline(
    patient_id: str,
    *,
    base_date: str,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    config_path: str | Path | None = None,
    skip_path_build: bool = False,
    skip_path_scoring: bool = False,
    query_family: str | None = None,
) -> dict[str, Any]:
    """Run path retrieval, scoring, and candidate ranking as one workflow."""
    resolved_config_path = DEFAULT_CONFIG_PATH if config_path is None else config_path
    resolved_window_days = _resolve_patient_path_window_days(resolved_config_path)
    started_at = time.perf_counter()
    LOGGER.info(
        "Starting similar-user pipeline: patient_id=%s, pattern=%s, base_date=%s, window_days=%s, config_path=%s",
        patient_id,
        pattern,
        base_date,
        resolved_window_days,
        resolved_config_path,
    )
    effective_query_family = query_family or "training_order_source_window"
    path_generation = None
    direct_entity_scoring = None
    candidate_result, direct_entity_scoring = _build_patient_candidates_with_auto_refresh(
        patient_id,
        config_path=resolved_config_path,
        base_date=base_date,
        query_family=effective_query_family,
    )
    candidate_output_paths = save_similar_user_candidates_result(candidate_result)
    LOGGER.info(
        "Saved similar-user candidates: detail_path=%s, summary_path=%s",
        candidate_output_paths["detail"],
        candidate_output_paths["summary"],
    )
    result = {
        "patient_id": patient_id,
        "pattern": pattern,
        "config_path": str(resolved_config_path),
        "skip_path_build": skip_path_build,
        "skip_path_scoring": skip_path_scoring,
        "base_date": base_date,
        "window_days": resolved_window_days,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "path_generation": path_generation,
        "direct_entity_scoring": direct_entity_scoring,
        "candidate_result": candidate_result,
        "candidate_output_paths": {
            key: str(value) for key, value in candidate_output_paths.items()
        },
    }
    LOGGER.info(
        "Completed similar-user pipeline: patient_id=%s, candidate_count=%s, elapsed_seconds=%s",
        patient_id,
        candidate_result.get("candidate_count"),
        result["elapsed_seconds"],
    )
    return result


def _summarize_path_result(path_result: dict[str, object]) -> dict[str, object]:
    """Summarize the saved path result without logging every path row."""
    retrieval_context = path_result.get("retrieval_context")
    paths = []
    path_window = None
    if isinstance(retrieval_context, dict):
        raw_paths = retrieval_context.get("paths")
        if isinstance(raw_paths, list):
            paths = raw_paths
        raw_path_window = retrieval_context.get("path_window")
        if isinstance(raw_path_window, dict):
            path_window = raw_path_window

    return {
        "patient_id": path_result.get("patient_id"),
        "pattern": path_result.get("pattern"),
        "path_window": path_window,
        "path_count": len(paths),
    }


def _raise_if_path_results_empty(
    path_generation: list[dict[str, object]],
    *,
    patient_id: str,
    base_date: str,
    window_days: int,
) -> None:
    """Stop the pipeline when freshly built path data is empty."""
    path_count = sum(
        item.get("path_count")
        for item in path_generation
        if isinstance(item.get("path_count"), int)
    )
    if path_count > 0:
        return
    raise EmptyPathResultsError(
        "path_result does not contain paths: "
        f"patient_id={patient_id}, base_date={base_date}, window_days={window_days}."
    )


def _resolve_patient_path_window_days(
    config_path: str | Path,
) -> int:
    return load_query_settings(config_path).patient_path.window_days


def _score_patient_paths_with_auto_refresh(
    patient_id: str,
    *,
    config_path: str | Path,
    base_date: str,
    query_family: str,
) -> None:
    try:
        score_and_save_configured_pattern_paths(
            patient_id,
            config_path=config_path,
            base_date=base_date,
            query_family=query_family,
        )
    except FileNotFoundError:
        LOGGER.info(
            "Patient raw paths missing or expired; rebuilding before scoring: patient_id=%s, base_date=%s, query_family=%s",
            patient_id,
            base_date,
            query_family,
        )
        path_generation = _build_patient_raw_paths_with_limit(
            patient_id,
            config_path=config_path,
            base_date=base_date,
            query_family=query_family,
        )
        _raise_if_path_results_empty(
            path_generation,
            patient_id=patient_id,
            base_date=base_date,
            window_days=_resolve_patient_path_window_days(config_path),
        )
        score_and_save_configured_pattern_paths(
            patient_id,
            config_path=config_path,
            base_date=base_date,
            query_family=query_family,
        )


def _build_patient_raw_paths_with_limit(
    patient_id: str,
    *,
    config_path: str | Path,
    base_date: str,
    query_family: str,
) -> list[dict[str, object]]:
    settings = load_user_cache_settings(config_path)
    max_attempts = settings.raw_path_build_max_retries + 1
    last_error: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            with _raw_path_build_limiter(config_path):
                LOGGER.info(
                    "Building raw paths with limiter: patient_id=%s, base_date=%s, query_family=%s, attempt=%s/%s, raw_path_build_workers=%s",
                    patient_id,
                    base_date,
                    query_family,
                    attempt,
                    max_attempts,
                    settings.raw_path_build_workers,
                )
                return [
                    _summarize_path_result(item)
                    for item in run_configured_pattern_path_flows(
                        patient_id,
                        config_path=config_path,
                        base_date=base_date,
                        query_family=query_family,
                    )
                ]
        except Exception as exc:
            last_error = exc
            if attempt >= max_attempts:
                break
            LOGGER.warning(
                "Raw path build failed; retrying: patient_id=%s, base_date=%s, query_family=%s, attempt=%s/%s, error_type=%s, error=%s",
                patient_id,
                base_date,
                query_family,
                attempt,
                max_attempts,
                type(exc).__name__,
                exc,
            )
            time.sleep(settings.raw_path_build_retry_sleep_seconds)
    assert last_error is not None
    raise last_error


@contextmanager
def _raw_path_build_limiter(config_path: str | Path):
    settings = load_user_cache_settings(config_path)
    semaphore = _get_raw_path_build_semaphore(
        settings.sqlite_path,
        settings.raw_path_build_workers,
    )
    with semaphore:
        with _cross_process_raw_path_build_lock(
            settings.sqlite_path,
            workers=settings.raw_path_build_workers,
        ):
            yield


def _get_raw_path_build_semaphore(
    sqlite_path: str,
    workers: int,
) -> threading.BoundedSemaphore:
    key = (str(Path(sqlite_path)), workers)
    with _RAW_PATH_BUILD_SEMAPHORES_LOCK:
        semaphore = _RAW_PATH_BUILD_SEMAPHORES.get(key)
        if semaphore is None:
            semaphore = threading.BoundedSemaphore(workers)
            _RAW_PATH_BUILD_SEMAPHORES[key] = semaphore
        return semaphore


@contextmanager
def _cross_process_raw_path_build_lock(sqlite_path: str, *, workers: int):
    if workers != 1:
        yield
        return
    lock_file = None
    lock_path = Path(sqlite_path).with_suffix(".raw_path_build.lock")
    try:
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        lock_file = lock_path.open("a", encoding="utf-8")
        fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
        yield
    finally:
        if lock_file is not None:
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
            lock_file.close()


def _build_patient_candidates_with_auto_refresh(
    patient_id: str,
    *,
    config_path: str | Path,
    base_date: str,
    query_family: str,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """构建患者候选用户，并在缓存缺失时自动补齐依赖数据。

    流程：
    1. 先尝试构建 topK 候选用户，内部会优先读取 topK candidates 缓存。
    2. 如果 topK 缓存命中，直接返回候选用户结果。
    3. 如果 topK 未命中但 scored paths 可用，则用 scored paths 构建并保存 topK。
    4. 如果 scored paths 缺失或过期，则先重新评分并保存 scored paths，再重试候选用户构建。
    5. 如果配置开启 direct entity path scoring，则在候选用户流程成功后补充该部分评分。
    """
    try:
        result = build_similar_user_candidates(
            patient_id,
            config_path=config_path,
            base_date=base_date,
            query_family=query_family,
        )
        if result.get("user_cache_hit"):
            return result, None

        direct_entity_scoring = _score_direct_entity_paths_if_enabled(
            patient_id,
            config_path=config_path,
            base_date=base_date,
        )
        if direct_entity_scoring is None:
            return result, None
        return (
            build_similar_user_candidates(
                patient_id,
                config_path=config_path,
                base_date=base_date,
                query_family=query_family,
            ),
            direct_entity_scoring,
        )
    except FileNotFoundError:
        LOGGER.info(
            "Patient scored paths missing or expired; rescoring before candidate build: patient_id=%s, base_date=%s, query_family=%s",
            patient_id,
            base_date,
            query_family,
        )
        _score_patient_paths_with_auto_refresh(
            patient_id,
            config_path=config_path,
            base_date=base_date,
            query_family=query_family,
        )
        direct_entity_scoring = _score_direct_entity_paths_if_enabled(
            patient_id,
            config_path=config_path,
            base_date=base_date,
        )
        return (
            build_similar_user_candidates(
                patient_id,
                config_path=config_path,
                base_date=base_date,
                query_family=query_family,
            ),
            direct_entity_scoring,
        )


def _score_direct_entity_paths_if_enabled(
    patient_id: str,
    *,
    config_path: str | Path,
    base_date: str,
) -> dict[str, Any] | None:
    """Score direct entity paths for an existing patient when enabled."""
    query_settings = load_query_settings(config_path)
    if not query_settings.direct_entity_path_scoring.use_when_patient_exists:
        LOGGER.info(
            "Skipped direct entity path scoring because use_when_patient_exists=false: patient_id=%s",
            patient_id,
        )
        return None

    result = score_direct_entity_paths(
        patient_id=patient_id,
        base_date=base_date,
        config_path=config_path,
    )
    output_paths = save_scored_direct_entity_result(result, config_path=config_path)
    LOGGER.info(
        "Completed direct entity path scoring: patient_id=%s, should_score=%s, scored_path_count=%s, saved_file_count=%s",
        patient_id,
        result.get("should_score"),
        result.get("scored_path_count"),
        len(output_paths),
    )
    return {
        "should_score": result.get("should_score"),
        "reason": result.get("reason"),
        "path_count": result.get("path_count"),
        "scored_path_count": result.get("scored_path_count"),
        "output_paths": [
            {key: str(value) for key, value in item.items()}
            for item in output_paths
        ],
    }


def summarize_pipeline_result(
    result: dict[str, Any],
    *,
    output_level: str = "ids",
) -> dict[str, Any]:
    """Build the compact pipeline output used by default CLI logging."""
    if output_level not in {"ids", "scores"}:
        raise ValueError(f"Unsupported summary output level: {output_level}.")
    candidate_result = result.get("candidate_result")
    candidate_summary: dict[str, Any] | None = None
    if isinstance(candidate_result, dict):
        candidate_summary = {
            "patient_id": candidate_result.get("patient_id"),
            "pattern": candidate_result.get("pattern"),
            "candidate_top_k": candidate_result.get("candidate_top_k"),
            "path_count": candidate_result.get("path_count"),
            "scored_path_count": candidate_result.get("scored_path_count"),
            "path_window": _extract_path_window(candidate_result),
            "candidate_count": candidate_result.get("candidate_count"),
        }
        candidates = candidate_result.get("candidates")
        if output_level == "ids":
            candidate_summary["candidate_ids"] = _extract_candidate_ids(candidates)
        else:
            candidate_summary["candidates"] = _extract_candidate_scores(candidates)

    return {
        "patient_id": result.get("patient_id"),
        "pattern": result.get("pattern"),
        "config_path": result.get("config_path"),
        "skip_path_build": result.get("skip_path_build"),
        "skip_path_scoring": result.get("skip_path_scoring"),
        "base_date": result.get("base_date"),
        "window_days": result.get("window_days"),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "path_generation": result.get("path_generation"),
        "candidate_summary": candidate_summary,
    }


def _extract_path_window(candidate_result: dict[str, Any]) -> object:
    retrieval_context = candidate_result.get("retrieval_context")
    if not isinstance(retrieval_context, dict):
        return None
    return retrieval_context.get("path_window")


def _extract_candidate_ids(candidates: object) -> list[object]:
    if not isinstance(candidates, list):
        return []

    candidate_ids: list[object] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_ids.append(candidate.get("patient_id"))
    return candidate_ids


def _extract_candidate_scores(candidates: object) -> list[dict[str, object]]:
    if not isinstance(candidates, list):
        return []

    candidate_scores: list[dict[str, object]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_scores.append(
            {
                "patient_id": candidate.get("patient_id"),
                "candidate_score": candidate.get("candidate_score"),
            }
        )
    return candidate_scores


def main() -> int:
    """Run the full pipeline and log the JSON result."""
    args = parse_args()
    try:
        result = run_similar_user_pipeline(
            args.patient_id,
            pattern=args.pattern,
            config_path=args.config,
            skip_path_build=args.skip_path_build,
            skip_path_scoring=args.skip_path_scoring,
            base_date=args.base_date,
            query_family=args.query_family,
        )
    except Exception as exc:
        LOGGER.exception(
            "Similar user pipeline failed: patient_id=%s, config_path=%s",
            args.patient_id,
            args.config,
        )
        return 1

    output = (
        result
        if args.output_level == "full"
        else summarize_pipeline_result(result, output_level=args.output_level)
    )
    LOGGER.info(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
