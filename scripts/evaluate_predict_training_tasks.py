"""Evaluate same-day training-task predictions over a patient list.

这个脚本按历史回测口径评估 `predict_training_tasks`：

1. 只使用 `base_date` 之前的数据生成预测。
2. 查询目标用户在 `base_date` 当天的真实训练任务。
3. 不关心预测任务排序，只比较预测任务集合和真实任务集合是否相交。

常用执行方式：

    python scripts/evaluate_predict_training_tasks.py --base-date 2022-05-22 --window-days 14
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from datetime import timedelta
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from similar_user.data_access.kg_repository import KgRepository
from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.domain.graph_schema import (
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
)
from similar_user.services.task_prediction import (
    DEFAULT_TASK_TOP_K,
    build_game_counts_from_history,
    parse_date_value,
)
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger

from scripts.predict_training_tasks import run_end_to_end_training_task_prediction
from scripts.score_patient_pattern_paths import DEFAULT_CONFIG_PATH


LOGGER = get_logger(__name__)
DEFAULT_OUTPUT_DIR = Path("data/evaluation")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for same-day prediction evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate same-day training-task prediction metrics."
    )
    parser.add_argument(
        "patient_ids_file",
        nargs="?",
        help=(
            "Optional text file with one patient_id per line; blank lines and # comments "
            "are ignored. If omitted, all Patient IDs are read from Neo4j."
        ),
    )
    parser.add_argument(
        "--base-date",
        required=True,
        help="Prediction date; actual labels are tasks on this date.",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        required=True,
        help="Number of days before base_date used to query candidate-user tasks.",
    )
    parser.add_argument(
        "--pattern",
        default=PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        help="Pattern name used by predict_training_tasks.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--skip-path-build",
        action="store_true",
        help="Use existing saved paths and only run scoring plus candidate ranking.",
    )
    parser.add_argument(
        "--task-top-k",
        type=int,
        default=DEFAULT_TASK_TOP_K,
        help="Number of predicted training tasks to evaluate.",
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


def evaluate_patient(
    patient_id: str,
    *,
    base_date: str,
    window_days: int,
    user_service: UserService,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    skip_path_build: bool = False,
    task_top_k: int = DEFAULT_TASK_TOP_K,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Run prediction and compare it with the patient's same-day true tasks."""
    started_at = time.perf_counter()
    try:
        actual_game_ids = get_actual_game_ids_on_base_date(
            user_service,
            patient_id,
            base_date,
        )
        if not actual_game_ids:
            return build_not_evaluable_detail(
                patient_id=patient_id,
                base_date=base_date,
                elapsed_seconds=round(time.perf_counter() - started_at, 3),
            )

        prediction_result = run_end_to_end_training_task_prediction(
            patient_id,
            base_date=base_date,
            window_days=window_days,
            pattern=pattern,
            config_path=config_path,
            skip_path_build=skip_path_build,
            task_top_k=task_top_k,
            use_llm=use_llm,
        )
        predicted_game_ids = extract_predicted_game_ids(prediction_result)
    except Exception as exc:
        return {
            "patient_id": patient_id,
            "base_date": base_date,
            "status": "failed",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        }

    metrics = evaluate_prediction_sets(predicted_game_ids, actual_game_ids)
    return {
        "patient_id": patient_id,
        "base_date": base_date,
        "status": "success_evaluated",
        "predicted_game_ids": predicted_game_ids,
        "actual_game_ids": actual_game_ids,
        "matched_game_ids": metrics["matched_game_ids"],
        "task_hit": metrics["task_hit"],
        "precision": metrics["precision"],
        "recall": metrics["recall"],
        "f1": metrics["f1"],
        "predicted_task_count": len(predicted_game_ids),
        "actual_task_count": len(actual_game_ids),
        "matched_task_count": len(metrics["matched_game_ids"]),
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
    }


def build_not_evaluable_detail(
    *,
    patient_id: str,
    base_date: str,
    elapsed_seconds: float,
) -> dict[str, Any]:
    """Build detail for patients without actual tasks on base_date."""
    return {
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
        "reason": "no_actual_tasks_on_base_date",
        "elapsed_seconds": elapsed_seconds,
    }


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


def get_actual_game_ids_on_base_date(
    user_service: UserService,
    patient_id: str,
    base_date: str,
) -> list[str]:
    """Return distinct game IDs trained by the patient on base_date."""
    parsed_base_date = parse_date_value(base_date, "base_date")
    end_date = parsed_base_date + timedelta(days=1)
    history_rows = user_service.get_patient_training_task_history_by_date_window(
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


def evaluate_prediction_sets(
    predicted_game_ids: list[str],
    actual_game_ids: list[str],
) -> dict[str, Any]:
    """Calculate set-based task metrics for one patient."""
    predicted = dedupe_texts(predicted_game_ids)
    actual = dedupe_texts(actual_game_ids)
    actual_set = set(actual)
    matched = [game_id for game_id in predicted if game_id in actual_set]
    precision = safe_divide(len(matched), len(predicted))
    recall = safe_divide(len(matched), len(actual))
    return {
        "matched_game_ids": matched,
        "task_hit": bool(matched),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(calculate_f1(precision, recall), 4),
    }


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
    success_count = len(evaluated_details) + len(not_evaluable_details)
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

    return {
        "total_count": total_count,
        "success_count": success_count,
        "failed_count": len(failed_details),
        "not_evaluable_count": len(not_evaluable_details),
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
        "avg_elapsed_seconds": round(average_numbers(elapsed_seconds), 4),
        "p95_elapsed_seconds": round(percentile(elapsed_seconds, 0.95), 4),
    }


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


def run_batch_evaluation(
    patient_ids: list[str] | None,
    *,
    base_date: str,
    window_days: int,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    skip_path_build: bool = False,
    task_top_k: int = DEFAULT_TASK_TOP_K,
    use_llm: bool = True,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Evaluate every patient and return per-patient details."""
    if limit is not None and limit <= 0:
        raise ValueError(f"limit must be a positive integer, got {limit}.")
    details: list[dict[str, Any]] = []
    with Neo4jClient.from_config(config_path) as client:
        user_service = UserService(
            kg_repository=KgRepository(
                client=client,
                config_path=Path(config_path),
            )
        )
        resolved_patient_ids = (
            user_service.get_patient_ids() if patient_ids is None else patient_ids
        )
        if limit is not None:
            resolved_patient_ids = resolved_patient_ids[:limit]
        for index, patient_id in enumerate(resolved_patient_ids, start=1):
            detail = evaluate_patient(
                patient_id,
                base_date=base_date,
                window_days=window_days,
                user_service=user_service,
                pattern=pattern,
                config_path=config_path,
                skip_path_build=skip_path_build,
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
    return details


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


def safe_divide(numerator: int | float, denominator: int | float) -> float:
    """Divide with a zero fallback."""
    return float(numerator) / float(denominator) if denominator else 0.0


def calculate_f1(precision: float, recall: float) -> float:
    """Calculate F1 from precision and recall."""
    return (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )


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
    try:
        patient_ids = (
            read_patient_ids(args.patient_ids_file)
            if args.patient_ids_file is not None
            else None
        )
        details = run_batch_evaluation(
            patient_ids,
            base_date=args.base_date,
            window_days=args.window_days,
            pattern=args.pattern,
            config_path=args.config,
            skip_path_build=args.skip_path_build,
            task_top_k=args.task_top_k,
            use_llm=not args.dry_run,
            limit=args.limit,
        )
        summary = summarize_evaluation_details(details)
        summary_path, details_path = write_outputs(
            details,
            summary,
            output_dir=args.output_dir,
            summary_file=args.summary_file,
            details_file=args.details_file,
        )
    except Exception as exc:
        LOGGER.exception("Training task prediction evaluation failed: %s", exc)
        return 1

    LOGGER.info(
        "Wrote prediction evaluation outputs: summary=%s, details=%s",
        summary_path,
        details_path,
    )
    LOGGER.info(json.dumps(summary, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
