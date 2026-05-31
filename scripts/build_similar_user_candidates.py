"""Build similar-user candidates from scored paths.

这个脚本处在“path 打分”和“训练任务推荐”之间：

1. `scripts/score_pattern_paths.py` 会保存各模式的 scored paths。
2. 本脚本读取已保存的 scored detail，把患者 path 中的 `p2` 和 direct entity
   path 中的 `patient_id` 去重成候选相似用户。
3. 对每个候选用户继续查询 Neo4j 中的历史画像/游戏表现，计算 candidate_score。
4. 下游推荐任务流程会使用这里输出的候选用户历史数据。

它不会生成 path，也不会直接预测 task；它只负责“从已评分 path 聚合并排序候选用户”。

常用执行方式：

    python scripts/build_similar_user_candidates.py 40 --base-date 2022-05-22

默认从 `config/settings.yaml` 的 `candidate_ranking.patterns` 读取多模式列表。
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import sys
import tempfile
import time
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import load_query_settings, load_user_cache_settings
from similar_user.data_access.user_cache_index import (
    UserCacheEntry,
    UserCacheIndexStore,
)
from similar_user.data_access.kg_repository import KgRepository
from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.data_access.pattern_registry import resolve_path_pattern
from similar_user.domain.graph_schema import (
    DISEASE_TASKSET_PATIENT,
    SYMPTOM_TASKSET_PATIENT,
    UNKNOWN_TASKSET_PATIENT,
)
from similar_user.services.similarity.candidate_service import SimilarUserCandidateService
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger

from scripts.score_pattern_paths import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_SCORED_OUTPUT_DIR,
    build_scored_key,
    validate_scored_cache_context,
)
from similar_user.utils.pattern_storage import build_path_key
from similar_user.utils.user_cache_paths import (
    files_root_from_sqlite_path,
    patient_cache_leaf_dir,
    patient_cache_root,
)


LOGGER = get_logger(__name__)
DEFAULT_CANDIDATES_DIR = Path("data/similar_user_candidates")
DIRECT_ENTITY_PATTERNS = (
    DISEASE_TASKSET_PATIENT,
    SYMPTOM_TASKSET_PATIENT,
    UNKNOWN_TASKSET_PATIENT,
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for candidate aggregation."""
    parser = argparse.ArgumentParser(
        description="Build ranked similar-user candidates from top-k scored paths."
    )
    parser.add_argument("patient_id", help="Patient identifier used in the stored file.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--scored-paths-dir",
        default=str(DEFAULT_SCORED_OUTPUT_DIR),
        help="Directory containing saved scored detail JSON files.",
    )
    parser.add_argument(
        "--candidates-dir",
        default=str(DEFAULT_CANDIDATES_DIR),
        help="Directory used to store similar-user candidate detail and summary JSON files.",
    )
    parser.add_argument(
        "--base-date",
        required=True,
        help="Path/scored cache base date used to locate saved scored paths.",
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
        help="Path/scored cache query family used to locate saved scored paths.",
    )
    return parser.parse_args()


def build_similar_user_candidates(
    patient_id: str,
    *,
    config_path: str | Path | None = None,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
    candidates_dir: str | Path = DEFAULT_CANDIDATES_DIR,
    disease_course_window_days: int | None = None,
    base_date: str | None = None,
    query_family: str | None = None,
) -> dict[str, Any]:
    """Aggregate ranked candidate users from top-k scored paths."""
    started_at = time.perf_counter()
    resolved_config_path = DEFAULT_CONFIG_PATH if config_path is None else config_path
    query_settings = load_query_settings(resolved_config_path)
    ranking_settings = query_settings.candidate_ranking
    expected_scored_key = build_expected_scored_key(
        resolved_config_path,
        base_date=base_date,
        query_family=query_family,
    )
    resolved_disease_course_window_days = (
        ranking_settings.disease_course_window_days
        if disease_course_window_days is None
        else disease_course_window_days
    )
    _validate_optional_positive_int(
        resolved_disease_course_window_days,
        "disease_course_window_days",
    )
    selected_patterns = tuple(ranking_settings.patterns)
    candidate_cache_context = build_candidate_cache_context(
        resolved_config_path,
        scored_key=expected_scored_key,
        disease_course_window_days=resolved_disease_course_window_days,
    )
    user_cache_context = build_topk_candidate_user_cache_context(
        resolved_config_path,
        patient_id=patient_id,
        base_date=base_date,
        query_family=query_family,
        scored_key=expected_scored_key,
        candidate_cache_context=candidate_cache_context,
    )
    cached_result = load_cached_topk_candidate_result(
        user_cache_context,
        candidates_dir=candidates_dir,
        request_base_date=base_date,
    )
    if cached_result is not None:
        cached_result = refresh_cached_candidate_base_dates_on_hit(
            cached_result,
            config_path=resolved_config_path,
            request_base_date=base_date,
        )
        LOGGER.info(
            "Loaded topK similar-user candidates from user cache: patient_id=%s, query_family=%s, cached_base_date=%s, request_base_date=%s, data_path=%s",
            patient_id,
            user_cache_context.get("query_family"),
            user_cache_context.get("cached_base_date"),
            base_date,
            cached_result.get("user_cache_data_path"),
        )
        return cached_result

    scored_key = expected_scored_key
    if not _has_any_saved_scored_pattern_result(
        patient_id,
        patterns=selected_patterns,
        scored_paths_dir=scored_paths_dir,
        scored_key=expected_scored_key,
        config_path=resolved_config_path,
    ):
        scored_key = resolve_scored_key_from_user_cache(
            resolved_config_path,
            patient_id=patient_id,
            base_date=base_date,
            query_family=query_family,
            expected_scored_key=expected_scored_key,
            scored_paths_dir=scored_paths_dir,
        )
    if scored_key != expected_scored_key:
        candidate_cache_context = build_candidate_cache_context(
            resolved_config_path,
            scored_key=scored_key,
            disease_course_window_days=resolved_disease_course_window_days,
        )
        user_cache_context = build_topk_candidate_user_cache_context(
            resolved_config_path,
            patient_id=patient_id,
            base_date=base_date,
            query_family=query_family,
            scored_key=scored_key,
            candidate_cache_context=candidate_cache_context,
        )

    LOGGER.info(
        "Starting similar-user candidate build from saved scored paths: patient_id=%s, patterns=%s, candidate_top_k=%s, disease_course_window_days=%s, config_path=%s, scored_paths_dir=%s",
        patient_id,
        selected_patterns,
        ranking_settings.candidate_top_k,
        resolved_disease_course_window_days,
        resolved_config_path,
        scored_paths_dir,
    )

    with Neo4jClient.from_config(resolved_config_path) as client:
        user_service = UserService(
            kg_repository=KgRepository(
                client=client,
                config_path=Path(resolved_config_path),
            )
        )
        candidate_service = SimilarUserCandidateService(user_service=user_service)
        scored_results = []
        loaded_patterns = []
        skipped_patterns = []
        for item in selected_patterns:
            scored_result = load_saved_scored_pattern_result(
                patient_id,
                pattern=item,
                scored_paths_dir=scored_paths_dir,
                scored_key=scored_key,
                config_path=resolved_config_path,
            )
            if scored_result is not None:
                scored_results.append(scored_result)
                loaded_patterns.append(scored_result.get("pattern", item))
            else:
                skipped_patterns.append(item)
        if query_settings.direct_entity_path_scoring.use_when_patient_exists:
            direct_scored_results = load_saved_direct_entity_scored_results(
                patient_id,
                scored_paths_dir=scored_paths_dir,
                direct_scored_key=build_direct_entity_scored_key(
                    base_date=base_date,
                    score_top_k=query_settings.score_pattern_paths.top_k,
                ),
                config_path=resolved_config_path,
            )
            scored_results.extend(direct_scored_results)
            loaded_patterns.extend(
                result.get("pattern")
                for result in direct_scored_results
                if isinstance(result.get("pattern"), str)
            )
        LOGGER.info(
            "Loaded scored pattern results: patient_id=%s, loaded_count=%s, skipped_count=%s, loaded_patterns=%s, skipped_patterns=%s",
            patient_id,
            len(loaded_patterns),
            len(skipped_patterns),
            loaded_patterns,
            skipped_patterns,
        )
        if not scored_results:
            raise FileNotFoundError(
                f"No saved scored detail found for source_id {patient_id}: "
                f"patterns={selected_patterns}, scored_paths_dir={scored_paths_dir}"
            )
        result = candidate_service.aggregate_candidates_from_multiple_scored_results(
            scored_results,
            candidate_top_k=ranking_settings.candidate_top_k,
            scoring_settings=ranking_settings.scoring,
            disease_course_window_days=resolved_disease_course_window_days,
            include_direct_entity_paths=(
                query_settings.direct_entity_path_scoring.use_when_patient_exists
            ),
        )
        result.setdefault("retrieval_context", {})[
            "disease_course_window_days"
        ] = resolved_disease_course_window_days
        result["cache_context"] = candidate_cache_context
        result["user_cache_context"] = user_cache_context
        result["user_cache_hit"] = False
    LOGGER.info(
        "Completed similar-user candidate build: patient_id=%s, pre_score_candidate_count=%s, candidate_count=%s, scored_path_count=%s, disease_course_available_count=%s, disease_course_missing_count=%s, elapsed_seconds=%s",
        patient_id,
        result.get("pre_score_candidate_count"),
        result.get("candidate_count"),
        result.get("scored_path_count"),
        result.get("disease_course_available_count"),
        result.get("disease_course_missing_count"),
        round(time.perf_counter() - started_at, 3),
    )
    return result


def load_saved_scored_pattern_result(
    source_id: str,
    *,
    pattern: str,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
    scored_key: str | None = None,
    config_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Load one saved scored detail file produced by score_pattern_paths.py."""
    normalized_source_id = _normalize_required_string(source_id, "source_id")
    normalized_pattern = resolve_path_pattern(pattern).value
    resolved_scored_key = _normalize_required_string(scored_key, "scored_key")
    detail_path = _resolve_saved_scored_pattern_detail_path(
        normalized_source_id,
        pattern=normalized_pattern,
        scored_paths_dir=scored_paths_dir,
        scored_key=resolved_scored_key,
        config_path=config_path,
    )
    if not detail_path.exists():
        LOGGER.warning(
            "Saved scored detail not found for pattern %s: %s",
            normalized_pattern,
            detail_path,
        )
        return None
    with detail_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Saved scored detail must contain a JSON object: {detail_path}")
    validate_scored_cache_context(data, expected_scored_key=resolved_scored_key)
    return data


def _resolve_saved_scored_pattern_detail_path(
    source_id: str,
    *,
    pattern: str,
    scored_paths_dir: str | Path,
    scored_key: str,
    config_path: str | Path | None,
) -> Path:
    if config_path is not None:
        settings = load_user_cache_settings(config_path)
        query_settings = load_query_settings(config_path)
        if settings.enabled:
            context = build_topk_scored_path_lookup_context(
                config_path,
                source_id=source_id,
                scored_key=scored_key,
            )
            return (
                patient_cache_leaf_dir(
                    files_root_from_sqlite_path(settings.sqlite_path),
                    patient_id=source_id,
                    cache_type="scored_paths",
                    query_family=context["query_family"],
                    window_days=query_settings.patient_path.window_days,
                    config_hash=context["config_hash"],
                    cached_base_date=context["cached_base_date"],
                )
                / f"{_slug_part(pattern)}.detail.json"
            )
    return (
        Path(scored_paths_dir)
        / scored_key
        / pattern
        / (source_id[:2] or "unknown")
        / f"{source_id}.detail.json"
    )


def build_topk_scored_path_lookup_context(
    config_path: str | Path,
    *,
    source_id: str,
    scored_key: str,
) -> dict[str, str]:
    """Build enough metadata to locate a patient scored-path file."""
    path_key = _strip_score_suffix(scored_key)
    base_date = _extract_key_part(path_key, "base")
    query_family = _extract_key_slice(path_key.split("_"), "qf", ("pathcfg",))
    if not query_family:
        query_family = "default"
    return {
        "source_id": source_id,
        "cached_base_date": base_date,
        "query_family": query_family,
        "config_hash": _scored_paths_user_cache_config_hash(scored_key),
    }


def _has_any_saved_scored_pattern_result(
    source_id: str,
    *,
    patterns: tuple[str, ...],
    scored_paths_dir: str | Path,
    scored_key: str,
    config_path: str | Path | None = None,
) -> bool:
    normalized_source_id = _normalize_required_string(source_id, "source_id")
    resolved_scored_key = _normalize_required_string(scored_key, "scored_key")
    for pattern in patterns:
        normalized_pattern = resolve_path_pattern(pattern).value
        detail_path = _resolve_saved_scored_pattern_detail_path(
            normalized_source_id,
            pattern=normalized_pattern,
            scored_paths_dir=scored_paths_dir,
            scored_key=resolved_scored_key,
            config_path=config_path,
        )
        if detail_path.exists():
            return True
    return False


def load_saved_direct_entity_scored_results(
    source_id: str,
    *,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
    direct_scored_key: str,
    config_path: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Load saved direct-entity scored detail files for one patient."""
    normalized_source_id = _normalize_required_string(source_id, "source_id")
    normalized_scored_key = _normalize_required_string(
        direct_scored_key,
        "direct_scored_key",
    )
    bucket = normalized_source_id[:2] or "unknown"
    scored_results: list[dict[str, Any]] = []
    for pattern in DIRECT_ENTITY_PATTERNS:
        detail_paths = _find_direct_entity_scored_detail_paths(
            normalized_source_id,
            pattern=pattern,
            scored_paths_dir=scored_paths_dir,
            direct_scored_key=normalized_scored_key,
            config_path=config_path,
        )
        if not detail_paths:
            pattern_dir = Path(scored_paths_dir) / normalized_scored_key / pattern
            LOGGER.warning(
                "Saved direct entity scored detail not found for pattern %s: %s",
                pattern,
                pattern_dir,
            )
            continue
        for detail_path in detail_paths:
            with detail_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
            if not isinstance(data, dict):
                raise ValueError(
                    f"Saved direct entity scored detail must contain a JSON object: {detail_path}"
                )
            cache_context = data.get("cache_context")
            if (
                isinstance(cache_context, dict)
                and cache_context.get("scored_key") != normalized_scored_key
            ):
                continue
            scored_results.append(data)
    return scored_results


def _find_direct_entity_scored_detail_paths(
    source_id: str,
    *,
    pattern: str,
    scored_paths_dir: str | Path,
    direct_scored_key: str,
    config_path: str | Path | None,
) -> list[Path]:
    paths: list[Path] = []
    if config_path is not None:
        settings = load_user_cache_settings(config_path)
        if settings.enabled:
            base_date = _extract_key_part(direct_scored_key, "base")
            patient_root = (
                patient_cache_root(
                    files_root_from_sqlite_path(settings.sqlite_path),
                    source_id,
                )
                / "scored_paths"
                / "direct_entity"
                / f"window_{load_query_settings(config_path).direct_entity_path.window_days}"
            )
            paths.extend(
                sorted(
                    patient_root.glob(
                        f"config_*/base_{_slug_part(base_date)}/{_slug_part(pattern)}__*.detail.json"
                    )
                )
            )
            return paths
    legacy_pattern_dir = Path(scored_paths_dir) / direct_scored_key / pattern
    paths.extend(
        sorted(legacy_pattern_dir.glob(f"*/{source_id[:2] or 'unknown'}/{source_id}.detail.json"))
    )
    deduped: list[Path] = []
    seen: set[Path] = set()
    for path in paths:
        if path in seen:
            continue
        deduped.append(path)
        seen.add(path)
    return deduped


def build_direct_entity_scored_key(
    *,
    base_date: str | None,
    score_top_k: int | None,
) -> str:
    """Build the scored cache key produced by score_direct_entity_paths.py."""
    resolved_base_date = _normalize_required_string(base_date, "base_date")
    return (
        f"base_{_slug_part(resolved_base_date)}"
        f"_qf_direct_entity"
        f"_scoretopk_{score_top_k if score_top_k is not None else 'all'}"
    )


def _slug_part(value: object) -> str:
    text = str(value).strip().lower()
    slug = []
    for char in text:
        if char.isalnum():
            slug.append(char)
        elif char in ("-", "_"):
            slug.append(char)
        else:
            slug.append("-")
    return "".join(slug).strip("-") or "none"


def build_expected_scored_key(
    config_path: str | Path,
    *,
    base_date: str | None,
    query_family: str | None,
) -> str:
    """Build the scored path cache key expected by candidate aggregation."""
    query_settings = load_query_settings(config_path)
    path_key = build_path_key(
        config_path,
        base_date=base_date,
        query_family=query_family,
    )
    return build_scored_key(path_key, query_settings.score_pattern_paths.top_k)


def resolve_scored_key_from_user_cache(
    config_path: str | Path,
    *,
    patient_id: str,
    base_date: str | None,
    query_family: str | None,
    expected_scored_key: str,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
) -> str:
    """Return a recent valid scored_key when exact scored paths are not available."""
    settings = load_user_cache_settings(config_path)
    if not settings.enabled:
        return expected_scored_key
    normalized_base_date = _normalize_required_string(base_date, "base_date")
    query_settings = load_query_settings(config_path)
    store = UserCacheIndexStore(settings.sqlite_path)
    entry = store.find_latest_valid_source_entry(
        cache_type="scored_paths",
        source_type="patient",
        source_id=_normalize_required_string(patient_id, "patient_id"),
        query_family=_normalize_user_cache_query_family(query_family),
        window_days=query_settings.patient_path.window_days,
        config_hash=_scored_paths_user_cache_config_hash(expected_scored_key),
        request_base_date=normalized_base_date,
    )
    if entry is None:
        return expected_scored_key
    detail_path = Path(entry.data_path)
    if not detail_path.exists():
        store.delete_entry(entry)
        LOGGER.warning(
            "Deleted stale scored-path user-cache index entry because detail file is missing: patient_id=%s, detail_path=%s",
            entry.patient_id,
            detail_path,
        )
        return expected_scored_key
    scored_key = entry.payload.get("scored_key")
    if not isinstance(scored_key, str) or not scored_key.strip():
        return expected_scored_key
    resolved_scored_key = scored_key.strip()
    LOGGER.info(
        "Using scored paths from user cache: patient_id=%s, expected_scored_key=%s, cached_scored_key=%s, cached_base_date=%s, data_path=%s, scored_paths_dir=%s",
        patient_id,
        expected_scored_key,
        resolved_scored_key,
        entry.cached_base_date,
        detail_path,
        scored_paths_dir,
    )
    return resolved_scored_key


def save_similar_user_candidates_result(
    result: dict[str, Any],
    output_dir: str | Path = DEFAULT_CANDIDATES_DIR,
) -> dict[str, Path]:
    """Save candidate score details and summary as two JSON files."""
    detail_path, summary_path = get_similar_user_candidate_output_paths(
        result,
        output_dir,
    )
    _write_json_atomic(detail_path, build_similar_user_candidate_detail(result))
    _write_json_atomic(summary_path, build_similar_user_candidate_summary(result))
    _register_topk_candidate_user_cache(result, detail_path, summary_path)
    LOGGER.debug(
        "Saved similar-user candidates result: source_id=%s, detail_path=%s, summary_path=%s",
        result.get("source_id"),
        detail_path,
        summary_path,
    )
    return {"detail": detail_path, "summary": summary_path}


def get_similar_user_candidate_output_paths(
    result: dict[str, Any],
    output_dir: str | Path = DEFAULT_CANDIDATES_DIR,
) -> tuple[Path, Path]:
    """Return detail and summary output paths for one candidate result."""
    source_id = _normalize_required_string(result.get("source_id"), "source_id")
    candidate_key = _extract_candidate_key(result.get("cache_context"))
    user_cache_context = result.get("user_cache_context")
    if isinstance(user_cache_context, dict) and user_cache_context.get("enabled"):
        output_base = patient_cache_leaf_dir(
            files_root_from_sqlite_path(
                _normalize_required_string(
                    user_cache_context.get("sqlite_path"),
                    "sqlite_path",
                )
            ),
            patient_id=user_cache_context.get("patient_id") or source_id,
            cache_type="topk_candidates",
            query_family=user_cache_context.get("query_family"),
            window_days=user_cache_context.get("window_days"),
            config_hash=user_cache_context.get("config_hash"),
            cached_base_date=user_cache_context.get("cached_base_date"),
        )
        return (
            output_base / "candidates.detail.json",
            output_base / "candidates.summary.json",
        )
    bucket = source_id[:2] or "unknown"
    output_base = Path(output_dir) / candidate_key / bucket
    return (
        output_base / f"{source_id}.detail.json",
        output_base / f"{source_id}.summary.json",
    )


def build_similar_user_candidate_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Build candidate summary from calculated candidate scores."""
    return _build_candidate_score_output(result, include_score_details=False)


def build_similar_user_candidate_detail(result: dict[str, Any]) -> dict[str, Any]:
    """Build candidate detail from calculated candidate scores."""
    return _build_candidate_score_output(result, include_score_details=True)


def _build_candidate_score_output(
    result: dict[str, Any],
    *,
    include_score_details: bool,
) -> dict[str, Any]:
    """Build saved candidate output from candidate_score and score_details."""
    raw_candidates = result.get("candidates")
    candidates = raw_candidates if isinstance(raw_candidates, list) else []
    score_candidates = []
    for rank, item in enumerate(candidates, start=1):
        if not isinstance(item, dict):
            continue
        score_details = item.get("score_details")
        score_candidate = {
            "rank": rank,
            "patient_id": item.get("patient_id"),
            "candidate_score": item.get("candidate_score"),
        }
        if include_score_details:
            score_candidate["score_details"] = score_details
        else:
            score_candidate["score_summary"] = _build_candidate_score_summary(
                score_details
            )
        score_candidates.append(score_candidate)
    output = {
        "source_id": result.get("source_id"),
        "source_parameter": result.get("source_parameter"),
        "candidate_top_k": result.get("candidate_top_k"),
        "retrieval_context": result.get("retrieval_context"),
        "cache_context": result.get("cache_context"),
        "candidate_count": result.get("candidate_count"),
        "candidates": score_candidates,
    }
    if include_score_details:
        output.update(
            {
                "pattern": result.get("pattern"),
                "patterns": result.get("patterns"),
                "path_count": result.get("path_count"),
                "scored_path_count": result.get("scored_path_count"),
                "user_cache_context": result.get("user_cache_context"),
                "user_cache_hit": result.get("user_cache_hit"),
                "pre_score_candidate_count": result.get("pre_score_candidate_count"),
                "disease_course_available_count": result.get(
                    "disease_course_available_count"
                ),
                "disease_course_missing_count": result.get(
                    "disease_course_missing_count"
                ),
            }
        )
    return output


def build_candidate_key(scored_key: str, candidate_config_hash: str) -> str:
    """Build a cache key for similar-user candidate results."""
    return f"{scored_key}_candcfg_{candidate_config_hash}"


def build_candidate_cache_context(
    config_path: str | Path,
    *,
    scored_key: str,
    disease_course_window_days: int | None,
) -> dict[str, Any]:
    """Build cache metadata for similar-user candidate results."""
    candidate_config = _candidate_config_payload(
        config_path,
        disease_course_window_days=disease_course_window_days,
    )
    candidate_config_hash = _short_hash(candidate_config)
    return {
        "cache_type": "similar_user_candidates",
        "scored_key": scored_key,
        "candidate_key": build_candidate_key(scored_key, candidate_config_hash),
        "candidate_config_hash": candidate_config_hash,
        "candidate_config": candidate_config,
    }


def build_direct_entity_candidate_cache_context(
    config_path: str | Path,
    *,
    scored_result: dict[str, Any],
    disease_course_window_days: int | None,
) -> dict[str, Any]:
    """Build cache metadata for direct-entity similar-user candidate results."""
    scored_cache_context = scored_result.get("cache_context")
    if not isinstance(scored_cache_context, dict):
        raise ValueError("direct entity candidate cache requires score cache_context.")
    scored_key = _normalize_required_string(
        scored_cache_context.get("scored_key"),
        "scored_key",
    )
    scored_source_hash = _short_hash(
        {
            "cache_type": "scored_direct_entity_paths",
            "scored_key_without_base_date": _strip_base_date_from_key(scored_key),
            "pattern_source_keys": scored_cache_context.get("pattern_source_keys"),
            "source_entries": scored_cache_context.get("source_entries"),
            "scoring_input_signature": _short_hash(
                _to_plain_data(scored_result.get("scoring_input"))
            ),
        }
    )
    direct_scored_key = f"{scored_key}_directsrc_{scored_source_hash}"
    candidate_context = build_candidate_cache_context(
        config_path,
        scored_key=direct_scored_key,
        disease_course_window_days=disease_course_window_days,
    )
    candidate_context["direct_entity_scored_source_hash"] = scored_source_hash
    candidate_context["direct_entity_scored_context"] = {
        "scored_key": scored_key,
        "pattern_source_keys": scored_cache_context.get("pattern_source_keys"),
        "source_entries": scored_cache_context.get("source_entries"),
    }
    return candidate_context


def build_topk_candidate_user_cache_context(
    config_path: str | Path,
    *,
    patient_id: str,
    base_date: str | None,
    query_family: str | None,
    scored_key: str,
    candidate_cache_context: dict[str, Any],
) -> dict[str, Any]:
    """Build source-centered cache metadata for final patient topK candidates."""
    settings = load_user_cache_settings(config_path)
    if not settings.enabled:
        return {"enabled": False, "cache_type": "topk_candidates"}
    query_settings = load_query_settings(config_path)
    normalized_patient_id = _normalize_required_string(patient_id, "patient_id")
    normalized_base_date = _normalize_required_string(base_date, "base_date")
    normalized_scored_key = _normalize_required_string(scored_key, "scored_key")
    candidate_key = _normalize_required_string(
        candidate_cache_context.get("candidate_key"),
        "candidate_key",
    )
    candidate_config_hash = _normalize_required_string(
        candidate_cache_context.get("candidate_config_hash"),
        "candidate_config_hash",
    )
    query_family_key = _normalize_user_cache_query_family(query_family)
    config_hash = _short_hash(
        {
            "cache_type": "topk_candidates",
            "cache_key_without_base_date": _strip_base_date_from_key(candidate_key),
        }
    )
    return {
        "enabled": settings.enabled,
        "cache_type": "topk_candidates",
        "sqlite_path": settings.sqlite_path,
        "patient_id": normalized_patient_id,
        "source_type": "patient",
        "source_id": normalized_patient_id,
        "query_family": query_family_key,
        "window_days": query_settings.patient_path.window_days,
        "config_hash": config_hash,
        "cached_base_date": normalized_base_date,
        "valid_days": settings.topk_candidates_valid_days,
        "candidate_key": candidate_key,
        "scored_key": normalized_scored_key,
        "candidate_config_hash": candidate_config_hash,
    }


def build_direct_entity_topk_candidate_user_cache_context(
    config_path: str | Path,
    *,
    source_id: str,
    base_date: str | None,
    candidate_cache_context: dict[str, Any],
) -> dict[str, Any]:
    """Build source-centered metadata for direct-entity topK candidates."""
    settings = load_user_cache_settings(config_path)
    if not settings.enabled:
        return {"enabled": False, "cache_type": "topk_candidates"}
    query_settings = load_query_settings(config_path)
    normalized_source_id = _normalize_required_string(source_id, "source_id")
    normalized_base_date = _normalize_required_string(base_date, "base_date")
    candidate_key = _normalize_required_string(
        candidate_cache_context.get("candidate_key"),
        "candidate_key",
    )
    candidate_config_hash = _normalize_required_string(
        candidate_cache_context.get("candidate_config_hash"),
        "candidate_config_hash",
    )
    config_hash = _short_hash(
        {
            "cache_type": "topk_candidates",
            "source_type": "direct_entity_profile",
            "cache_key_without_base_date": _strip_base_date_from_key(candidate_key),
        }
    )
    window_days = query_settings.candidate_ranking.disease_course_window_days
    if window_days is None:
        raise ValueError(
            "candidate_ranking disease_course_window_days is required for direct entity topK candidate cache."
        )
    return {
        "enabled": settings.enabled,
        "cache_type": "topk_candidates",
        "sqlite_path": settings.sqlite_path,
        "patient_id": normalized_source_id,
        "source_type": "direct_entity_profile",
        "source_id": normalized_source_id,
        "query_family": "direct_entity",
        "window_days": window_days,
        "config_hash": config_hash,
        "cached_base_date": normalized_base_date,
        "valid_days": settings.topk_candidates_valid_days,
        "candidate_key": candidate_key,
        "scored_key": candidate_cache_context.get("scored_key"),
        "candidate_config_hash": candidate_config_hash,
    }


def load_cached_topk_candidate_result(
    user_cache_context: dict[str, Any],
    *,
    candidates_dir: str | Path = DEFAULT_CANDIDATES_DIR,
    request_base_date: str | None,
) -> dict[str, Any] | None:
    """Load the newest valid topK candidate cache for one patient/config."""
    if not user_cache_context.get("enabled"):
        return None
    request_date = _normalize_required_string(request_base_date, "base_date")
    store = UserCacheIndexStore(
        _normalize_required_string(user_cache_context.get("sqlite_path"), "sqlite_path")
    )
    entry = store.find_latest_valid_source_entry(
        cache_type="topk_candidates",
        source_type=_normalize_required_string(
            user_cache_context.get("source_type"),
            "source_type",
        ),
        source_id=_normalize_required_string(
            user_cache_context.get("source_id"),
            "source_id",
        ),
        query_family=_normalize_required_string(
            user_cache_context.get("query_family"),
            "query_family",
        ),
        window_days=_normalize_positive_int(
            user_cache_context.get("window_days"),
            "window_days",
        ),
        config_hash=_normalize_required_string(
            user_cache_context.get("config_hash"),
            "config_hash",
        ),
        request_base_date=request_date,
    )
    if entry is None:
        return None
    detail_path = Path(entry.data_path)
    if not detail_path.exists():
        store.delete_entry(entry)
        LOGGER.warning(
            "Deleted stale topK candidate user-cache index entry because detail file is missing: patient_id=%s, detail_path=%s",
            entry.patient_id,
            detail_path,
        )
        return None
    with detail_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Cached topK candidate detail must be a JSON object: {detail_path}")
    _validate_cached_topk_candidate_result(
        data,
        expected_candidate_key=_normalize_required_string(
            entry.payload.get("candidate_key"),
            "candidate_key",
        ),
    )
    result = dict(data)
    result["user_cache_hit"] = True
    result["user_cache_context"] = {
        **user_cache_context,
        "cached_base_date": entry.cached_base_date,
        "valid_days": entry.valid_days,
    }
    result["user_cache_data_path"] = str(detail_path)
    # Keep output path calculation stable even when a custom candidates_dir is supplied.
    result.setdefault("cache_context", data.get("cache_context"))
    return result


def refresh_cached_candidate_base_dates_on_hit(
    result: dict[str, Any],
    *,
    config_path: str | Path,
    request_base_date: str | None,
) -> dict[str, Any]:
    """Refresh cached candidate disease-course base dates for the request date."""
    settings = load_user_cache_settings(config_path)
    query_settings = load_query_settings(config_path)
    if (
        not settings.enabled
        or not settings.refresh_candidate_base_date_on_hit
        or not query_settings.candidate_ranking.scoring.disease_course_secondary_ability
    ):
        return result

    source_patient_id = _normalize_optional_string(result.get("source_id"))
    request_date = _normalize_optional_string(request_base_date)
    candidate_ids = _extract_cached_candidate_ids(result)
    if source_patient_id is None or request_date is None or not candidate_ids:
        return result

    with Neo4jClient.from_config(config_path) as client:
        user_service = UserService(
            kg_repository=KgRepository(
                client=client,
                config_path=Path(config_path),
            )
        )
        matches = user_service.find_patient_total_score_timepoint_matches(
            source_patient_id=source_patient_id,
            source_training_date=request_date,
            comparison_patient_ids=candidate_ids,
        )
    refreshed = refresh_cached_candidate_base_dates_from_matches(
        result,
        matches=matches,
        request_base_date=request_date,
    )
    LOGGER.info(
        "Refreshed cached candidate base dates: patient_id=%s, request_base_date=%s, refreshed_count=%s, candidate_count=%s",
        source_patient_id,
        request_date,
        refreshed.get("candidate_base_date_refresh", {}).get("refreshed_count"),
        len(candidate_ids),
    )
    return refreshed


def refresh_cached_candidate_base_dates_from_matches(
    result: dict[str, Any],
    *,
    matches: list[dict[str, Any]] | object,
    request_base_date: str,
) -> dict[str, Any]:
    """Return cached candidate result with candidate_base_date refreshed from matches."""
    refreshed = copy.deepcopy(result)
    recommended_dates = _build_recommended_dates_by_candidate(matches)
    candidates = refreshed.get("candidates")
    refreshed_count = 0
    if isinstance(candidates, list):
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            patient_id = _normalize_optional_string(candidate.get("patient_id"))
            if patient_id is None:
                continue
            candidate_date = recommended_dates.get(patient_id)
            if candidate_date is not None:
                refreshed_count += 1
            _set_candidate_base_date(candidate, candidate_date)
    refreshed["candidate_base_date_refresh"] = {
        "enabled": True,
        "request_base_date": request_base_date,
        "refreshed_count": refreshed_count,
        "matched_candidate_count": len(recommended_dates),
    }
    return refreshed


def _build_candidate_score_summary(score_details: object) -> dict[str, Any]:
    details = score_details if isinstance(score_details, dict) else {}
    common_game_score_similarity = _extract_nested_value(
        details,
        "common_game_score_similarity",
        "similarity",
    )
    game_similarity_with_diversity_score = _extract_nested_value(
        details,
        "game_similarity_with_diversity_score",
        "score",
    )
    set_same_score = _extract_nested_value(details, "set_same_scores", "score")
    disease_course_secondary_ability_score = _extract_nested_value(
        details,
        "disease_course_secondary_ability",
        "score",
    )
    disease_course_secondary_ability_distance = _extract_nested_value(
        details,
        "disease_course_secondary_ability",
        "distance",
    )
    disease_course_secondary_ability_candidate_base_date = _extract_nested_value(
        details,
        "disease_course_secondary_ability",
        "candidate_base_date",
    )
    disease_course_secondary_ability_summary = {
        "score": disease_course_secondary_ability_score,
        "distance": disease_course_secondary_ability_distance,
    }
    if disease_course_secondary_ability_candidate_base_date is not None:
        disease_course_secondary_ability_summary[
            "candidate_base_date"
        ] = disease_course_secondary_ability_candidate_base_date

    return {
        "common_game_score_similarity": common_game_score_similarity,
        "game_similarity_with_diversity_score": game_similarity_with_diversity_score,
        "disease_course_secondary_ability": disease_course_secondary_ability_summary,
        "set_same_score": {
            "total": set_same_score,
            "disease": _extract_nested_value(
                details,
                "set_same_scores",
                "disease",
                "score",
            ),
            "symptom": _extract_nested_value(
                details,
                "set_same_scores",
                "symptom",
                "score",
            ),
            "unknown": _extract_nested_value(
                details,
                "set_same_scores",
                "unknown",
                "score",
            ),
        },
    }


def _extract_nested_value(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _extract_candidate_key(cache_context: object) -> str:
    if not isinstance(cache_context, dict):
        raise ValueError("candidate result cache_context must be present before saving.")
    candidate_key = cache_context.get("candidate_key")
    if not isinstance(candidate_key, str) or not candidate_key.strip():
        raise ValueError("candidate result cache_context.candidate_key must be non-empty.")
    return candidate_key.strip()


def _register_topk_candidate_user_cache(
    result: dict[str, Any],
    detail_path: Path,
    summary_path: Path,
) -> None:
    user_cache_context = result.get("user_cache_context")
    if not isinstance(user_cache_context, dict) or not user_cache_context.get("enabled"):
        return
    store = UserCacheIndexStore(
        _normalize_required_string(user_cache_context.get("sqlite_path"), "sqlite_path")
    )
    entry = UserCacheEntry(
        cache_type="topk_candidates",
        patient_id=_normalize_required_string(
            user_cache_context.get("patient_id"),
            "patient_id",
        ),
        query_family=_normalize_required_string(
            user_cache_context.get("query_family"),
            "query_family",
        ),
        window_days=_normalize_positive_int(
            user_cache_context.get("window_days"),
            "window_days",
        ),
        config_hash=_normalize_required_string(
            user_cache_context.get("config_hash"),
            "config_hash",
        ),
        cached_base_date=_normalize_required_string(
            user_cache_context.get("cached_base_date"),
            "cached_base_date",
        ),
        valid_days=_normalize_non_negative_int(
            user_cache_context.get("valid_days"),
            "valid_days",
        ),
        data_path=str(detail_path),
        payload={
            "candidate_key": _normalize_required_string(
                user_cache_context.get("candidate_key"),
                "candidate_key",
            ),
            "scored_key": user_cache_context.get("scored_key"),
            "candidate_config_hash": user_cache_context.get("candidate_config_hash"),
            "summary_path": str(summary_path),
        },
        source_type=_normalize_required_string(
            user_cache_context.get("source_type"),
            "source_type",
        ),
        source_id=_normalize_required_string(
            user_cache_context.get("source_id"),
            "source_id",
        ),
    )
    store.upsert_entry(entry)


def _validate_cached_topk_candidate_result(
    result: dict[str, Any],
    *,
    expected_candidate_key: str,
) -> None:
    cache_context = result.get("cache_context")
    if not isinstance(cache_context, dict):
        raise ValueError("Cached topK candidate result is missing cache_context.")
    actual_candidate_key = cache_context.get("candidate_key")
    if actual_candidate_key != expected_candidate_key:
        raise ValueError(
            "Cached topK candidate result cache key mismatch: "
            f"expected={expected_candidate_key}, actual={actual_candidate_key}."
        )


def _extract_cached_candidate_ids(result: dict[str, Any]) -> list[str]:
    candidates = result.get("candidates")
    if not isinstance(candidates, list):
        return []
    candidate_ids: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        patient_id = _normalize_optional_string(candidate.get("patient_id"))
        if patient_id is None or patient_id in seen:
            continue
        candidate_ids.append(patient_id)
        seen.add(patient_id)
    return candidate_ids


def _build_recommended_dates_by_candidate(matches: object) -> dict[str, str]:
    if not isinstance(matches, list):
        return {}
    recommended_dates: dict[str, str] = {}
    for match in matches:
        if not isinstance(match, dict):
            continue
        matched = match.get("matched")
        if not isinstance(matched, dict):
            continue
        patient_id = _normalize_optional_string(matched.get("patient_id"))
        recommended_date = _normalize_optional_string(matched.get("recommended_date"))
        if patient_id is None or recommended_date is None:
            continue
        recommended_dates.setdefault(patient_id, recommended_date)
    return recommended_dates


def _set_candidate_base_date(
    candidate: dict[str, Any],
    candidate_base_date: str | None,
) -> None:
    for score_key in ("score_details", "score_summary"):
        score_data = candidate.get(score_key)
        if not isinstance(score_data, dict):
            continue
        disease_course = score_data.get("disease_course_secondary_ability")
        if not isinstance(disease_course, dict):
            continue
        if candidate_base_date is None:
            disease_course.pop("candidate_base_date", None)
            continue
        disease_course["candidate_base_date"] = candidate_base_date


def _candidate_config_payload(
    config_path: str | Path,
    *,
    disease_course_window_days: int | None,
) -> dict[str, Any]:
    query_settings = load_query_settings(config_path)
    ranking_settings = query_settings.candidate_ranking
    return {
        "patterns": list(ranking_settings.patterns),
        "candidate_top_k": ranking_settings.candidate_top_k,
        "total_score_match_top_k": ranking_settings.total_score_match_top_k,
        "disease_course_window_days": disease_course_window_days,
        "direct_entity_path_scoring": {
            "use_when_patient_exists": (
                query_settings.direct_entity_path_scoring.use_when_patient_exists
            )
        },
        "scoring": _to_plain_data(ranking_settings.scoring),
    }


def _to_plain_data(value: Any) -> Any:
    if is_dataclass(value):
        return _to_plain_data(asdict(value))
    if isinstance(value, dict):
        return {str(key): _to_plain_data(item) for key, item in sorted(value.items())}
    if isinstance(value, (list, tuple)):
        return [_to_plain_data(item) for item in value]
    return value


def _short_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:8]


def _normalize_required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _normalize_optional_string(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    return text or None


def _normalize_positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _normalize_non_negative_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _normalize_user_cache_query_family(query_family: str | None) -> str:
    if query_family is None or not str(query_family).strip():
        return "default"
    return _slug_part(str(query_family).strip())


def _strip_base_date_from_key(value: str) -> str:
    parts = value.split("_", 2)
    if len(parts) == 3 and parts[0] == "base":
        return parts[2]
    return value


def _strip_score_suffix(value: str) -> str:
    marker = "_scoretopk_"
    if marker in value:
        return value.split(marker, 1)[0]
    return value


def _extract_key_part(value: str, marker: str) -> str:
    parts = value.split("_")
    for index, part in enumerate(parts[:-1]):
        if part == marker:
            return parts[index + 1]
    raise ValueError(f"{marker} must be present in cache key: {value}")


def _extract_key_slice(
    parts: list[str],
    start_marker: str,
    end_markers: tuple[str, ...],
) -> str:
    try:
        start_index = parts.index(start_marker) + 1
    except ValueError:
        return ""
    end_index = len(parts)
    for marker in end_markers:
        if marker in parts[start_index:]:
            marker_index = parts.index(marker, start_index)
            end_index = min(end_index, marker_index)
    return "_".join(parts[start_index:end_index]).strip("_")


def _scored_paths_user_cache_config_hash(scored_key: str) -> str:
    return _short_hash(
        {
            "cache_type": "scored_paths",
            "cache_key_without_base_date": _strip_base_date_from_key(scored_key),
        }
    )


def _validate_optional_positive_int(value: object, field_name: str) -> None:
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_file.write(serialized)
        temp_path = Path(temp_file.name)

    os.replace(temp_path, path)


def main() -> int:
    """Build similar-user candidates and log the JSON result."""
    args = parse_args()
    try:
        result = build_similar_user_candidates(
            args.patient_id,
            config_path=args.config,
            scored_paths_dir=args.scored_paths_dir,
            candidates_dir=args.candidates_dir,
            **_scored_cache_kwargs(args),
        )
        output_paths = save_similar_user_candidates_result(
            result,
            output_dir=args.candidates_dir,
        )
        LOGGER.info(
            "Saved similar-user candidates: detail_path=%s, summary_path=%s",
            output_paths["detail"],
            output_paths["summary"],
        )
    except Exception as exc:
        LOGGER.exception("Build similar user candidates from scored paths failed: %s", exc)
        return 1

    return 0


def _scored_cache_kwargs(args: argparse.Namespace) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    base_date = getattr(args, "base_date", None)
    if isinstance(base_date, str) and base_date.strip():
        kwargs["base_date"] = base_date.strip()
    query_family = getattr(args, "query_family", None)
    if isinstance(query_family, str) and query_family.strip():
        kwargs["query_family"] = query_family.strip()
    return kwargs


if __name__ == "__main__":
    raise SystemExit(main())
