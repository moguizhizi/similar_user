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
from scripts.predict_training_tasks_from_profiles import (  # noqa: E402
    DEFAULT_PROFILE_PATH,
    load_profiles,
)
from similar_user.services.task_recommendation_validation import (  # noqa: E402
    validate_training_task_recommendation,
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
    parser.add_argument("--task-top-k", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int)
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
    resolved_task_top_k = task_top_k or query_settings.training_task_prediction.task_top_k
    resolved_workers = workers or evaluation_settings.workers or 1

    details = run_profile_evaluations(
        profiles,
        config_path=config_path,
        scored_paths_dir=scored_paths_dir,
        task_top_k=resolved_task_top_k,
        use_llm=use_llm,
        workers=resolved_workers,
        validation_mode=evaluation_settings.validation_mode,
        score_url=evaluation_settings.score_validation_url,
        csv_path=evaluation_settings.algorithm_request_results_csv,
        timeout_seconds=evaluation_settings.score_validation_timeout,
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
    validation_mode: str,
    score_url: str,
    csv_path: str | Path,
    timeout_seconds: float,
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
                validation_mode=validation_mode,
                score_url=score_url,
                csv_path=csv_path,
                timeout_seconds=timeout_seconds,
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
                validation_mode=validation_mode,
                score_url=score_url,
                csv_path=csv_path,
                timeout_seconds=timeout_seconds,
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
    validation_mode: str,
    score_url: str,
    csv_path: str | Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    """Evaluate one direct-entity profile."""
    started_at = time.perf_counter()
    patient_id = str(profile.get("patient_id") or "").strip()
    base_date = str(profile.get("base_date") or "").strip()
    try:
        result = predict_training_tasks_from_direct_entity(
            patient_id=patient_id,
            base_date=base_date,
            age=profile.get("age"),
            education=profile.get("education"),
            gender=profile.get("gender"),
            disease_ids=normalize_profile_list(profile.get("disease_ids")),
            disease_names=[
                str(name)
                for name in profile.get("disease_names") or []
                if str(name).strip()
            ],
            symptom_ids=normalize_profile_list(profile.get("symptom_ids")),
            unknown_ids=normalize_profile_list(profile.get("unknown_ids")),
            config_path=config_path,
            scored_paths_dir=scored_paths_dir,
            use_llm=use_llm,
            task_top_k=task_top_k,
        )
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
        validation_started_at = time.perf_counter()
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
    except Exception as exc:
        return {
            "patient_id": patient_id,
            "base_date": base_date,
            "status": "failed",
            "validation_mode": validation_mode,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        }

    return {
        "patient_id": patient_id,
        "base_date": base_date,
        "status": validation_result["status"],
        "validation_mode": validation_result["validation_mode"],
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
        "prediction_started_at_seconds": round(started_at, 6),
        "prediction_finished_at_seconds": round(prediction_finished_at, 6),
        "validation_started_at_seconds": round(validation_started_at, 6),
        "validation_finished_at_seconds": round(validation_finished_at, 6),
        "prediction_elapsed_seconds": prediction_elapsed_seconds,
        "validation_elapsed_seconds": validation_elapsed_seconds,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
    }


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
            task_top_k=args.task_top_k,
            use_llm=not args.dry_run,
            workers=args.workers,
        )
    except Exception as exc:
        LOGGER.exception("Direct entity profile evaluation failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
