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

from config.settings import load_query_settings
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
            "training_order",
            "date_window",
            "training_order_local_sampling",
            "training_order_age_only",
            "training_order_layer1_age_completion",
            "training_order_layer2_education_exact",
            "training_order_layer3_activity_task_type",
        ),
        help="Path/scored cache query family used to locate saved scored paths.",
    )
    return parser.parse_args()


def build_similar_user_candidates(
    patient_id: str,
    *,
    config_path: str | Path | None = None,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
    disease_course_window_days: int | None = None,
    base_date: str | None = None,
    query_family: str | None = None,
) -> dict[str, Any]:
    """Aggregate ranked candidate users from top-k scored paths."""
    started_at = time.perf_counter()
    resolved_config_path = DEFAULT_CONFIG_PATH if config_path is None else config_path
    query_settings = load_query_settings(resolved_config_path)
    ranking_settings = query_settings.candidate_ranking
    scored_key = build_expected_scored_key(
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
        result["cache_context"] = build_candidate_cache_context(
            resolved_config_path,
            scored_key=scored_key,
            disease_course_window_days=resolved_disease_course_window_days,
        )
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
) -> dict[str, Any] | None:
    """Load one saved scored detail file produced by score_pattern_paths.py."""
    normalized_source_id = _normalize_required_string(source_id, "source_id")
    normalized_pattern = resolve_path_pattern(pattern).value
    resolved_scored_key = _normalize_required_string(scored_key, "scored_key")
    detail_path = (
        Path(scored_paths_dir)
        / resolved_scored_key
        / normalized_pattern
        / (normalized_source_id[:2] or "unknown")
        / f"{normalized_source_id}.detail.json"
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


def load_saved_direct_entity_scored_results(
    source_id: str,
    *,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
    direct_scored_key: str,
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
        pattern_dir = Path(scored_paths_dir) / normalized_scored_key / pattern
        detail_paths = sorted(
            pattern_dir.glob(f"*/{bucket}/{normalized_source_id}.detail.json")
        )
        if not detail_paths:
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
            scored_results.append(data)
    return scored_results


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
    return {
        "source_id": result.get("source_id"),
        "source_parameter": result.get("source_parameter"),
        "candidate_top_k": result.get("candidate_top_k"),
        "retrieval_context": result.get("retrieval_context"),
        "cache_context": result.get("cache_context"),
        "candidate_count": result.get("candidate_count"),
        "candidates": score_candidates,
    }


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
