"""Evaluate direct-entity predictions over exported profile JSONL records."""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import tempfile
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import load_query_settings  # noqa: E402
from scripts.evaluate_predict_training_tasks import (  # noqa: E402
    build_coverage_diagnostics,
    count_candidate_training_tasks,
    count_similar_user_game_count_tasks,
    extract_predicted_game_ids,
    summarize_evaluation_details,
)
from scripts.predict_training_tasks_from_direct_entity import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    DEFAULT_SCORED_OUTPUT_DIR,
    predict_training_tasks_from_direct_entity,
)
from scripts.predict_training_tasks import write_prompt_to_file  # noqa: E402
from scripts.predict_training_tasks_unified import (  # noqa: E402
    predict_training_tasks_unified,
)
from scripts.predict_training_tasks_from_profiles import (  # noqa: E402
    DEFAULT_PROFILE_PATH,
    load_profiles,
)
from similar_user.services.task_recommendation_validation import (  # noqa: E402
    validate_training_task_recommendation,
)
from similar_user.services.task_prediction_failure import (  # noqa: E402
    build_prediction_failure_metadata,
    build_validation_failure_metadata,
    build_validation_success_metadata,
    prediction_metadata_from_nested_result,
)
from similar_user.utils.logger import get_logger  # noqa: E402


LOGGER = get_logger(__name__)
DEFAULT_OUTPUT_DIR = Path("data/evaluation_direct_entity_profiles")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Evaluate direct-entity predictions from profile JSONL."
    )
    parser.add_argument("--profiles", default=str(DEFAULT_PROFILE_PATH))
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument("--scored-paths-dir", default=str(DEFAULT_SCORED_OUTPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument(
        "--summary-file",
        default="predict_training_tasks_summary.json",
    )
    parser.add_argument(
        "--details-file",
        default="predict_training_tasks_details.jsonl",
    )
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--patient-id",
        action="append",
        default=[],
        help="Optional patient ID filter. Can be supplied multiple times.",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int)
    parser.add_argument(
        "--prediction-mode",
        choices=("direct_entity", "unified"),
        default="direct_entity",
        help="Prediction function used for each profile.",
    )
    parser.add_argument(
        "--output-level",
        choices=("ids", "scores", "full"),
        default="scores",
        help="Reserved for parity with profile prediction CLI.",
    )
    return parser.parse_args()


def evaluate_direct_entity_profiles(
    *,
    profiles_path: str | Path = DEFAULT_PROFILE_PATH,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    summary_file: str = "predict_training_tasks_summary.json",
    details_file: str = "predict_training_tasks_details.jsonl",
    limit: int | None = None,
    patient_ids: list[str] | None = None,
    task_top_k: int | None = None,
    use_llm: bool = True,
    workers: int | None = None,
    prediction_mode: str = "direct_entity",
    pattern: str | None = None,
    query_family: str | None = None,
    skip_path_build: bool = False,
    skip_path_scoring: bool = False,
) -> dict[str, Any]:
    """Run direct-entity predictions and write grid-compatible evaluation outputs."""
    started_at = time.perf_counter()
    profiles = select_profiles(
        load_profiles(profiles_path),
        patient_ids=patient_ids,
        limit=limit,
    )
    query_settings = load_query_settings(config_path)
    evaluation_settings = query_settings.training_task_evaluation
    validation_enabled = getattr(evaluation_settings, "validation_enabled", True)
    if not isinstance(validation_enabled, bool):
        validation_enabled = True
    resolved_task_top_k = task_top_k or query_settings.training_task_prediction.task_top_k
    resolved_workers = workers or evaluation_settings.workers or 1
    save_prompt = query_settings.training_task_prediction.save_prompt_enabled
    prompt_output_dir = Path(output_dir) / "prompts"

    details = run_profile_evaluations(
        profiles,
        config_path=config_path,
        scored_paths_dir=scored_paths_dir,
        task_top_k=resolved_task_top_k,
        use_llm=use_llm,
        workers=resolved_workers,
        prediction_mode=prediction_mode,
        pattern=pattern,
        query_family=query_family,
        skip_path_build=skip_path_build,
        skip_path_scoring=skip_path_scoring,
        validation_enabled=validation_enabled,
        validation_mode=evaluation_settings.validation_mode,
        score_url=evaluation_settings.score_validation_url,
        csv_path=evaluation_settings.algorithm_request_results_csv,
        timeout_seconds=evaluation_settings.score_validation_timeout,
        save_prompt=save_prompt,
        prompt_output_dir=prompt_output_dir,
    )
    summary = summarize_evaluation_details(details)
    summary.update(
        {
            "profiles_path": str(profiles_path),
            "config_path": str(config_path),
            "total_count": len(details),
            "workers": resolved_workers,
            "task_top_k": resolved_task_top_k,
            "use_llm": use_llm,
            "prediction_mode": prediction_mode,
            "validation_enabled": validation_enabled,
            "save_prompt_enabled": save_prompt,
            "prompt_output_dir": str(prompt_output_dir) if save_prompt else None,
            "query_family": query_family,
            "route_counts": build_route_counts(details),
            "batch_elapsed_seconds": round(time.perf_counter() - started_at, 3),
        }
    )

    resolved_output_dir = Path(output_dir)
    details_path = resolved_output_dir / details_file
    summary_path = resolved_output_dir / summary_file
    write_jsonl(details_path, details)
    write_json(summary_path, summary)
    summary["details_path"] = str(details_path)
    summary["summary_path"] = str(summary_path)
    LOGGER.info(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return summary


def run_profile_evaluations(
    profiles: list[dict[str, Any]],
    *,
    config_path: str | Path,
    scored_paths_dir: str | Path,
    task_top_k: int,
    use_llm: bool,
    workers: int,
    prediction_mode: str,
    pattern: str | None,
    query_family: str | None,
    skip_path_build: bool,
    skip_path_scoring: bool,
    validation_enabled: bool,
    validation_mode: str,
    score_url: str,
    csv_path: str | Path,
    timeout_seconds: float,
    save_prompt: bool = False,
    prompt_output_dir: str | Path | None = None,
) -> list[dict[str, Any]]:
    """Evaluate profiles sequentially or with a small thread pool."""
    if workers <= 1:
        details = []
        for index, profile in enumerate(profiles, start=1):
            detail = evaluate_profile(
                profile,
                config_path=config_path,
                scored_paths_dir=scored_paths_dir,
                task_top_k=task_top_k,
                use_llm=use_llm,
                prediction_mode=prediction_mode,
                pattern=pattern,
                query_family=query_family,
                skip_path_build=skip_path_build,
                skip_path_scoring=skip_path_scoring,
                validation_enabled=validation_enabled,
                validation_mode=validation_mode,
                score_url=score_url,
                csv_path=csv_path,
                timeout_seconds=timeout_seconds,
                save_prompt=save_prompt,
                prompt_output_dir=prompt_output_dir,
            )
            details.append(detail)
            LOGGER.info(
                "Evaluated direct entity prediction: index=%s/%s, patient_id=%s, status=%s",
                index,
                len(profiles),
                detail.get("patient_id"),
                detail.get("status"),
            )
        return details

    details_by_index: dict[int, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                evaluate_profile,
                profile,
                config_path=config_path,
                scored_paths_dir=scored_paths_dir,
                task_top_k=task_top_k,
                use_llm=use_llm,
                prediction_mode=prediction_mode,
                pattern=pattern,
                query_family=query_family,
                skip_path_build=skip_path_build,
                skip_path_scoring=skip_path_scoring,
                validation_enabled=validation_enabled,
                validation_mode=validation_mode,
                score_url=score_url,
                csv_path=csv_path,
                timeout_seconds=timeout_seconds,
                save_prompt=save_prompt,
                prompt_output_dir=prompt_output_dir,
            ): index
            for index, profile in enumerate(profiles)
        }
        for future in as_completed(futures):
            index = futures[future]
            detail = future.result()
            details_by_index[index] = detail
            LOGGER.info(
                "Evaluated direct entity prediction: index=%s/%s, patient_id=%s, status=%s",
                index + 1,
                len(profiles),
                detail.get("patient_id"),
                detail.get("status"),
            )
    return [details_by_index[index] for index in range(len(profiles))]


def evaluate_profile(
    profile: dict[str, Any],
    *,
    config_path: str | Path,
    scored_paths_dir: str | Path,
    task_top_k: int,
    use_llm: bool,
    prediction_mode: str,
    pattern: str | None,
    query_family: str | None,
    skip_path_build: bool,
    skip_path_scoring: bool,
    validation_enabled: bool,
    validation_mode: str,
    score_url: str,
    csv_path: str | Path,
    timeout_seconds: float,
    save_prompt: bool = False,
    prompt_output_dir: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate one direct-entity profile."""
    started_at = time.perf_counter()
    patient_id = str(profile.get("patient_id") or "").strip()
    base_date = str(profile.get("base_date") or "").strip()
    current_stage = "prediction"
    result: dict[str, Any] | None = None
    prompt_path: Path | None = None
    try:
        routed_result = predict_profile_training_tasks(
            profile,
            config_path=config_path,
            scored_paths_dir=scored_paths_dir,
            task_top_k=task_top_k,
            use_llm=use_llm,
            prediction_mode=prediction_mode,
            pattern=pattern,
            query_family=query_family,
            skip_path_build=skip_path_build,
            skip_path_scoring=skip_path_scoring,
            include_prompt=save_prompt,
        )
        result = unwrap_unified_result(routed_result)
        predicted_game_ids = extract_predicted_game_ids(result)
        similar_user_game_counts_task_count = count_similar_user_game_count_tasks(
            result
        )
        candidate_training_tasks_count = count_candidate_training_tasks(result)
        coverage_diagnostics = build_coverage_diagnostics(
            predicted_game_ids,
            [],
            result,
        )
        prediction_finished_at = time.perf_counter()
        prediction_elapsed_seconds = round(prediction_finished_at - started_at, 3)
        prompt_path = maybe_write_prompt(
            result,
            patient_id=patient_id,
            base_date=base_date,
            save_prompt=save_prompt,
            prompt_output_dir=prompt_output_dir,
        )
        current_stage = "validation"
        validation_started_at = time.perf_counter()
        if validation_enabled:
            validation_result = validate_training_task_recommendation(
                validation_mode=validation_mode,
                prediction_result=result,
                patient_id=patient_id,
                predicted_game_ids=predicted_game_ids,
                actual_game_ids=[],
                score_url=score_url,
                csv_path=csv_path,
                timeout_seconds=timeout_seconds,
            )
            validation_finished_at = time.perf_counter()
            validation_elapsed_seconds = round(
                validation_finished_at - validation_started_at,
                3,
            )
        else:
            validation_finished_at = validation_started_at
            validation_elapsed_seconds = 0.0
            validation_result = {
                "status": "success_not_validated",
                "validation_mode": validation_mode,
                "reason": "validation_disabled",
                "matched_game_ids": [],
                "task_hit": None,
                "precision": None,
                "recall": None,
                "f1": None,
                "training_task_score_validation": None,
                "kg_avg_score": None,
                "csv_avg_score": None,
                "score_delta": None,
                "actual_task_count": 0,
                "matched_task_count": 0,
            }
            LOGGER.info(
                "Skipped training task validation: patient_id=%s, "
                "prediction_mode=%s, validation_enabled=False, validation_mode=%s",
                patient_id,
                prediction_mode,
                validation_mode,
            )
    except Exception as exc:
        failure_stage, failure_reason = classify_profile_failure(
            exc,
            current_stage=current_stage,
        )
        if current_stage == "prediction":
            LOGGER.error(
                "Training task prediction failed: patient_id=%s, prediction_mode=%s, "
                "failure_stage=%s, failure_reason=%s, error_type=%s, error_message=%s",
                patient_id,
                prediction_mode,
                failure_stage,
                failure_reason,
                type(exc).__name__,
                str(exc),
            )
        else:
            LOGGER.error(
                "Training task validation failed: patient_id=%s, prediction_mode=%s, "
                "failure_stage=%s, failure_reason=%s, error_type=%s, error_message=%s",
                patient_id,
                prediction_mode,
                failure_stage,
                failure_reason,
                type(exc).__name__,
                str(exc),
            )
        detail = {
            "patient_id": patient_id,
            "base_date": base_date,
            "status": "failed",
            "prediction_mode": prediction_mode,
            "failure_stage": failure_stage,
            "failure_reason": failure_reason,
            "validation_enabled": validation_enabled,
            "validation_mode": validation_mode,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        }
        if current_stage == "prediction":
            detail.update(build_prediction_failure_metadata(exc))
            prompt_path = maybe_write_exception_prompt(
                exc,
                patient_id=patient_id,
                base_date=base_date,
                save_prompt=save_prompt,
                prompt_output_dir=prompt_output_dir,
            )
            if prompt_path is not None:
                detail["prompt_path"] = str(prompt_path)
        else:
            detail.update(
                prediction_metadata_from_nested_result(result or {})
                or {
                    "prediction_status": "success",
                    "fallback_used": False,
                    "fallback_reason": None,
                }
            )
            detail.update(build_validation_failure_metadata(exc))
            if prompt_path is not None:
                detail["prompt_path"] = str(prompt_path)
        return detail

    return {
        "patient_id": patient_id,
        "base_date": base_date,
        **prediction_metadata_from_nested_result(result),
        **build_validation_success_metadata(),
        "prediction_mode": prediction_mode,
        "route": routed_result.get("route"),
        "patient_exists": routed_result.get("patient_exists"),
        "status": validation_result["status"],
        "validation_mode": validation_result["validation_mode"],
        "validation_enabled": validation_enabled,
        "reason": validation_result.get("reason"),
        "predicted_game_ids": predicted_game_ids,
        "actual_game_ids": [],
        "matched_game_ids": validation_result.get("matched_game_ids", []),
        "task_hit": validation_result.get("task_hit"),
        "precision": validation_result.get("precision"),
        "recall": validation_result.get("recall"),
        "f1": validation_result.get("f1"),
        "training_task_score_validation": validation_result.get(
            "training_task_score_validation"
        ),
        "kg_avg_score": validation_result.get("kg_avg_score"),
        "csv_avg_score": validation_result.get("csv_avg_score"),
        "score_delta": validation_result.get("score_delta"),
        "predicted_task_count": len(predicted_game_ids),
        "actual_task_count": validation_result["actual_task_count"],
        "matched_task_count": validation_result["matched_task_count"],
        "similar_user_game_counts_task_count": similar_user_game_counts_task_count,
        "candidate_training_tasks_count": candidate_training_tasks_count,
        "coverage_diagnostics": coverage_diagnostics,
        "prompt_path": str(prompt_path) if prompt_path is not None else None,
        "prediction_started_at_seconds": round(started_at, 6),
        "prediction_finished_at_seconds": round(prediction_finished_at, 6),
        "validation_started_at_seconds": round(validation_started_at, 6),
        "validation_finished_at_seconds": round(validation_finished_at, 6),
        "prediction_elapsed_seconds": prediction_elapsed_seconds,
        "validation_elapsed_seconds": validation_elapsed_seconds,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
    }



def maybe_write_prompt(
    result: dict[str, Any],
    *,
    patient_id: str,
    base_date: str,
    save_prompt: bool,
    prompt_output_dir: str | Path | None,
) -> Path | None:
    """Persist the generated prompt when enabled, without failing evaluation."""
    if not save_prompt:
        return None
    if prompt_output_dir is None:
        return None
    try:
        prompt_result = dict(result)
        if not prompt_result.get("patient_id"):
            prompt_result["patient_id"] = patient_id
        return write_prompt_to_file(
            prompt_result,
            output_dir=prompt_output_dir,
            base_date=base_date,
        )
    except Exception as exc:
        LOGGER.warning(
            "Failed to save training-task prediction prompt: patient_id=%s, error=%s",
            patient_id,
            exc,
        )
        return None


def maybe_write_exception_prompt(
    exc: Exception,
    *,
    patient_id: str,
    base_date: str,
    save_prompt: bool,
    prompt_output_dir: str | Path | None,
) -> Path | None:
    """Persist prompt attached to prediction exceptions when present."""
    llm_prompt = getattr(exc, "llm_prompt", None)
    if not save_prompt or not isinstance(llm_prompt, str) or not llm_prompt.strip():
        return None
    if prompt_output_dir is None:
        return None
    try:
        return write_prompt_to_file(
            {
                "training_task_prediction": {
                    "patient_id": patient_id,
                    "llm_prompt": llm_prompt,
                }
            },
            output_dir=prompt_output_dir,
            base_date=base_date,
        )
    except Exception as prompt_exc:
        LOGGER.warning(
            "Failed to save failed prediction prompt: patient_id=%s, error=%s",
            patient_id,
            prompt_exc,
        )
        return None

def classify_profile_failure(
    exc: Exception,
    *,
    current_stage: str,
) -> tuple[str, str]:
    """Return coarse failure stage/reason for profile prediction logs."""
    message = str(exc).lower()
    if current_stage == "validation":
        if "timeout" in message:
            return "validation", "validation_timeout"
        return "validation", "validation_error"
    if "education is required" in message:
        return "input", "missing_education"
    if "gender is required" in message:
        return "input", "missing_gender"
    if "age is required" in message:
        return "input", "missing_age"
    if "no_resolved_entity_names" in message:
        return "entity_resolution", "no_resolved_entity_names"
    if "missing_entity_input" in message:
        return "input", "missing_entity_input"
    if "candidate" in message:
        return "candidate", "candidate_error"
    if "llm" in message or "prompt" in message:
        return "llm", "llm_error"
    if "timeout" in message:
        return "prediction", "prediction_timeout"
    return "prediction", "prediction_error"


def predict_profile_training_tasks(
    profile: dict[str, Any],
    *,
    config_path: str | Path,
    scored_paths_dir: str | Path,
    task_top_k: int,
    use_llm: bool,
    prediction_mode: str,
    pattern: str | None = None,
    query_family: str | None = None,
    skip_path_build: bool = False,
    skip_path_scoring: bool = False,
    include_prompt: bool = False,
) -> dict[str, Any]:
    """Run one profile through direct-entity or unified prediction."""
    patient_id = str(profile.get("patient_id") or "").strip()
    base_date = str(profile.get("base_date") or "").strip()
    disease_names = [
        str(name) for name in profile.get("disease_names") or [] if str(name).strip()
    ]
    common_kwargs = {
        "patient_id": patient_id,
        "base_date": base_date,
        "age": profile.get("age"),
        "education": profile.get("education"),
        "gender": profile.get("gender"),
        "disease_ids": normalize_profile_list(profile.get("disease_ids")),
        "disease_names": disease_names,
        "symptom_ids": normalize_profile_list(profile.get("symptom_ids")),
        "unknown_ids": normalize_profile_list(profile.get("unknown_ids")),
        "config_path": config_path,
        "use_llm": use_llm,
        "task_top_k": task_top_k,
        "include_prompt": include_prompt,
    }
    if prediction_mode == "direct_entity":
        result = predict_training_tasks_from_direct_entity(
            **common_kwargs,
            scored_paths_dir=scored_paths_dir,
        )
        return {
            "route": "direct_entity_path",
            "patient_exists": False,
            "result": result,
        }
    if prediction_mode == "unified":
        unified_kwargs = {
            **common_kwargs,
            "query_family": query_family,
            "skip_path_build": skip_path_build,
            "skip_path_scoring": skip_path_scoring,
        }
        if pattern is not None:
            unified_kwargs["pattern"] = pattern
        return predict_training_tasks_unified(**unified_kwargs)
    raise ValueError(f"Unsupported prediction_mode: {prediction_mode}")


def unwrap_unified_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return the inner prediction payload from a routed result."""
    inner = result.get("result")
    return inner if isinstance(inner, dict) else result


def build_route_counts(details: list[dict[str, Any]]) -> dict[str, int]:
    """Count evaluated profiles by unified route."""
    counts: dict[str, int] = {}
    for detail in details:
        route = detail.get("route")
        if not isinstance(route, str) or not route:
            route = "unknown"
        counts[route] = counts.get(route, 0) + 1
    return counts


def select_profiles(
    profiles: list[dict[str, Any]],
    *,
    patient_ids: list[str] | None,
    limit: int | None,
) -> list[dict[str, Any]]:
    """Apply optional patient ID filter and limit."""
    requested_patient_ids = {
        str(patient_id).strip() for patient_id in patient_ids or [] if str(patient_id).strip()
    }
    if requested_patient_ids:
        profiles = [
            profile
            for profile in profiles
            if str(profile.get("patient_id") or "").strip() in requested_patient_ids
        ]
    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be a positive integer.")
        profiles = profiles[:limit]
    return profiles


def normalize_profile_list(value: object) -> list[str]:
    """Normalize optional profile entity ID lists."""
    if value is None:
        return []
    values = value if isinstance(value, list) else [value]
    return [str(item).strip() for item in values if str(item).strip()]


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    """Write detail records atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        for record in records:
            temp_file.write(json.dumps(record, ensure_ascii=False, default=str))
            temp_file.write("\n")
        temp_path = Path(temp_file.name)
    os.replace(temp_path, path)


def write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write one JSON object atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        json.dump(payload, temp_file, ensure_ascii=False, indent=2, default=str)
        temp_path = Path(temp_file.name)
    os.replace(temp_path, path)


def main() -> int:
    """Run direct-entity profile evaluation."""
    args = parse_args()
    try:
        evaluate_direct_entity_profiles(
            profiles_path=args.profiles,
            config_path=args.config,
            scored_paths_dir=args.scored_paths_dir,
            output_dir=args.output_dir,
            summary_file=args.summary_file,
            details_file=args.details_file,
            limit=args.limit,
            patient_ids=args.patient_id,
            use_llm=not args.dry_run,
            workers=args.workers,
            prediction_mode=args.prediction_mode,
        )
    except Exception as exc:
        LOGGER.exception("Direct entity profile evaluation failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
