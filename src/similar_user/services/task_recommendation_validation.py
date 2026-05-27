"""Validation helpers for training-task recommendations."""

from __future__ import annotations

from pathlib import Path
from statistics import mean
from typing import Any

from ..data_access.algorithm_request_results import (
    DEFAULT_ALGORITHM_REQUEST_RESULTS_PATH,
    load_algorithm_request_results,
)
from .training_task_score_client import (
    TrainingTaskScoreClient,
    TrainingTaskScoreError,
)


def evaluate_prediction_sets(
    predicted_game_ids: list[str],
    actual_game_ids: list[str],
) -> dict[str, Any]:
    """Calculate set-based task metrics for one patient."""
    predicted = normalize_task_ids(predicted_game_ids)
    actual = normalize_task_ids(actual_game_ids)
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


def build_training_task_score_validation(
    prediction_result: dict[str, Any],
    *,
    patient_id: str,
    score_url: str,
    csv_path: str | Path = DEFAULT_ALGORITHM_REQUEST_RESULTS_PATH,
    timeout_seconds: float = 10.0,
    client: TrainingTaskScoreClient | None = None,
) -> dict[str, Any]:
    """Score KG tasks and CSV snapshot tasks for the same patient profile."""
    normalized_patient_id = str(patient_id).strip()
    if not normalized_patient_id:
        raise ValueError("patient_id must be a non-empty string.")

    kg_task_ids = extract_predicted_task_ids(prediction_result)
    request_result = load_algorithm_request_results(csv_path).get_by_patient_id(
        normalized_patient_id
    )
    records = request_result.get("records")
    if not isinstance(records, list) or not records:
        return {
            "status": "skipped",
            "reason": "no_algorithm_request_result_record",
            "patient_id": normalized_patient_id,
            "matched_count": request_result.get("matched_count", 0),
            "kg_task_ids": kg_task_ids,
        }

    record = records[0]
    ai_params = record.get("ai_params")
    recommen_train = record.get("recommen_train")
    if not isinstance(ai_params, dict):
        return _skipped_payload(
            normalized_patient_id,
            kg_task_ids,
            record,
            reason="missing_ai_params",
        )
    if not isinstance(recommen_train, dict):
        return _skipped_payload(
            normalized_patient_id,
            kg_task_ids,
            record,
            reason="missing_recommen_train",
        )

    csv_task_ids = normalize_task_ids(recommen_train.get("id"))
    all_task_ids = normalize_task_ids([*kg_task_ids, *csv_task_ids])
    if not all_task_ids:
        return _skipped_payload(
            normalized_patient_id,
            kg_task_ids,
            record,
            reason="no_tasks_to_score",
            csv_task_ids=csv_task_ids,
        )

    resolved_client = client or TrainingTaskScoreClient(
        score_url,
        timeout_seconds=timeout_seconds,
    )
    try:
        scored_tasks = resolved_client.score_tasks(all_task_ids, ai_params=ai_params)
    except TrainingTaskScoreError as exc:
        return {
            "status": "failed",
            "reason": "score_service_error",
            "detail": str(exc),
            "patient_id": normalized_patient_id,
            "record_row_number": record.get("row_number"),
            "raw_user_id": record.get("raw_user_id"),
            "kg_task_ids": kg_task_ids,
            "csv_task_ids": csv_task_ids,
        }

    scores_by_task_id = {
        str(item["task_id"]): float(item["score"])
        for item in scored_tasks
        if isinstance(item, dict)
        and item.get("task_id") is not None
        and item.get("score") is not None
    }
    kg_scored_tasks = _select_scored_tasks(kg_task_ids, scores_by_task_id)
    csv_scored_tasks = _select_scored_tasks(csv_task_ids, scores_by_task_id)

    kg_avg_score = _average_score(kg_scored_tasks)
    csv_avg_score = _average_score(csv_scored_tasks)
    csv_task_id_set = set(csv_task_ids)
    return {
        "status": "ok",
        "patient_id": normalized_patient_id,
        "record_row_number": record.get("row_number"),
        "raw_user_id": record.get("raw_user_id"),
        "matched_count": request_result.get("matched_count", 0),
        "score_url": score_url,
        "kg_task_ids": kg_task_ids,
        "csv_task_ids": csv_task_ids,
        "overlap_task_ids": [
            task_id for task_id in kg_task_ids if task_id in csv_task_id_set
        ],
        "kg_avg_score": kg_avg_score,
        "csv_avg_score": csv_avg_score,
        "score_delta": _score_delta(kg_avg_score, csv_avg_score),
        "kg_top_score": _top_score(kg_scored_tasks),
        "csv_top_score": _top_score(csv_scored_tasks),
        "kg_better_than_csv_avg_count": _count_better_than_average(
            kg_scored_tasks,
            csv_avg_score,
        ),
        "kg_scored_tasks": kg_scored_tasks,
        "csv_scored_tasks": csv_scored_tasks,
    }


def extract_predicted_task_ids(result: dict[str, Any]) -> list[str]:
    """Extract unique KG predicted task IDs from either nested or plain output."""
    prediction_result = result.get("training_task_prediction")
    if isinstance(prediction_result, dict):
        result = prediction_result

    predictions = result.get("predicted_training_tasks")
    if not isinstance(predictions, list):
        return []
    return normalize_task_ids(
        [
            prediction.get("game_id")
            for prediction in predictions
            if isinstance(prediction, dict)
        ]
    )


def normalize_task_ids(raw_task_ids: object) -> list[str]:
    """Normalize task IDs while preserving first-seen order."""
    if raw_task_ids is None:
        return []
    values = raw_task_ids if isinstance(raw_task_ids, list) else [raw_task_ids]
    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value).strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)
    return normalized


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


def _skipped_payload(
    patient_id: str,
    kg_task_ids: list[str],
    record: dict[str, Any],
    *,
    reason: str,
    csv_task_ids: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "status": "skipped",
        "reason": reason,
        "patient_id": patient_id,
        "record_row_number": record.get("row_number"),
        "raw_user_id": record.get("raw_user_id"),
        "kg_task_ids": kg_task_ids,
    }
    if csv_task_ids is not None:
        payload["csv_task_ids"] = csv_task_ids
    return payload


def _select_scored_tasks(
    task_ids: list[str],
    scores_by_task_id: dict[str, float],
) -> list[dict[str, Any]]:
    return [
        {
            "task_id": task_id,
            "score": round(scores_by_task_id[task_id], 4),
        }
        for task_id in task_ids
        if task_id in scores_by_task_id
    ]


def _average_score(scored_tasks: list[dict[str, Any]]) -> float | None:
    if not scored_tasks:
        return None
    return round(mean(float(item["score"]) for item in scored_tasks), 4)


def _top_score(scored_tasks: list[dict[str, Any]]) -> float | None:
    if not scored_tasks:
        return None
    return max(float(item["score"]) for item in scored_tasks)


def _score_delta(
    kg_avg_score: float | None,
    csv_avg_score: float | None,
) -> float | None:
    if kg_avg_score is None or csv_avg_score is None:
        return None
    return round(kg_avg_score - csv_avg_score, 4)


def _count_better_than_average(
    scored_tasks: list[dict[str, Any]],
    average_score: float | None,
) -> int | None:
    if average_score is None:
        return None
    return sum(1 for item in scored_tasks if float(item["score"]) > average_score)
