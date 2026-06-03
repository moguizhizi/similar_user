"""Shared metadata for task prediction failures and fallback visibility."""

from __future__ import annotations

from collections import Counter
from typing import Any


PREDICTION_METADATA_FIELDS = (
    "prediction_status",
    "prediction_failure_stage",
    "prediction_failure_reason",
    "prediction_error_type",
    "prediction_error_message",
    "fallback_used",
    "fallback_reason",
    "fallback_source",
    "fallback_candidates_count",
)

VALIDATION_METADATA_FIELDS = (
    "validation_status",
    "validation_failure_stage",
    "validation_failure_reason",
)


def build_prediction_success_metadata(
    *,
    fallback_used: bool = False,
    fallback_reason: str | None = None,
    fallback_source: str | None = None,
    fallback_candidates_count: int | None = None,
    failure_stage: str | None = None,
    failure_reason: str | None = None,
    error_type: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Return standard metadata for a successful prediction."""
    return {
        "prediction_status": "success",
        "prediction_failure_stage": failure_stage,
        "prediction_failure_reason": failure_reason,
        "prediction_error_type": error_type,
        "prediction_error_message": error_message,
        "fallback_used": bool(fallback_used),
        "fallback_reason": fallback_reason,
        "fallback_source": fallback_source,
        "fallback_candidates_count": fallback_candidates_count,
    }


def build_prediction_failure_metadata(exc: Exception) -> dict[str, Any]:
    """Return standard metadata for a failed prediction exception."""
    failure_stage, failure_reason = classify_prediction_exception(exc)
    return {
        "prediction_status": "failed",
        "prediction_failure_stage": failure_stage,
        "prediction_failure_reason": failure_reason,
        "prediction_error_type": type(exc).__name__,
        "prediction_error_message": str(exc),
        "fallback_used": False,
        "fallback_reason": None,
        "fallback_source": None,
        "fallback_candidates_count": None,
    }


def build_validation_success_metadata() -> dict[str, Any]:
    """Return standard metadata for successful validation."""
    return {
        "validation_status": "success",
        "validation_failure_stage": None,
        "validation_failure_reason": None,
    }


def build_validation_failure_metadata(exc: Exception) -> dict[str, Any]:
    """Return standard metadata for failed validation."""
    message = str(exc).lower()
    reason = "validation_timeout" if "timeout" in message else "validation_error"
    return {
        "validation_status": "failed",
        "validation_failure_stage": "validation",
        "validation_failure_reason": reason,
    }


def classify_prediction_exception(exc: Exception) -> tuple[str, str]:
    """Classify a prediction exception into a coarse stage and reason."""
    message = str(exc).lower()
    if "education is required" in message or "requires: education" in message:
        return "input", "missing_education"
    if "gender is required" in message or "requires: gender" in message:
        return "input", "missing_gender"
    if "age is required" in message or "requires: age" in message:
        return "input", "missing_age"
    if "no_resolved_entity_names" in message:
        return "entity_resolution", "no_resolved_entity_names"
    if "missing_entity_input" in message or "requires at least one" in message:
        return "input", "missing_entity_input"
    if "does not contain candidates" in message or "candidate" in message:
        return "candidate", "empty_candidates"
    if "llm" in message or "prompt" in message:
        return "llm", "llm_error"
    if "timeout" in message:
        return "prediction", "prediction_timeout"
    return "prediction", "prediction_error"


def copy_prediction_metadata(source: dict[str, Any]) -> dict[str, Any]:
    """Copy standard prediction metadata from a prediction result."""
    return {
        field: source.get(field)
        for field in PREDICTION_METADATA_FIELDS
        if field in source
    }


def prediction_metadata_from_nested_result(result: dict[str, Any]) -> dict[str, Any]:
    """Return prediction metadata from either a direct or wrapped result."""
    prediction_result = result.get("training_task_prediction")
    if isinstance(prediction_result, dict):
        return copy_prediction_metadata(prediction_result)
    return copy_prediction_metadata(result)


def summarize_prediction_visibility(details: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate prediction/fallback metadata for evaluation summaries."""
    prediction_status_counts = Counter(
        str(detail.get("prediction_status"))
        for detail in details
        if detail.get("prediction_status") is not None
    )
    failure_stage_counts = Counter(
        str(detail.get("prediction_failure_stage"))
        for detail in details
        if detail.get("prediction_failure_stage")
    )
    failure_reason_counts = Counter(
        str(detail.get("prediction_failure_reason"))
        for detail in details
        if detail.get("prediction_failure_reason")
    )
    fallback_reason_counts = Counter(
        str(detail.get("fallback_reason"))
        for detail in details
        if detail.get("fallback_reason")
    )
    fallback_source_counts = Counter(
        str(detail.get("fallback_source"))
        for detail in details
        if detail.get("fallback_source")
    )
    fallback_used_count = sum(1 for detail in details if detail.get("fallback_used"))
    return {
        "prediction_status_counts": dict(sorted(prediction_status_counts.items())),
        "prediction_failure_stage_counts": dict(sorted(failure_stage_counts.items())),
        "prediction_failure_reason_counts": dict(sorted(failure_reason_counts.items())),
        "fallback_used_count": fallback_used_count,
        "fallback_reason_counts": dict(sorted(fallback_reason_counts.items())),
        "fallback_source_counts": dict(sorted(fallback_source_counts.items())),
    }
