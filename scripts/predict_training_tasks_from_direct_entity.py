"""Predict training tasks from manual profile and direct entity paths.

这个脚本服务“不走患者 path”的预测场景：

1. 使用命令行传入的患者标识、画像和疾病/症状/未知实体列表。
2. 读取已离线保存的 direct entity paths，并按画像相似度评分。
3. 只基于 direct entity scored paths 聚合候选用户。
4. 查询候选用户历史训练任务并推荐 task。

`patient_id` 只作为本次预测对象标识和文件保存名，不要求 KG 中存在该 Patient。

常用执行方式：

    python scripts/predict_training_tasks_from_direct_entity.py \
      --patient-id 201231885555 \
      --base-date 2026-05-27 \
      --age 66 \
      --education 本科 \
      --gender 男 \
      --disease-id AU_DIS_0029

    python scripts/predict_training_tasks_from_direct_entity.py \
      --patient-id 201231885555 \
      --base-date 2026-05-27 \
      --age 66 \
      --education 本科 \
      --gender 男 \
      --disease-name 注意缺陷多动障碍
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import load_query_settings  # noqa: E402
from similar_user.data_access.kg_repository import KgRepository  # noqa: E402
from similar_user.data_access.neo4j_client import Neo4jClient  # noqa: E402
from similar_user.services.llm_client import LlmClient  # noqa: E402
from similar_user.services.direct_entity_fallback_prediction import (  # noqa: E402
    DirectEntityFallbackPredictionService,
)
from similar_user.services.direct_entity_name_resolution import (  # noqa: E402
    DirectEntityNameResolver,
)
from similar_user.services.task_prediction import (  # noqa: E402
    TrainingTaskPredictionService,
)
from similar_user.services.user_service import UserService  # noqa: E402
from similar_user.services.similarity import SimilarUserCandidateService  # noqa: E402
from similar_user.utils.logger import get_logger  # noqa: E402

from scripts.score_pattern_paths import DEFAULT_CONFIG_PATH  # noqa: E402
from scripts.score_direct_entity_paths import (  # noqa: E402
    DEFAULT_SCORED_OUTPUT_DIR,
    save_scored_direct_entity_result,
    score_direct_entity_paths,
)
from scripts.build_similar_user_candidates import (  # noqa: E402
    DEFAULT_CANDIDATES_DIR,
    build_direct_entity_candidate_cache_context,
    build_direct_entity_topk_candidate_user_cache_context,
    load_cached_topk_candidate_result,
    save_similar_user_candidates_result,
)
from scripts.build_direct_entity_paths import build_direct_entity_paths  # noqa: E402
from similar_user.data_access.algorithm_request_results import (  # noqa: E402
    normalize_algorithm_request_education,
    normalize_algorithm_request_gender,
)


LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Predict training tasks from manual profile and direct entity paths."
    )
    parser.add_argument("--patient-id", required=True, help="Prediction target ID.")
    parser.add_argument("--base-date", required=True, help="Prediction base date.")
    parser.add_argument("--age", required=True, help="Target age.")
    parser.add_argument("--education", required=True, help="Target education.")
    parser.add_argument("--gender", required=True, help="Target gender.")
    parser.add_argument(
        "--disease-id",
        action="append",
        nargs="+",
        default=[],
        help="Disease IDs. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--disease-name",
        action="append",
        nargs="+",
        default=[],
        help=(
            "Disease/entity names to resolve from KG Disease/Symptom/Unknown nodes. "
            "Can be supplied multiple times."
        ),
    )
    parser.add_argument(
        "--symptom-id",
        action="append",
        nargs="+",
        default=[],
        help="Symptom IDs. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--unknown-id",
        action="append",
        nargs="+",
        default=[],
        help="Unknown IDs. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--scored-paths-dir",
        default=str(DEFAULT_SCORED_OUTPUT_DIR),
        help="Directory used to store scored direct entity path files.",
    )
    parser.add_argument(
        "--candidates-dir",
        default=str(DEFAULT_CANDIDATES_DIR),
        help="Directory used to store direct entity similar-user candidate files.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path.",
    )
    parser.add_argument(
        "--output-level",
        choices=("ids", "scores", "full"),
        default="ids",
        help="Output detail level.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip the LLM call and return deterministic candidate-task predictions.",
    )
    parser.add_argument(
        "--task-top-k",
        type=int,
        help="Override query.training_task_prediction.task_top_k.",
    )
    parser.add_argument(
        "--include-prompt",
        action="store_true",
        help="Include the generated LLM prompt in full output.",
    )
    return parser.parse_args()


def predict_training_tasks_from_direct_entity(
    *,
    patient_id: str,
    base_date: str,
    age: int | str,
    education: str,
    gender: str,
    disease_ids: list[str] | None = None,
    disease_names: list[str] | None = None,
    symptom_ids: list[str] | None = None,
    unknown_ids: list[str] | None = None,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
    candidates_dir: str | Path = DEFAULT_CANDIDATES_DIR,
    use_llm: bool = True,
    include_prompt: bool = False,
    task_top_k: int | None = None,
) -> dict[str, Any]:
    """Run the direct-entity-only task prediction flow."""
    normalized_patient_id = _normalize_required_text(patient_id, "patient_id")
    normalized_gender = normalize_direct_entity_gender(gender)
    normalized_education = normalize_direct_entity_education(education)
    resolved_config_path = Path(config_path)
    query_settings = load_query_settings(resolved_config_path)
    resolved_disease_ids = _dedupe_texts(disease_ids or [])
    resolved_symptom_ids = _dedupe_texts(symptom_ids or [])
    resolved_unknown_ids = _dedupe_texts(unknown_ids or [])
    resolved_disease_names = _dedupe_texts(disease_names or [])
    entity_name_resolution = {
        "resolved": [],
        "unresolved": [],
    }
    if resolved_disease_names:
        with Neo4jClient.from_config(resolved_config_path) as client:
            repository = KgRepository(
                client=client,
                config_path=resolved_config_path,
            )
            entity_name_resolution = resolve_direct_entity_names(
                DirectEntityNameResolver(repository),
                resolved_disease_names,
            )
        resolved_disease_ids = _dedupe_texts(
            resolved_disease_ids + _ids_by_type(entity_name_resolution, "disease")
        )
        resolved_symptom_ids = _dedupe_texts(
            resolved_symptom_ids + _ids_by_type(entity_name_resolution, "symptom")
        )
        resolved_unknown_ids = _dedupe_texts(
            resolved_unknown_ids + _ids_by_type(entity_name_resolution, "unknown")
        )
    resolved_task_top_k = task_top_k or query_settings.training_task_prediction.task_top_k
    candidate_top_k = query_settings.candidate_ranking.candidate_top_k
    candidate_window_days = query_settings.candidate_ranking.disease_course_window_days
    if candidate_window_days is None:
        raise ValueError(
            "candidate_ranking disease_course_window_days is required for direct entity prediction."
        )
    LOGGER.info(
        "Starting direct entity task prediction: patient_id=%s, base_date=%s, disease_id_count=%s, symptom_id_count=%s, unknown_id_count=%s, score_top_k=%s, candidate_top_k=%s, task_top_k=%s",
        normalized_patient_id,
        base_date,
        len(resolved_disease_ids),
        len(resolved_symptom_ids),
        len(resolved_unknown_ids),
        query_settings.score_pattern_paths.top_k,
        candidate_top_k,
        resolved_task_top_k,
    )

    has_direct_entities = bool(
        resolved_disease_ids or resolved_symptom_ids or resolved_unknown_ids
    )
    missing_entity_reason = (
        "no_resolved_entity_names" if resolved_disease_names else "missing_entity_input"
    )
    direct_score_result: dict[str, Any] = {
        "should_score": False,
        "reason": missing_entity_reason,
        "path_count": 0,
        "scored_path_count": 0,
        "top_k": query_settings.score_pattern_paths.top_k,
        "missing_sources": [],
    }
    direct_score_output_paths: list[dict[str, Path]] = []
    candidate_result: dict[str, Any] = {
        "source_id": normalized_patient_id,
        "source_parameter": "manual_profile",
        "candidate_top_k": candidate_top_k,
        "path_count": 0,
        "scored_path_count": 0,
        "candidate_count": 0,
        "pre_score_candidate_count": 0,
        "ranking": "direct_entity_best_score_avg_score_match_count",
        "candidates": [],
    }

    if has_direct_entities:
        direct_score_result = _score_direct_entity_paths_with_auto_refresh(
            config_path=resolved_config_path,
            patient_id=normalized_patient_id,
            base_date=base_date,
            age=age,
            education=normalized_education,
            gender=normalized_gender,
            disease_ids=resolved_disease_ids,
            symptom_ids=resolved_symptom_ids,
            unknown_ids=resolved_unknown_ids,
            top_k=query_settings.score_pattern_paths.top_k,
        )
        LOGGER.info(
            "Scored direct entity paths: patient_id=%s, source_count=%s, path_count=%s, scored_path_count=%s, missing_source_count=%s",
            normalized_patient_id,
            direct_score_result.get("source_count"),
            direct_score_result.get("path_count"),
            direct_score_result.get("scored_path_count"),
            len(direct_score_result.get("missing_sources") or []),
        )
        missing_sources = direct_score_result.get("missing_sources")
        if isinstance(missing_sources, list) and missing_sources:
            LOGGER.warning(
                "Some direct entity sources were not found in local path cache: patient_id=%s, missing_sources=%s",
                normalized_patient_id,
                missing_sources,
            )
        direct_score_output_paths = save_scored_direct_entity_result(
            direct_score_result,
            scored_paths_dir,
            config_path=resolved_config_path,
        )
        candidate_cache_context = build_direct_entity_candidate_cache_context(
            resolved_config_path,
            scored_result=direct_score_result,
            disease_course_window_days=candidate_window_days,
        )
        candidate_user_cache_context = build_direct_entity_topk_candidate_user_cache_context(
            resolved_config_path,
            source_id=str(direct_score_result.get("source_id") or normalized_patient_id),
            base_date=base_date,
            candidate_cache_context=candidate_cache_context,
        )
        cached_candidate_result = load_cached_topk_candidate_result(
            candidate_user_cache_context,
            candidates_dir=candidates_dir,
            request_base_date=base_date,
        )
        if cached_candidate_result is not None:
            candidate_result = cached_candidate_result
            LOGGER.info(
                "Direct entity topK candidates cache hit: patient_id=%s, candidate_count=%s, data_path=%s",
                normalized_patient_id,
                candidate_result.get("candidate_count"),
                candidate_result.get("user_cache_data_path"),
            )
        else:
            candidate_result = (
                SimilarUserCandidateService()
                .aggregate_candidates_from_direct_entity_scored_result(
                    direct_score_result,
                    candidate_top_k=candidate_top_k,
                )
            )
            candidate_result["cache_context"] = candidate_cache_context
            candidate_result["user_cache_context"] = candidate_user_cache_context
            candidate_result["user_cache_hit"] = False
            save_similar_user_candidates_result(
                candidate_result,
                output_dir=candidates_dir,
            )
            LOGGER.info(
                "Aggregated direct entity candidates: patient_id=%s, pre_score_candidate_count=%s, candidate_count=%s",
                normalized_patient_id,
                candidate_result.get("pre_score_candidate_count"),
                candidate_result.get("candidate_count"),
            )
    else:
        LOGGER.info(
            "Skipping direct entity path scoring because no disease/symptom/unknown IDs were supplied: patient_id=%s",
            normalized_patient_id,
        )

    with Neo4jClient.from_config(resolved_config_path) as client:
        user_service = UserService(
            kg_repository=KgRepository(
                client=client,
                config_path=resolved_config_path,
            )
        )
        if int(candidate_result.get("candidate_count") or 0) <= 0:
            fallback_reason = (
                missing_entity_reason
                if not has_direct_entities
                else "no_direct_entity_candidates"
            )
            prediction_result = DirectEntityFallbackPredictionService(
                user_service=user_service,
            ).predict(
                patient_id=normalized_patient_id,
                base_date=base_date,
                age=age,
                education=normalized_education,
                gender=normalized_gender,
                task_top_k=resolved_task_top_k,
                reason=fallback_reason,
            )
            LOGGER.info(
                "Completed fallback task prediction: patient_id=%s, fallback_level=%s, predicted_task_count=%s",
                normalized_patient_id,
                prediction_result.get("candidate_source", {}).get("fallback_level"),
                len(prediction_result.get("predicted_training_tasks") or []),
            )
            return {
                "patient_id": normalized_patient_id,
                "source_parameter": "manual_profile",
                "base_date": base_date,
                "config_path": str(resolved_config_path),
                "entity_name_resolution": entity_name_resolution,
                "direct_entity_scoring": {
                    "should_score": direct_score_result.get("should_score"),
                    "reason": direct_score_result.get("reason"),
                    "path_count": direct_score_result.get("path_count"),
                    "scored_path_count": direct_score_result.get("scored_path_count"),
                    "top_k": direct_score_result.get("top_k"),
                    "output_paths": [
                        {key: str(value) for key, value in item.items()}
                        for item in direct_score_output_paths
                    ],
                },
                "direct_entity_candidate_result": candidate_result,
                "training_task_prediction": prediction_result,
            }

        llm_client = LlmClient.from_config(resolved_config_path) if use_llm else None
        prediction_service = TrainingTaskPredictionService(
            user_service=user_service,
            llm_client=llm_client,
            prompt_candidate_compression_enabled=(
                query_settings.training_task_prediction.prompt_candidate_compression_enabled
            ),
            prompt_template_name=(
                query_settings.direct_entity_task_prediction.prompt_template_name
            ),
            similar_user_game_counts_weighting_enabled=(
                query_settings.training_task_prediction.similar_user_game_counts_weighting_enabled
            ),
            similar_user_game_counts_weighted_sort_enabled=(
                query_settings.training_task_prediction.similar_user_game_counts_weighted_sort_enabled
            ),
        )
        prediction_result = prediction_service.predict_from_direct_entity_candidates(
            patient_id=normalized_patient_id,
            candidate_result=candidate_result,
            base_date=base_date,
            window_days=candidate_window_days,
            target_profile={
                "age": age,
                "education": normalized_education,
                "gender": normalized_gender,
            },
            target_entities={
                "disease_ids": resolved_disease_ids,
                "symptom_ids": resolved_symptom_ids,
                "unknown_ids": resolved_unknown_ids,
                "disease_names": resolved_disease_names,
                "entity_name_resolution": entity_name_resolution,
            },
            task_top_k=resolved_task_top_k,
            use_llm=use_llm,
            include_prompt=include_prompt,
        )

    predicted_tasks = prediction_result.get("predicted_training_tasks")
    LOGGER.info(
        "Completed direct entity task prediction: patient_id=%s, candidate_count=%s, candidate_training_task_count=%s, predicted_task_count=%s",
        normalized_patient_id,
        candidate_result.get("candidate_count"),
        len(prediction_result.get("candidate_training_tasks") or []),
        len(predicted_tasks if isinstance(predicted_tasks, list) else []),
    )

    return {
        "patient_id": normalized_patient_id,
        "source_parameter": "manual_profile",
        "base_date": base_date,
        "config_path": str(resolved_config_path),
        "entity_name_resolution": entity_name_resolution,
        "direct_entity_scoring": {
            "should_score": direct_score_result.get("should_score"),
            "reason": direct_score_result.get("reason"),
            "path_count": direct_score_result.get("path_count"),
            "scored_path_count": direct_score_result.get("scored_path_count"),
            "top_k": direct_score_result.get("top_k"),
            "output_paths": [
                {key: str(value) for key, value in item.items()}
                for item in direct_score_output_paths
            ],
        },
        "direct_entity_candidate_result": candidate_result,
        "training_task_prediction": prediction_result,
    }


def summarize_prediction_result(
    result: dict[str, Any],
    *,
    output_level: str,
) -> dict[str, Any]:
    """Build compact CLI output."""
    prediction = result.get("training_task_prediction")
    if not isinstance(prediction, dict):
        prediction = {}
    tasks = prediction.get("predicted_training_tasks")
    if not isinstance(tasks, list):
        tasks = []
    if output_level == "ids":
        return {
            "patient_id": result.get("patient_id"),
            "predicted_training_task_ids": [
                task.get("game_id") for task in tasks if isinstance(task, dict)
            ],
        }
    if output_level == "scores":
        return {
            "patient_id": result.get("patient_id"),
            "predicted_training_tasks": tasks,
        }
    return result


def normalize_direct_entity_gender(value: object) -> str:
    """Normalize direct-entity CLI gender input into KG-facing text."""
    return normalize_algorithm_request_gender(value)


def normalize_direct_entity_education(value: object) -> str:
    """Normalize direct-entity CLI education input into KG-facing text."""
    return normalize_algorithm_request_education(value)


def _score_direct_entity_paths_with_auto_refresh(
    *,
    config_path: str | Path,
    patient_id: str,
    base_date: str,
    age: int | str,
    education: str,
    gender: str,
    disease_ids: list[str],
    symptom_ids: list[str],
    unknown_ids: list[str],
    top_k: int | None,
) -> dict[str, Any]:
    try:
        result = score_direct_entity_paths(
            config_path=config_path,
            patient_id=patient_id,
            base_date=base_date,
            age=age,
            education=education,
            gender=gender,
            disease_ids=disease_ids,
            symptom_ids=symptom_ids,
            unknown_ids=unknown_ids,
            top_k=top_k,
            force_manual_input=True,
        )
    except FileNotFoundError:
        LOGGER.info(
            "Direct raw path index missing; rebuilding direct entity paths before scoring: patient_id=%s, base_date=%s",
            patient_id,
            base_date,
        )
        build_direct_entity_paths(
            config_path=config_path,
            disease_ids=disease_ids,
            symptom_ids=symptom_ids,
            unknown_ids=unknown_ids,
        )
        return score_direct_entity_paths(
            config_path=config_path,
            patient_id=patient_id,
            base_date=base_date,
            age=age,
            education=education,
            gender=gender,
            disease_ids=disease_ids,
            symptom_ids=symptom_ids,
            unknown_ids=unknown_ids,
            top_k=top_k,
            force_manual_input=True,
        )

    missing_sources = result.get("missing_sources")
    if isinstance(missing_sources, list) and missing_sources:
        refresh_ids = _direct_refresh_ids_from_missing_sources(missing_sources)
        LOGGER.info(
            "Direct raw paths missing or expired; rebuilding before scoring: patient_id=%s, missing_sources=%s",
            patient_id,
            missing_sources,
        )
        build_direct_entity_paths(
            config_path=config_path,
            disease_ids=refresh_ids["disease_ids"],
            symptom_ids=refresh_ids["symptom_ids"],
            unknown_ids=refresh_ids["unknown_ids"],
        )
        result = score_direct_entity_paths(
            config_path=config_path,
            patient_id=patient_id,
            base_date=base_date,
            age=age,
            education=education,
            gender=gender,
            disease_ids=disease_ids,
            symptom_ids=symptom_ids,
            unknown_ids=unknown_ids,
            top_k=top_k,
            force_manual_input=True,
        )
    return result


def _direct_refresh_ids_from_missing_sources(
    missing_sources: list[object],
) -> dict[str, list[str]]:
    refresh_ids = {
        "disease_ids": [],
        "symptom_ids": [],
        "unknown_ids": [],
    }
    for item in missing_sources:
        if not isinstance(item, dict):
            continue
        source_id = item.get("source_id")
        pattern = item.get("pattern")
        if not isinstance(source_id, str) or not source_id.strip():
            continue
        if pattern == "DISEASE_TASKSET_PATIENT":
            refresh_ids["disease_ids"].append(source_id.strip())
        elif pattern == "SYMPTOM_TASKSET_PATIENT":
            refresh_ids["symptom_ids"].append(source_id.strip())
        elif pattern == "UNKNOWN_TASKSET_PATIENT":
            refresh_ids["unknown_ids"].append(source_id.strip())
    return {key: _dedupe_texts(value) for key, value in refresh_ids.items()}


def resolve_direct_entity_names(
    resolver: DirectEntityNameResolver,
    entity_names: list[str],
) -> dict[str, list[dict[str, Any]]]:
    """Resolve disease-name input against KG Disease/Symptom/Unknown nodes."""
    return resolver.resolve_names(entity_names)


def _ids_by_type(
    resolution: dict[str, list[dict[str, Any]]],
    entity_type: str,
) -> list[str]:
    ids: list[str] = []
    for item in resolution.get("resolved") or []:
        if not isinstance(item, dict):
            continue
        if item.get("entity_type") != entity_type:
            continue
        entity_id = _normalize_optional_text(item.get("entity_id"))
        if entity_id is not None:
            ids.append(entity_id)
    return ids


def _flatten(values: list[list[str]] | None) -> list[str]:
    flattened: list[str] = []
    for group in values or []:
        for item in group:
            text = _normalize_optional_text(item)
            if text is not None:
                flattened.append(text)
    return flattened


def _dedupe_texts(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _normalize_optional_text(value)
        if text is None or text in seen:
            continue
        deduped.append(text)
        seen.add(text)
    return deduped


def _normalize_required_text(value: object, field_name: str) -> str:
    text = _normalize_optional_text(value)
    if text is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return text


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


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
    """Run direct-entity-only task prediction."""
    args = parse_args()
    try:
        result = predict_training_tasks_from_direct_entity(
            patient_id=args.patient_id,
            base_date=args.base_date,
            age=args.age,
            education=args.education,
            gender=args.gender,
            disease_ids=_flatten(args.disease_id),
            disease_names=_flatten(args.disease_name),
            symptom_ids=_flatten(args.symptom_id),
            unknown_ids=_flatten(args.unknown_id),
            config_path=args.config,
            scored_paths_dir=args.scored_paths_dir,
            candidates_dir=args.candidates_dir,
            use_llm=not args.dry_run,
            include_prompt=args.include_prompt,
            task_top_k=args.task_top_k,
        )
        output = summarize_prediction_result(result, output_level=args.output_level)
        if args.output:
            _write_json_atomic(Path(args.output), result)
        LOGGER.info(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    except Exception as exc:
        LOGGER.exception("Direct entity task prediction failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
