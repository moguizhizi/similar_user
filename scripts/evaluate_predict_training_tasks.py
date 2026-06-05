"""Evaluate same-day training-task predictions over a patient list.

这个脚本按历史回测口径评估 `predict_training_tasks`：

1. 只使用 `base_date` 之前的数据生成预测。
2. 查询目标用户在 `base_date` 当天的真实训练任务。
3. 不关心预测任务排序，只比较预测任务集合和真实任务集合是否相交。

常用执行方式：

    python scripts/evaluate_predict_training_tasks.py --base-date 2022-05-22
    python scripts/evaluate_predict_training_tasks.py --patient-id 40 --base-date 2022-05-22
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import timedelta
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
from similar_user.domain.graph_schema import (
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
)
from similar_user.services.task_prediction import (
    CURRENT_TASK_PREDICTION_PROMPT_TEMPLATE_NAME,
    DEFAULT_TASK_TOP_K,
    build_game_counts_from_history,
    parse_date_value,
)
from similar_user.services.task_prediction_failure import (
    build_prediction_failure_metadata,
    build_validation_success_metadata,
    prediction_metadata_from_nested_result,
    summarize_prediction_visibility,
)
from similar_user.services.task_recommendation_validation import (
    calculate_f1,
    evaluate_prediction_sets,
    safe_divide,
    validate_training_task_recommendation,
)
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger

from scripts.predict_training_tasks import (
    DEFAULT_PROMPT_OUTPUT_DIR,
    run_end_to_end_training_task_prediction,
    write_prompt_to_file,
)
from scripts.export_patient_ids_with_training_on_date import (
    DEFAULT_OUTPUT_DIR as DEFAULT_PATIENT_IDS_OUTPUT_DIR,
    build_patient_ids_output_path,
    export_patient_ids_with_training_on_date,
)
from scripts.run_similar_user_pipeline import EmptyPathResultsError
from scripts.score_pattern_paths import DEFAULT_CONFIG_PATH


LOGGER = get_logger(__name__)
DEFAULT_OUTPUT_DIR = Path("data/evaluation")
DEFAULT_SCORE_CURL_FILE = "training_task_score_requests.sh"


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for same-day prediction evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate same-day training-task prediction metrics."
    )
    parser.add_argument(
        "--patient-id",
        help="Evaluate only this patient_id instead of a file or the full patient list.",
    )
    parser.add_argument(
        "--patient-list-dir",
        default=str(DEFAULT_PATIENT_IDS_OUTPUT_DIR),
        help=(
            "Base directory for patient ID files generated from base_date when "
            "--patient-id is omitted."
        ),
    )
    parser.add_argument(
        "--base-date",
        required=True,
        help="Prediction date; actual labels are tasks on this date.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip the LLM call during prediction.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for summary JSON and detail JSONL outputs.",
    )
    parser.add_argument(
        "--summary-file",
        default="predict_training_tasks_summary.json",
        help="Summary JSON filename under output-dir.",
    )
    parser.add_argument(
        "--details-file",
        default="predict_training_tasks_details.jsonl",
        help="Per-patient detail JSONL filename under output-dir.",
    )
    parser.add_argument(
        "--analysis-file",
        default="predict_training_tasks_analysis.json",
        help="Analysis JSON filename under output-dir.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Evaluate at most this many patient IDs after loading them.",
    )
    return parser.parse_args()


def read_patient_ids(path: str | Path) -> list[str]:
    """Read patient IDs from a plain text file."""
    patient_ids: list[str] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        value = line.strip()
        if not value or value.startswith("#"):
            continue
        patient_ids.append(value)
    return patient_ids


def build_patient_ids_file_from_base_date(
    *,
    base_date: str,
    patient_list_dir: str | Path = DEFAULT_PATIENT_IDS_OUTPUT_DIR,
) -> Path:
    """Build the expected patient ID file path for the evaluation base date."""
    return build_patient_ids_output_path(
        base_date=base_date,
        output_dir=patient_list_dir,
    )


def evaluate_patient(
    patient_id: str,
    *,
    base_date: str,
    user_service: UserService,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    skip_path_build: bool = False,
    skip_path_scoring: bool = False,
    query_family: str | None = None,
    task_top_k: int = DEFAULT_TASK_TOP_K,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Run prediction and compare it with the patient's same-day true tasks."""
    started_at = time.perf_counter()
    query_settings = load_query_settings(config_path)
    evaluation_settings = query_settings.training_task_evaluation
    save_prompt = query_settings.training_task_prediction.save_prompt_enabled
    validation_enabled = getattr(evaluation_settings, "validation_enabled", True)
    if not isinstance(validation_enabled, bool):
        validation_enabled = True
    validation_mode = evaluation_settings.validation_mode
    try:
        if not validation_enabled:
            actual_game_ids = []
        elif validation_mode == "set":
            actual_game_ids = get_actual_game_ids_on_base_date(
                user_service,
                patient_id,
                base_date,
            )
            if not actual_game_ids:
                detail = build_not_evaluable_detail(
                    patient_id=patient_id,
                    base_date=base_date,
                    elapsed_seconds=round(time.perf_counter() - started_at, 3),
                )
                detail["validation_mode"] = validation_mode
                return detail
        elif validation_mode == "score":
            actual_game_ids = []
        else:
            raise ValueError(
                f"Unsupported training task evaluation validation_mode: {validation_mode}."
            )

        prediction_result = run_end_to_end_training_task_prediction(
            patient_id,
            base_date=base_date,
            pattern=pattern,
            config_path=config_path,
            skip_path_build=skip_path_build,
            skip_path_scoring=skip_path_scoring,
            query_family=query_family,
            task_top_k=task_top_k,
            use_llm=use_llm,
            include_prompt=save_prompt,
        )
        prompt_path = None
        if save_prompt:
            prompt_path = write_prompt_to_file(
                prediction_result,
                output_dir=DEFAULT_PROMPT_OUTPUT_DIR,
                base_date=base_date,
            )
        predicted_game_ids = extract_predicted_game_ids(prediction_result)
        actual_game_similar_user_counts = build_actual_game_similar_user_counts(
            actual_game_ids,
            prediction_result,
        )
        predicted_game_similar_user_counts = build_game_similar_user_counts(
            predicted_game_ids,
            prediction_result,
        )
        similar_user_game_counts_task_count = count_similar_user_game_count_tasks(
            prediction_result
        )
        candidate_training_tasks_count = count_candidate_training_tasks(
            prediction_result
        )
        coverage_diagnostics = build_coverage_diagnostics(
            predicted_game_ids,
            actual_game_ids,
            prediction_result,
        )
        prediction_finished_at = time.perf_counter()
        prediction_elapsed_seconds = round(prediction_finished_at - started_at, 3)
        validation_started_at = time.perf_counter()
        if validation_enabled:
            validation_result = validate_training_task_recommendation(
                validation_mode=validation_mode,
                prediction_result=prediction_result,
                patient_id=patient_id,
                predicted_game_ids=predicted_game_ids,
                actual_game_ids=actual_game_ids,
                score_url=evaluation_settings.score_validation_url,
                csv_path=evaluation_settings.algorithm_request_results_csv,
                timeout_seconds=evaluation_settings.score_validation_timeout,
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
                "validation_enabled=False, validation_mode=%s",
                patient_id,
                validation_mode,
            )
    except EmptyPathResultsError as exc:
        detail = build_not_evaluable_detail(
            patient_id=patient_id,
            base_date=base_date,
            elapsed_seconds=round(time.perf_counter() - started_at, 3),
            reason="no_pattern_paths",
            error_message=str(exc),
        )
        detail["validation_mode"] = validation_mode
        detail.update(
            {
                "prediction_status": "failed",
                "prediction_failure_stage": "candidate",
                "prediction_failure_reason": "no_pattern_paths",
                "prediction_error_type": type(exc).__name__,
                "prediction_error_message": str(exc),
                "fallback_used": False,
                "fallback_reason": None,
            }
        )
        return detail
    except Exception as exc:
        prompt_path = None
        llm_prompt = getattr(exc, "llm_prompt", None)
        if save_prompt and isinstance(llm_prompt, str) and llm_prompt.strip():
            try:
                prompt_path = write_prompt_to_file(
                    {
                        "training_task_prediction": {
                            "patient_id": patient_id,
                            "llm_prompt": llm_prompt,
                        }
                    },
                    output_dir=DEFAULT_PROMPT_OUTPUT_DIR,
                    base_date=base_date,
                )
            except Exception as prompt_exc:
                LOGGER.warning(
                    "Failed to save prompt after prediction failure: patient_id=%s, "
                    "base_date=%s, error=%s",
                    patient_id,
                    base_date,
                    prompt_exc,
                )
        return {
            "patient_id": patient_id,
            "base_date": base_date,
            "status": "failed",
            "validation_enabled": validation_enabled,
            "validation_mode": validation_mode,
            **build_prediction_failure_metadata(exc),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "prompt_path": str(prompt_path) if prompt_path is not None else None,
            "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        }

    return {
        "patient_id": patient_id,
        "base_date": base_date,
        **prediction_metadata_from_nested_result(prediction_result),
        **build_validation_success_metadata(),
        "status": validation_result["status"],
        "validation_enabled": validation_enabled,
        "validation_mode": validation_result["validation_mode"],
        "reason": validation_result.get("reason"),
        "predicted_game_ids": predicted_game_ids,
        "predicted_game_similar_user_counts": predicted_game_similar_user_counts,
        "actual_game_ids": actual_game_ids,
        "actual_game_similar_user_counts": actual_game_similar_user_counts,
        "similar_user_game_counts_task_count": similar_user_game_counts_task_count,
        "candidate_training_tasks_count": candidate_training_tasks_count,
        "coverage_diagnostics": coverage_diagnostics,
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
        "prompt_path": str(prompt_path) if prompt_path is not None else None,
        "prediction_started_at_seconds": round(started_at, 6),
        "prediction_finished_at_seconds": round(prediction_finished_at, 6),
        "validation_started_at_seconds": round(validation_started_at, 6),
        "validation_finished_at_seconds": round(validation_finished_at, 6),
        "prediction_elapsed_seconds": prediction_elapsed_seconds,
        "validation_elapsed_seconds": validation_elapsed_seconds,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
    }


def build_not_evaluable_detail(
    *,
    patient_id: str,
    base_date: str,
    elapsed_seconds: float,
    reason: str = "no_actual_tasks_on_base_date",
    error_message: str | None = None,
) -> dict[str, Any]:
    """Build detail for patients without actual tasks on base_date."""
    detail: dict[str, Any] = {
        "patient_id": patient_id,
        "base_date": base_date,
        "status": "success_not_evaluable",
        "predicted_game_ids": [],
        "actual_game_ids": [],
        "matched_game_ids": [],
        "task_hit": None,
        "precision": None,
        "recall": None,
        "f1": None,
        "predicted_task_count": 0,
        "actual_task_count": 0,
        "matched_task_count": 0,
        "reason": reason,
        "elapsed_seconds": elapsed_seconds,
    }
    if error_message is not None:
        detail["error_message"] = error_message
    detail.update(
        {
            "prediction_status": "not_run",
            "prediction_failure_stage": None,
            "prediction_failure_reason": None,
            "prediction_error_type": None,
            "prediction_error_message": None,
            "fallback_used": False,
            "fallback_reason": None,
            "validation_status": "not_run",
            "validation_failure_stage": None,
            "validation_failure_reason": None,
        }
    )
    return detail


def extract_predicted_game_ids(result: dict[str, Any]) -> list[str]:
    """Extract unique predicted game IDs from an end-to-end prediction result."""
    prediction_result = result.get("training_task_prediction")
    if isinstance(prediction_result, dict):
        result = prediction_result
    predictions = result.get("predicted_training_tasks")
    if not isinstance(predictions, list):
        return []

    game_ids: list[str] = []
    seen_game_ids: set[str] = set()
    for prediction in predictions:
        if not isinstance(prediction, dict):
            continue
        game_id = normalize_text(prediction.get("game_id"))
        if game_id is None or game_id in seen_game_ids:
            continue
        game_ids.append(game_id)
        seen_game_ids.add(game_id)
    return game_ids


def build_actual_game_similar_user_counts(
    actual_game_ids: list[str],
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Map actual same-day game IDs to prompt similar-user aggregate counts."""
    return build_game_similar_user_counts(actual_game_ids, result)


def count_similar_user_game_count_tasks(result: dict[str, Any]) -> int:
    """Return the number of task rows in prompt similar-user aggregate counts."""
    result = unwrap_training_task_prediction(result)
    raw_counts = result.get("similar_user_game_counts")
    if not isinstance(raw_counts, list):
        return 0
    return sum(
        1
        for raw_count in raw_counts
        if isinstance(raw_count, dict) and normalize_text(raw_count.get("game_id"))
    )


def count_candidate_training_tasks(result: dict[str, Any]) -> int:
    """Return the number of unique tasks in the prompt candidate pool."""
    result = unwrap_training_task_prediction(result)
    return len(extract_game_ids_from_rows(result.get("candidate_training_tasks"), "game_id"))


def build_game_similar_user_counts(
    game_ids: list[str],
    result: dict[str, Any],
) -> list[dict[str, Any]]:
    """Map game IDs to prompt similar-user aggregate counts."""
    result = unwrap_training_task_prediction(result)
    raw_counts = result.get("similar_user_game_counts")
    if not isinstance(raw_counts, list):
        raw_counts = []

    sorted_counts = sorted(
        raw_counts,
        key=lambda raw_count: (
            -int(raw_count.get("count") or 0) if isinstance(raw_count, dict) else 0,
            str(raw_count.get("game_id") or "") if isinstance(raw_count, dict) else "",
        ),
    )
    count_rank_by_game_id: dict[str, int] = {}
    counts_by_game_id: dict[str, dict[str, Any]] = {}
    for index, raw_count in enumerate(sorted_counts, start=1):
        if not isinstance(raw_count, dict):
            continue
        game_id = normalize_text(raw_count.get("game_id"))
        if game_id is None:
            continue
        count_rank_by_game_id[game_id] = index
        counts_by_game_id[game_id] = raw_count

    mappings: list[dict[str, Any]] = []
    for game_id in dedupe_texts(game_ids):
        raw_count = counts_by_game_id.get(game_id)
        mappings.append(
            {
                "game_id": game_id,
                "game_name": normalize_text(raw_count.get("game_name"))
                if raw_count is not None
                else None,
                "similar_user_count": int(raw_count.get("count") or 0)
                if raw_count is not None
                else 0,
                "similar_user_count_rank": count_rank_by_game_id.get(game_id),
                "appears_in_similar_user_game_counts": raw_count is not None,
            }
        )
    return mappings


def unwrap_training_task_prediction(result: dict[str, Any]) -> dict[str, Any]:
    """Return the nested training-task prediction payload when present."""
    prediction_result = result.get("training_task_prediction")
    return prediction_result if isinstance(prediction_result, dict) else result


def build_coverage_diagnostics(
    predicted_game_ids: list[str],
    actual_game_ids: list[str],
    result: dict[str, Any],
) -> dict[str, Any]:
    """Build per-patient coverage diagnostics for prompt evidence and candidates."""
    prediction_result = unwrap_training_task_prediction(result)
    raw_similar_user_game_ids = extract_game_ids_from_rows(
        prediction_result.get("raw_similar_user_game_counts"),
        "game_id",
    )
    similar_user_game_ids = extract_game_ids_from_rows(
        prediction_result.get("similar_user_game_counts"),
        "game_id",
    )
    overlap_similar_user_game_ids = raw_similar_user_game_ids or similar_user_game_ids
    candidate_training_task_ids = extract_game_ids_from_rows(
        prediction_result.get("candidate_training_tasks"),
        "game_id",
    )
    return {
        "similar_user_game_counts": build_missing_coverage_section(
            predicted_game_ids,
            actual_game_ids,
            similar_user_game_ids,
        ),
        "candidate_training_tasks": build_missing_coverage_section(
            predicted_game_ids,
            actual_game_ids,
            candidate_training_task_ids,
        ),
        "similar_user_candidate_task_overlap": build_task_pool_overlap_section(
            overlap_similar_user_game_ids,
            candidate_training_task_ids,
        ),
    }


def extract_game_ids_from_rows(raw_rows: object, field_name: str) -> set[str]:
    """Extract normalized game IDs from a list of dictionaries."""
    if not isinstance(raw_rows, list):
        return set()
    game_ids: set[str] = set()
    for raw_row in raw_rows:
        if not isinstance(raw_row, dict):
            continue
        game_id = normalize_text(raw_row.get(field_name))
        if game_id is not None:
            game_ids.add(game_id)
    return game_ids


def build_missing_coverage_section(
    predicted_game_ids: list[str],
    actual_game_ids: list[str],
    available_game_ids: set[str],
) -> dict[str, Any]:
    """Build missing counts/rates against one evidence or candidate game-id set."""
    predicted_ids = dedupe_texts(predicted_game_ids)
    actual_ids = dedupe_texts(actual_game_ids)
    predicted_missing_count = sum(
        1 for game_id in predicted_ids if game_id not in available_game_ids
    )
    actual_missing_count = sum(
        1 for game_id in actual_ids if game_id not in available_game_ids
    )
    return {
        "predicted_missing_count": predicted_missing_count,
        "predicted_total_count": len(predicted_ids),
        "predicted_missing_rate": round(
            safe_divide(predicted_missing_count, len(predicted_ids)),
            4,
        ),
        "actual_missing_count": actual_missing_count,
        "actual_total_count": len(actual_ids),
        "actual_missing_rate": round(
            safe_divide(actual_missing_count, len(actual_ids)),
            4,
        ),
    }


def build_task_pool_overlap_section(
    similar_user_task_ids: set[str],
    candidate_task_ids: set[str],
) -> dict[str, Any]:
    """Build overlap metrics between similar-user evidence tasks and candidates."""
    intersection_ids = similar_user_task_ids & candidate_task_ids
    return {
        "similar_user_task_count": len(similar_user_task_ids),
        "candidate_task_count": len(candidate_task_ids),
        "intersection_task_count": len(intersection_ids),
        "coverage": round(
            safe_divide(len(intersection_ids), len(similar_user_task_ids)),
            4,
        ),
        "candidate_supported_rate": round(
            safe_divide(len(intersection_ids), len(candidate_task_ids)),
            4,
        ),
    }


def get_actual_game_ids_on_base_date(
    user_service: UserService,
    patient_id: str,
    base_date: str,
) -> list[str]:
    """Return distinct exclusive-task game IDs trained by the patient on base_date."""
    parsed_base_date = parse_date_value(base_date, "base_date")
    end_date = parsed_base_date + timedelta(days=1)
    history_rows = user_service.get_patient_exclusive_training_task_history_by_date_window(
        patient_id,
        parsed_base_date.isoformat(),
        end_date.isoformat(),
    )
    game_ids: list[str] = []
    for game_count in build_game_counts_from_history(history_rows):
        game_id = normalize_text(game_count.get("game_id"))
        if game_id is not None:
            game_ids.append(game_id)
    return game_ids


def summarize_evaluation_details(details: list[dict[str, Any]]) -> dict[str, Any]:
    """Build aggregate metrics from per-patient evaluation details."""
    total_count = len(details)
    failed_details = [detail for detail in details if detail.get("status") == "failed"]
    evaluated_details = [
        detail for detail in details if detail.get("status") == "success_evaluated"
    ]
    not_evaluable_details = [
        detail
        for detail in details
        if detail.get("status") == "success_not_evaluable"
    ]
    not_validated_details = [
        detail
        for detail in details
        if detail.get("status") == "success_not_validated"
    ]
    success_count = (
        len(evaluated_details)
        + len(not_evaluable_details)
        + len(not_validated_details)
    )
    task_hit_count = sum(1 for detail in evaluated_details if detail.get("task_hit"))
    total_predicted_tasks = sum(
        int(detail.get("predicted_task_count") or 0) for detail in evaluated_details
    )
    total_actual_tasks = sum(
        int(detail.get("actual_task_count") or 0) for detail in evaluated_details
    )
    total_matched_tasks = sum(
        int(detail.get("matched_task_count") or 0) for detail in evaluated_details
    )
    micro_precision = safe_divide(total_matched_tasks, total_predicted_tasks)
    micro_recall = safe_divide(total_matched_tasks, total_actual_tasks)
    elapsed_seconds = [
        float(detail["elapsed_seconds"])
        for detail in details
        if isinstance(detail.get("elapsed_seconds"), int | float)
    ]
    prediction_elapsed_seconds = [
        float(detail["prediction_elapsed_seconds"])
        for detail in details
        if isinstance(detail.get("prediction_elapsed_seconds"), int | float)
    ]
    validation_elapsed_seconds = [
        float(detail["validation_elapsed_seconds"])
        for detail in details
        if isinstance(detail.get("validation_elapsed_seconds"), int | float)
    ]
    batch_prediction_elapsed_seconds = calculate_batch_phase_elapsed_seconds(
        details,
        start_field="prediction_started_at_seconds",
        end_field="prediction_finished_at_seconds",
    )
    batch_validation_elapsed_seconds = calculate_batch_phase_elapsed_seconds(
        details,
        start_field="validation_started_at_seconds",
        end_field="validation_finished_at_seconds",
    )
    similar_user_game_counts_task_counts = [
        int(detail["similar_user_game_counts_task_count"])
        for detail in evaluated_details
        if isinstance(detail.get("similar_user_game_counts_task_count"), int | float)
    ]
    candidate_training_tasks_counts = [
        int(detail["candidate_training_tasks_count"])
        for detail in evaluated_details
        if isinstance(detail.get("candidate_training_tasks_count"), int | float)
    ]
    coverage_diagnostics = aggregate_coverage_diagnostics(evaluated_details)
    task_pool_overlap = coverage_diagnostics["similar_user_candidate_task_overlap"]
    score_evaluated_details = [
        detail
        for detail in evaluated_details
        if detail.get("validation_mode") == "score"
        and isinstance(detail.get("score_delta"), int | float)
    ]

    prediction_visibility = summarize_prediction_visibility(details)

    return {
        "total_count": total_count,
        "success_count": success_count,
        "failed_count": len(failed_details),
        **prediction_visibility,
        "not_evaluable_count": len(not_evaluable_details),
        "validation_skipped_count": len(not_validated_details),
        "evaluated_count": len(evaluated_details),
        "coverage_rate": round(safe_divide(success_count, total_count), 4),
        "evaluable_rate": round(safe_divide(len(evaluated_details), total_count), 4),
        "task_hit_rate": round(
            safe_divide(task_hit_count, len(evaluated_details)),
            4,
        ),
        "micro_precision": round(micro_precision, 4),
        "micro_recall": round(micro_recall, 4),
        "micro_f1": round(calculate_f1(micro_precision, micro_recall), 4),
        "macro_precision": round(
            average_metric(evaluated_details, "precision"),
            4,
        ),
        "macro_recall": round(average_metric(evaluated_details, "recall"), 4),
        "macro_f1": round(average_metric(evaluated_details, "f1"), 4),
        "avg_predicted_task_count": round(
            average_count(evaluated_details, "predicted_task_count"),
            4,
        ),
        "avg_actual_task_count": round(
            average_count(evaluated_details, "actual_task_count"),
            4,
        ),
        "avg_similar_user_game_counts_task_count": round(
            average_numbers(
                [float(value) for value in similar_user_game_counts_task_counts]
            ),
            4,
        ),
        "min_similar_user_game_counts_task_count": min(
            similar_user_game_counts_task_counts,
            default=0,
        ),
        "max_similar_user_game_counts_task_count": max(
            similar_user_game_counts_task_counts,
            default=0,
        ),
        "avg_candidate_training_tasks_count": round(
            average_numbers([float(value) for value in candidate_training_tasks_counts]),
            4,
        ),
        "min_candidate_training_tasks_count": min(
            candidate_training_tasks_counts,
            default=0,
        ),
        "max_candidate_training_tasks_count": max(
            candidate_training_tasks_counts,
            default=0,
        ),
        "similar_user_game_counts_predicted_missing_rate": coverage_diagnostics[
            "similar_user_game_counts"
        ]["predicted_missing_rate"],
        "similar_user_game_counts_actual_missing_rate": coverage_diagnostics[
            "similar_user_game_counts"
        ]["actual_missing_rate"],
        "candidate_training_tasks_predicted_missing_rate": coverage_diagnostics[
            "candidate_training_tasks"
        ]["predicted_missing_rate"],
        "candidate_training_tasks_actual_missing_rate": coverage_diagnostics[
            "candidate_training_tasks"
        ]["actual_missing_rate"],
        "similar_user_candidate_task_coverage": task_pool_overlap["coverage"],
        "candidate_task_supported_rate": task_pool_overlap[
            "candidate_supported_rate"
        ],
        "avg_similar_user_candidate_task_intersection_count": task_pool_overlap[
            "avg_intersection_task_count"
        ],
        "score_evaluated_count": len(score_evaluated_details),
        "avg_kg_score": round(
            average_metric(score_evaluated_details, "kg_avg_score"),
            4,
        ),
        "avg_csv_score": round(
            average_metric(score_evaluated_details, "csv_avg_score"),
            4,
        ),
        "avg_score_delta": round(
            average_metric(score_evaluated_details, "score_delta"),
            4,
        ),
        "avg_elapsed_seconds": round(average_numbers(elapsed_seconds), 4),
        "p95_elapsed_seconds": round(percentile(elapsed_seconds, 0.95), 4),
        "avg_prediction_elapsed_seconds": round(
            average_numbers(prediction_elapsed_seconds),
            4,
        ),
        "batch_prediction_elapsed_seconds": round(
            batch_prediction_elapsed_seconds,
            4,
        ),
        "p95_prediction_elapsed_seconds": round(
            percentile(prediction_elapsed_seconds, 0.95),
            4,
        ),
        "avg_validation_elapsed_seconds": round(
            average_numbers(validation_elapsed_seconds),
            4,
        ),
        "batch_validation_elapsed_seconds": round(
            batch_validation_elapsed_seconds,
            4,
        ),
        "p95_validation_elapsed_seconds": round(
            percentile(validation_elapsed_seconds, 0.95),
            4,
        ),
    }


def analyze_evaluation_details(details: list[dict[str, Any]]) -> dict[str, Any]:
    """Analyze rank and task distributions from per-patient evaluation details."""
    evaluated_details = [
        detail for detail in details if detail.get("status") == "success_evaluated"
    ]
    predicted_ranks: list[int] = []
    actual_ranks: list[int] = []
    matched_actual_ranks: list[int] = []
    missed_actual_ranks: list[int] = []
    predicted_missing_count = 0
    actual_missing_count = 0
    predicted_games: Counter[tuple[str, str | None]] = Counter()
    actual_games: Counter[tuple[str, str | None]] = Counter()
    matched_games: Counter[tuple[str, str | None]] = Counter()
    missed_actual_games: Counter[tuple[str, str | None]] = Counter()
    per_patient: list[dict[str, Any]] = []

    for detail in evaluated_details:
        matched_game_ids = set(dedupe_texts(detail.get("matched_game_ids") or []))
        predicted_counts = _list_dicts(
            detail.get("predicted_game_similar_user_counts")
        )
        actual_counts = _list_dicts(detail.get("actual_game_similar_user_counts"))

        for item in predicted_counts:
            game_id = normalize_text(item.get("game_id"))
            if game_id is None:
                continue
            game_name = normalize_text(item.get("game_name"))
            predicted_games[(game_id, game_name)] += 1
            rank = _rank_value(item)
            if rank is None:
                predicted_missing_count += 1
            else:
                predicted_ranks.append(rank)

        for item in actual_counts:
            game_id = normalize_text(item.get("game_id"))
            if game_id is None:
                continue
            game_name = normalize_text(item.get("game_name"))
            actual_games[(game_id, game_name)] += 1
            rank = _rank_value(item)
            if rank is None:
                actual_missing_count += 1
            else:
                actual_ranks.append(rank)
            if game_id in matched_game_ids:
                matched_games[(game_id, game_name)] += 1
                if rank is not None:
                    matched_actual_ranks.append(rank)
            else:
                missed_actual_games[(game_id, game_name)] += 1
                if rank is not None:
                    missed_actual_ranks.append(rank)

        per_patient.append(
            {
                "patient_id": detail.get("patient_id"),
                "task_hit": detail.get("task_hit"),
                "matched_task_count": detail.get("matched_task_count", 0),
                "predicted_task_count": detail.get("predicted_task_count", 0),
                "actual_task_count": detail.get("actual_task_count", 0),
                "precision": detail.get("precision"),
                "recall": detail.get("recall"),
                "predicted_rank_min": _min_rank(predicted_counts),
                "predicted_rank_max": _max_rank(predicted_counts),
                "actual_rank_min": _min_rank(actual_counts),
                "actual_rank_max": _max_rank(actual_counts),
                "similar_user_game_counts_task_count": detail.get(
                    "similar_user_game_counts_task_count"
                ),
                "candidate_training_tasks_count": detail.get(
                    "candidate_training_tasks_count"
                ),
                "similar_user_candidate_task_coverage": (
                    (detail.get("coverage_diagnostics") or {})
                    .get("similar_user_candidate_task_overlap", {})
                    .get("coverage")
                ),
                "candidate_task_supported_rate": (
                    (detail.get("coverage_diagnostics") or {})
                    .get("similar_user_candidate_task_overlap", {})
                    .get("candidate_supported_rate")
                ),
                "elapsed_seconds": detail.get("elapsed_seconds"),
                "prediction_elapsed_seconds": detail.get(
                    "prediction_elapsed_seconds"
                ),
                "validation_elapsed_seconds": detail.get(
                    "validation_elapsed_seconds"
                ),
            }
        )

    similar_user_game_counts_task_counts = [
        int(detail["similar_user_game_counts_task_count"])
        for detail in evaluated_details
        if isinstance(detail.get("similar_user_game_counts_task_count"), int | float)
    ]
    candidate_training_tasks_counts = [
        int(detail["candidate_training_tasks_count"])
        for detail in evaluated_details
        if isinstance(detail.get("candidate_training_tasks_count"), int | float)
    ]
    coverage_diagnostics = aggregate_coverage_diagnostics(evaluated_details)
    task_pool_overlap = coverage_diagnostics["similar_user_candidate_task_overlap"]

    return {
        "evaluated_count": len(evaluated_details),
        "rank_stats": {
            "predicted": build_number_stats(predicted_ranks),
            "actual": build_number_stats(actual_ranks),
            "matched_actual": build_number_stats(matched_actual_ranks),
            "missed_actual": build_number_stats(missed_actual_ranks),
        },
        "rank_buckets": {
            "predicted": build_rank_buckets(predicted_ranks),
            "actual": build_rank_buckets(actual_ranks),
            "matched_actual": build_rank_buckets(matched_actual_ranks),
            "missed_actual": build_rank_buckets(missed_actual_ranks),
        },
        "missing_from_similar_user_game_counts": {
            "predicted_task_count": predicted_missing_count,
            "actual_task_count": actual_missing_count,
        },
        "coverage_diagnostics": coverage_diagnostics,
        "similar_user_game_counts_task_count_stats": build_number_stats(
            similar_user_game_counts_task_counts
        ),
        "candidate_training_tasks_count_stats": build_number_stats(
            candidate_training_tasks_counts
        ),
        "similar_user_candidate_task_overlap": task_pool_overlap,
        "top_predicted_games": _counter_to_game_rows(predicted_games),
        "top_actual_games": _counter_to_game_rows(actual_games),
        "top_matched_games": _counter_to_game_rows(matched_games),
        "top_missed_actual_games": _counter_to_game_rows(missed_actual_games),
        "per_patient": per_patient,
    }


def build_number_stats(values: list[int | float]) -> dict[str, Any]:
    """Build compact numeric distribution stats."""
    numeric_values = [float(value) for value in values]
    if not numeric_values:
        return {
            "count": 0,
            "min": None,
            "p25": None,
            "median": None,
            "mean": None,
            "p75": None,
            "max": None,
        }
    return {
        "count": len(numeric_values),
        "min": _clean_number(min(numeric_values)),
        "p25": _clean_number(percentile(numeric_values, 0.25)),
        "median": _clean_number(percentile(numeric_values, 0.5)),
        "mean": round(average_numbers(numeric_values), 4),
        "p75": _clean_number(percentile(numeric_values, 0.75)),
        "max": _clean_number(max(numeric_values)),
    }


def aggregate_coverage_diagnostics(
    evaluated_details: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate per-patient coverage diagnostics across evaluated details."""
    return {
        "similar_user_game_counts": aggregate_coverage_section(
            evaluated_details,
            "similar_user_game_counts",
        ),
        "candidate_training_tasks": aggregate_coverage_section(
            evaluated_details,
            "candidate_training_tasks",
        ),
        "similar_user_candidate_task_overlap": (
            aggregate_task_pool_overlap_section(evaluated_details)
        ),
    }


def aggregate_task_pool_overlap_section(
    evaluated_details: list[dict[str, Any]],
) -> dict[str, Any]:
    """Aggregate similar-user task pool vs candidate task pool overlap metrics."""
    sections: list[dict[str, Any]] = []
    for detail in evaluated_details:
        coverage_diagnostics = detail.get("coverage_diagnostics")
        if not isinstance(coverage_diagnostics, dict):
            continue
        section = coverage_diagnostics.get("similar_user_candidate_task_overlap")
        if isinstance(section, dict):
            sections.append(section)

    coverage_values = [
        float(section["coverage"])
        for section in sections
        if isinstance(section.get("coverage"), int | float)
    ]
    candidate_supported_rate_values = [
        float(section["candidate_supported_rate"])
        for section in sections
        if isinstance(section.get("candidate_supported_rate"), int | float)
    ]
    intersection_counts = [
        float(section["intersection_task_count"])
        for section in sections
        if isinstance(section.get("intersection_task_count"), int | float)
    ]
    similar_user_task_counts = [
        float(section["similar_user_task_count"])
        for section in sections
        if isinstance(section.get("similar_user_task_count"), int | float)
    ]
    candidate_task_counts = [
        float(section["candidate_task_count"])
        for section in sections
        if isinstance(section.get("candidate_task_count"), int | float)
    ]
    return {
        "count": len(sections),
        "coverage": round(average_numbers(coverage_values), 4),
        "candidate_supported_rate": round(
            average_numbers(candidate_supported_rate_values),
            4,
        ),
        "avg_intersection_task_count": round(
            average_numbers(intersection_counts),
            4,
        ),
        "avg_similar_user_task_count": round(
            average_numbers(similar_user_task_counts),
            4,
        ),
        "avg_candidate_task_count": round(
            average_numbers(candidate_task_counts),
            4,
        ),
    }


def aggregate_coverage_section(
    evaluated_details: list[dict[str, Any]],
    section_name: str,
) -> dict[str, Any]:
    """Aggregate one coverage section from details."""
    predicted_missing_count = 0
    predicted_total_count = 0
    actual_missing_count = 0
    actual_total_count = 0
    for detail in evaluated_details:
        coverage_diagnostics = detail.get("coverage_diagnostics")
        if not isinstance(coverage_diagnostics, dict):
            continue
        section = coverage_diagnostics.get(section_name)
        if not isinstance(section, dict):
            continue
        predicted_missing_count += int(section.get("predicted_missing_count") or 0)
        predicted_total_count += int(section.get("predicted_total_count") or 0)
        actual_missing_count += int(section.get("actual_missing_count") or 0)
        actual_total_count += int(section.get("actual_total_count") or 0)
    return {
        "predicted_missing_count": predicted_missing_count,
        "predicted_total_count": predicted_total_count,
        "predicted_missing_rate": round(
            safe_divide(predicted_missing_count, predicted_total_count),
            4,
        ),
        "actual_missing_count": actual_missing_count,
        "actual_total_count": actual_total_count,
        "actual_missing_rate": round(
            safe_divide(actual_missing_count, actual_total_count),
            4,
        ),
    }


def build_rank_buckets(ranks: list[int]) -> dict[str, int]:
    """Bucket similar-user count ranks for quick inspection."""
    buckets = {"1-7": 0, "8-10": 0, "11-20": 0, "21-50": 0, "51+": 0}
    for rank in ranks:
        if rank <= 7:
            buckets["1-7"] += 1
        elif rank <= 10:
            buckets["8-10"] += 1
        elif rank <= 20:
            buckets["11-20"] += 1
        elif rank <= 50:
            buckets["21-50"] += 1
        else:
            buckets["51+"] += 1
    return buckets


def _list_dicts(value: Any) -> list[dict[str, Any]]:
    """Return list items that are dictionaries."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _rank_value(item: dict[str, Any]) -> int | None:
    """Return a positive integer rank from a mapped game-count item."""
    rank = item.get("similar_user_count_rank")
    if isinstance(rank, int) and not isinstance(rank, bool) and rank > 0:
        return rank
    return None


def _min_rank(items: list[dict[str, Any]]) -> int | None:
    ranks = [_rank_value(item) for item in items]
    present_ranks = [rank for rank in ranks if rank is not None]
    return min(present_ranks, default=None)


def _max_rank(items: list[dict[str, Any]]) -> int | None:
    ranks = [_rank_value(item) for item in items]
    present_ranks = [rank for rank in ranks if rank is not None]
    return max(present_ranks, default=None)


def _counter_to_game_rows(
    counter: Counter[tuple[str, str | None]],
    *,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Convert game counters to JSON-friendly rows."""
    return [
        {
            "game_id": game_id,
            "game_name": game_name,
            "count": count,
        }
        for (game_id, game_name), count in counter.most_common(limit)
    ]


def _clean_number(value: float) -> int | float:
    """Return ints without a trailing decimal for JSON readability."""
    return int(value) if value.is_integer() else round(value, 4)


def write_outputs(
    details: list[dict[str, Any]],
    summary: dict[str, Any],
    *,
    output_dir: str | Path,
    summary_file: str,
    details_file: str,
) -> tuple[Path, Path]:
    """Write summary JSON and detail JSONL outputs."""
    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = resolved_output_dir / summary_file
    details_path = resolved_output_dir / details_file
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    details_path.write_text(
        "".join(
            json.dumps(detail, ensure_ascii=False, default=str) + "\n"
            for detail in details
        ),
        encoding="utf-8",
    )
    return summary_path, details_path


def write_score_curl_commands(
    details: list[dict[str, Any]],
    *,
    output_dir: str | Path,
    curl_file: str = DEFAULT_SCORE_CURL_FILE,
) -> Path | None:
    """Write score-service curl commands captured in per-patient details."""
    blocks: list[str] = []
    for detail in details:
        validation = detail.get("training_task_score_validation")
        if not isinstance(validation, dict):
            continue
        for label, exchange_name in (
            ("kg", "kg_score_exchange"),
            ("csv", "csv_score_exchange"),
        ):
            exchange = validation.get(exchange_name)
            if not isinstance(exchange, dict):
                continue
            curl_command = exchange.get("request_curl")
            if not isinstance(curl_command, str) or not curl_command.strip():
                continue
            blocks.append(
                "\n".join(
                    [
                        f"# patient_id={detail.get('patient_id')} base_date={detail.get('base_date')} source={label}",
                        curl_command.strip(),
                    ]
                )
            )
    if not blocks:
        return None

    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    curl_path = resolved_output_dir / curl_file
    curl_path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")
    return curl_path


def write_analysis_output(
    analysis: dict[str, Any],
    *,
    output_dir: str | Path,
    analysis_file: str,
) -> Path:
    """Write analysis JSON output."""
    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    analysis_path = resolved_output_dir / analysis_file
    analysis_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return analysis_path


def build_experiment_config(
    *,
    base_date: str,
    pattern: str,
    config_path: str | Path,
    skip_path_build: bool,
    skip_path_scoring: bool,
    query_family: str | None,
    task_top_k: int,
    use_llm: bool,
    workers: int,
) -> dict[str, Any]:
    """Build experiment metadata saved with evaluation outputs."""
    query_settings = load_query_settings(config_path)
    disease_course_window_days = (
        query_settings.candidate_ranking.disease_course_window_days
    )
    scored_path_top_k = query_settings.score_pattern_paths.top_k
    patient_path_window_days = query_settings.patient_path.window_days
    prompt_template_name = getattr(
        query_settings.training_task_prediction,
        "prompt_template_name",
        CURRENT_TASK_PREDICTION_PROMPT_TEMPLATE_NAME,
    )
    if not isinstance(prompt_template_name, str) or not prompt_template_name.strip():
        prompt_template_name = CURRENT_TASK_PREDICTION_PROMPT_TEMPLATE_NAME
    similar_user_game_counts_weighting_enabled = getattr(
        query_settings.training_task_prediction,
        "similar_user_game_counts_weighting_enabled",
        False,
    )
    if not isinstance(similar_user_game_counts_weighting_enabled, bool):
        similar_user_game_counts_weighting_enabled = False
    unlock_train_candidate_tasks_enabled = getattr(
        query_settings.training_task_prediction,
        "unlock_train_candidate_tasks_enabled",
        False,
    )
    if not isinstance(unlock_train_candidate_tasks_enabled, bool):
        unlock_train_candidate_tasks_enabled = False
    similar_user_game_counts_weighted_sort_enabled = getattr(
        query_settings.training_task_prediction,
        "similar_user_game_counts_weighted_sort_enabled",
        False,
    )
    if not isinstance(similar_user_game_counts_weighted_sort_enabled, bool):
        similar_user_game_counts_weighted_sort_enabled = False
    evaluation_settings = getattr(query_settings, "training_task_evaluation", None)
    validation_mode = getattr(evaluation_settings, "validation_mode", "set")
    score_validation_url = getattr(evaluation_settings, "score_validation_url", None)
    algorithm_request_results_csv = getattr(
        evaluation_settings,
        "algorithm_request_results_csv",
        None,
    )
    score_validation_timeout = getattr(
        evaluation_settings,
        "score_validation_timeout",
        None,
    )
    return {
        "base_date": base_date,
        "window_days": patient_path_window_days,
        "pattern": pattern,
        "config_path": str(config_path),
        "skip_path_build": skip_path_build,
        "skip_path_scoring": skip_path_scoring,
        "query_family": query_family,
        "task_top_k": task_top_k,
        "use_llm": use_llm,
        "workers": workers,
        "prompt_template": prompt_template_name,
        "unlock_train_candidate_tasks_enabled": unlock_train_candidate_tasks_enabled,
        "similar_user_game_counts_weighting_enabled": similar_user_game_counts_weighting_enabled,
        "similar_user_game_counts_weighted_sort_enabled": similar_user_game_counts_weighted_sort_enabled,
        "validation_mode": validation_mode,
        "score_validation_url": score_validation_url,
        "algorithm_request_results_csv": algorithm_request_results_csv,
        "score_validation_timeout": score_validation_timeout,
        "scored_path_top_k": scored_path_top_k,
        "disease_course_window_days": disease_course_window_days,
    }


def build_experiment_output_dir(
    output_dir: str | Path,
    experiment_config: dict[str, Any],
) -> Path:
    """Return a parameterized output directory to avoid overwriting experiments."""
    disease_course_window_days = experiment_config.get("disease_course_window_days")
    query_family = experiment_config.get("query_family") or "default"
    use_llm = "llm" if experiment_config.get("use_llm") else "dry_run"
    parts = [
        f"base_{_slug_part(experiment_config.get('base_date'))}",
        f"window_{_slug_part(experiment_config.get('window_days'))}",
        f"dcw_{_slug_part(disease_course_window_days)}",
        f"topk_{_slug_part(experiment_config.get('task_top_k'))}",
        f"qf_{_slug_part(query_family)}",
        use_llm,
    ]
    if "validation_mode" in experiment_config:
        parts.insert(-1, f"eval_{_slug_part(experiment_config.get('validation_mode'))}")
    return Path(output_dir) / "_".join(parts)


def _slug_part(value: Any) -> str:
    """Return a filesystem-friendly value for experiment directory names."""
    text = str(value if value is not None else "none").strip()
    return "".join(char if char.isalnum() else "-" for char in text) or "none"


def run_batch_evaluation(
    patient_ids: list[str] | None,
    *,
    base_date: str,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    skip_path_build: bool = False,
    skip_path_scoring: bool = False,
    query_family: str | None = None,
    task_top_k: int = DEFAULT_TASK_TOP_K,
    use_llm: bool = True,
    limit: int | None = None,
    workers: int | None = None,
) -> list[dict[str, Any]]:
    """Evaluate every patient and return per-patient details."""
    started_at = time.perf_counter()
    query_settings = load_query_settings(config_path)
    patient_path_window_days = query_settings.patient_path.window_days
    evaluation_settings = query_settings.training_task_evaluation
    validation_mode = evaluation_settings.validation_mode
    resolved_workers = evaluation_settings.workers if workers is None else workers
    if limit is not None and limit <= 0:
        raise ValueError(f"limit must be a positive integer, got {limit}.")
    if resolved_workers <= 0:
        raise ValueError(f"workers must be a positive integer, got {resolved_workers}.")
    if not patient_ids:
        raise ValueError("patient_ids must contain at least one patient ID.")
    details: list[dict[str, Any]] = []
    with Neo4jClient.from_config(config_path) as client:
        user_service = UserService(
            kg_repository=KgRepository(
                client=client,
                config_path=Path(config_path),
            )
        )
        resolved_patient_ids = patient_ids
        if limit is not None:
            resolved_patient_ids = resolved_patient_ids[:limit]
        LOGGER.info(
            "Starting prediction evaluation batch: patient_count=%s, base_date=%s, window_days=%s, query_family=%s, task_top_k=%s, use_llm=%s, validation_mode=%s, workers=%s",
            len(resolved_patient_ids),
            base_date,
            patient_path_window_days,
            query_family,
            task_top_k,
            use_llm,
            validation_mode,
            resolved_workers,
        )
        if resolved_workers == 1 or len(resolved_patient_ids) == 1:
            for index, patient_id in enumerate(resolved_patient_ids, start=1):
                detail = evaluate_patient(
                    patient_id,
                    base_date=base_date,
                    user_service=user_service,
                    pattern=pattern,
                    config_path=config_path,
                    skip_path_build=skip_path_build,
                    skip_path_scoring=skip_path_scoring,
                    query_family=query_family,
                    task_top_k=task_top_k,
                    use_llm=use_llm,
                )
                details.append(detail)
                LOGGER.info(
                    "Evaluated prediction: index=%s/%s, patient_id=%s, status=%s",
                    index,
                    len(resolved_patient_ids),
                    patient_id,
                    detail.get("status"),
                )
        else:
            max_workers = min(resolved_workers, len(resolved_patient_ids))
            details_by_index: dict[int, dict[str, Any]] = {}
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        evaluate_patient,
                        patient_id,
                        base_date=base_date,
                        user_service=user_service,
                        pattern=pattern,
                        config_path=config_path,
                        skip_path_build=skip_path_build,
                        skip_path_scoring=skip_path_scoring,
                        query_family=query_family,
                        task_top_k=task_top_k,
                        use_llm=use_llm,
                    ): (index, patient_id)
                    for index, patient_id in enumerate(resolved_patient_ids, start=1)
                }
                for future in as_completed(futures):
                    index, patient_id = futures[future]
                    detail = future.result()
                    details_by_index[index] = detail
                    LOGGER.info(
                        "Evaluated prediction: index=%s/%s, patient_id=%s, status=%s",
                        index,
                        len(resolved_patient_ids),
                        patient_id,
                        detail.get("status"),
                    )
            details = [
                details_by_index[index]
                for index in range(1, len(resolved_patient_ids) + 1)
            ]
    summary = summarize_evaluation_details(details)
    LOGGER.info(
        "Completed prediction evaluation batch: total_count=%s, evaluated_count=%s, not_evaluable_count=%s, failed_count=%s, task_hit_rate=%s, elapsed_seconds=%s",
        summary["total_count"],
        summary["evaluated_count"],
        summary["not_evaluable_count"],
        summary["failed_count"],
        summary["task_hit_rate"],
        round(time.perf_counter() - started_at, 3),
    )
    return details


def resolve_patient_ids_for_evaluation(
    user_service: UserService,
    *,
    patient_ids: list[str] | None,
    base_date: str,
) -> list[str]:
    """Resolve the patient ID list used by batch evaluation."""
    if patient_ids is not None:
        return patient_ids
    return user_service.get_patient_ids()


def dedupe_texts(values: list[str]) -> list[str]:
    """Normalize and dedupe text values while preserving order."""
    results: list[str] = []
    seen_values: set[str] = set()
    for value in values:
        normalized = normalize_text(value)
        if normalized is None or normalized in seen_values:
            continue
        results.append(normalized)
        seen_values.add(normalized)
    return results


def normalize_text(value: Any) -> str | None:
    """Return a stripped string or None for empty values."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def average_metric(details: list[dict[str, Any]], field_name: str) -> float:
    """Average a per-user metric across evaluated details."""
    values = [
        float(detail[field_name])
        for detail in details
        if isinstance(detail.get(field_name), int | float)
    ]
    return average_numbers(values)


def average_count(details: list[dict[str, Any]], field_name: str) -> float:
    """Average a per-user count across evaluated details."""
    values = [
        float(detail[field_name])
        for detail in details
        if isinstance(detail.get(field_name), int | float)
    ]
    return average_numbers(values)


def calculate_batch_phase_elapsed_seconds(
    details: list[dict[str, Any]],
    *,
    start_field: str,
    end_field: str,
) -> float:
    """Return the wall-clock span covered by a phase across the batch."""
    starts: list[float] = []
    ends: list[float] = []
    for detail in details:
        start = detail.get(start_field)
        end = detail.get(end_field)
        if isinstance(start, int | float) and isinstance(end, int | float):
            starts.append(float(start))
            ends.append(float(end))
    if not starts or not ends:
        return 0.0
    return max(ends) - min(starts)


def average_numbers(values: list[float]) -> float:
    """Return the arithmetic mean of a number list."""
    return sum(values) / len(values) if values else 0.0


def percentile(values: list[float], ratio: float) -> float:
    """Return nearest-rank percentile for a number list."""
    if not values:
        return 0.0
    sorted_values = sorted(values)
    index = max(0, math.ceil(len(sorted_values) * ratio) - 1)
    return sorted_values[index]


def main() -> int:
    """Run same-day prediction evaluation and write metrics outputs."""
    args = parse_args()
    query_settings = load_query_settings(args.config)
    patient_path_window_days = query_settings.patient_path.window_days
    patient_path_query_family = query_settings.patient_path.query_family
    task_top_k = query_settings.training_task_prediction.task_top_k
    evaluation_workers = query_settings.training_task_evaluation.workers
    started_at = time.perf_counter()
    LOGGER.info(
        "Starting prediction evaluation: patient_id=%s, base_date=%s, window_days=%s, query_family=%s, task_top_k=%s, use_llm=%s, workers=%s, output_dir=%s",
        args.patient_id,
        args.base_date,
        patient_path_window_days,
        patient_path_query_family,
        task_top_k,
        not args.dry_run,
        evaluation_workers,
        args.output_dir,
    )
    try:
        if args.patient_id is not None:
            patient_ids = [args.patient_id]
        else:
            patient_ids_file = build_patient_ids_file_from_base_date(
                base_date=args.base_date,
                patient_list_dir=args.patient_list_dir,
            )
            if not Path(patient_ids_file).exists():
                export_patient_ids_with_training_on_date(
                    base_date=args.base_date,
                    config_path=args.config,
                    output_dir=args.patient_list_dir,
                )
            patient_ids = read_patient_ids(patient_ids_file)
        if not patient_ids:
            raise ValueError(
                "No patient IDs were provided. Use --patient-id or ensure the "
                "base_date patient ID file can be generated."
            )
        batch_started_at = time.perf_counter()
        details = run_batch_evaluation(
            patient_ids,
            base_date=args.base_date,
            config_path=args.config,
            query_family=patient_path_query_family,
            task_top_k=task_top_k,
            use_llm=not args.dry_run,
            limit=args.limit,
            workers=evaluation_workers,
        )
        batch_elapsed_seconds = round(time.perf_counter() - batch_started_at, 3)
        summary = summarize_evaluation_details(details)
        summary["batch_elapsed_seconds"] = batch_elapsed_seconds
        summary["workers"] = evaluation_workers
        analysis = analyze_evaluation_details(details)
        experiment_config = build_experiment_config(
            base_date=args.base_date,
            config_path=args.config,
            query_family=patient_path_query_family,
            task_top_k=task_top_k,
            use_llm=not args.dry_run,
            workers=evaluation_workers,
        )
        summary["experiment_config"] = experiment_config
        resolved_output_dir = build_experiment_output_dir(
            args.output_dir,
            experiment_config,
        )
        summary_path, details_path = write_outputs(
            details,
            summary,
            output_dir=resolved_output_dir,
            summary_file=args.summary_file,
            details_file=args.details_file,
        )
        score_curl_path = write_score_curl_commands(
            details,
            output_dir=resolved_output_dir,
        )
        analysis_path = write_analysis_output(
            analysis,
            output_dir=resolved_output_dir,
            analysis_file=args.analysis_file,
        )
    except Exception as exc:
        LOGGER.exception("Training task prediction evaluation failed: %s", exc)
        return 1

    LOGGER.info(
        "Completed prediction evaluation: total_count=%s, evaluated_count=%s, not_evaluable_count=%s, failed_count=%s, task_hit_rate=%s, summary_path=%s, details_path=%s, analysis_path=%s, elapsed_seconds=%s",
        summary["total_count"],
        summary["evaluated_count"],
        summary["not_evaluable_count"],
        summary["failed_count"],
        summary["task_hit_rate"],
        summary_path,
        details_path,
        analysis_path,
        round(time.perf_counter() - started_at, 3),
    )
    if score_curl_path is not None:
        LOGGER.info("Wrote training-task score curl commands to %s", score_curl_path)
    LOGGER.info(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
