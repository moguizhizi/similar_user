"""Adapters for external training-task prediction requests."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config.settings import DEFAULT_CONFIG_PATH
from ..services.task_prediction import DEFAULT_TASK_TOP_K


DEFAULT_OUTPUT_LEVEL = "scores"
DEFAULT_BASE_DATE = "2026-05-25"


@dataclass(frozen=True)
class UnifiedPredictionInput:
    """Normalized input passed from the HTTP API to unified prediction."""

    patient_id: str
    base_date: str
    config_path: str | Path = DEFAULT_CONFIG_PATH
    age: int | str | None = None
    education: str | None = None
    gender: str | None = None
    disease_ids: list[str] = field(default_factory=list)
    disease_names: list[str] = field(default_factory=list)
    symptom_ids: list[str] = field(default_factory=list)
    unknown_ids: list[str] = field(default_factory=list)
    query_family: str | None = None
    task_top_k: int = DEFAULT_TASK_TOP_K
    use_llm: bool = True
    include_prompt: bool = False
    output_level: str = DEFAULT_OUTPUT_LEVEL


def build_unified_prediction_input(
    payload: dict[str, Any],
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> UnifiedPredictionInput:
    """Normalize an external request body into unified prediction arguments."""
    if not isinstance(payload, dict):
        raise ValueError("Request payload must be a JSON object.")

    behavior_data = payload.get("behavior_data")
    behavior = behavior_data if isinstance(behavior_data, dict) else {}
    patient_id = normalize_user_id(
        payload.get("user_id", behavior.get("user_id")),
    )
    if not patient_id:
        raise ValueError("Field 'user_id' must be a non-empty value.")

    task_top_k = _normalize_positive_int(
        payload.get("task_top_k", DEFAULT_TASK_TOP_K),
        field_name="task_top_k",
    )
    output_level = _normalize_output_level(
        payload.get("output_level", DEFAULT_OUTPUT_LEVEL),
    )

    return UnifiedPredictionInput(
        patient_id=patient_id,
        base_date=DEFAULT_BASE_DATE,
        config_path=config_path,
        age=payload.get("age", behavior.get("age")),
        education=_resolve_education(payload, behavior),
        gender=_resolve_gender(payload, behavior),
        disease_ids=_normalize_text_list(payload.get("disease_ids")),
        disease_names=_resolve_disease_names(payload, behavior),
        symptom_ids=_normalize_text_list(payload.get("symptom_ids")),
        unknown_ids=_normalize_text_list(payload.get("unknown_ids")),
        query_family=_normalize_optional_text(payload.get("query_family")),
        task_top_k=task_top_k,
        use_llm=_normalize_bool(payload.get("use_llm", True), field_name="use_llm"),
        include_prompt=_normalize_bool(
            payload.get("include_prompt", False),
            field_name="include_prompt",
        ),
        output_level=output_level,
    )


def build_external_prediction_response(
    unified_result: dict[str, Any],
    *,
    source_payload: dict[str, Any],
) -> dict[str, Any]:
    """Build the response shape expected by the external module."""
    task_ids = extract_predicted_task_ids(unified_result)
    ba_dalt_length = _resolve_ba_dalt_length(source_payload)
    return {
        "id": [_normalize_response_task_id(task_id) for task_id in task_ids],
        "ba_dalt": [0] * ba_dalt_length,
        "ba_id_list": [0] * len(task_ids),
    }


def extract_predicted_task_ids(unified_result: dict[str, Any]) -> list[str]:
    """Extract predicted task IDs from raw unified prediction output."""
    inner = unified_result.get("result") if isinstance(unified_result, dict) else None
    if not isinstance(inner, dict):
        return []

    prediction = inner.get("training_task_prediction")
    if not isinstance(prediction, dict):
        return []

    tasks = prediction.get("predicted_training_tasks")
    if not isinstance(tasks, list):
        return []

    task_ids: list[str] = []
    seen: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            continue
        task_id = _normalize_optional_text(task.get("game_id"))
        if task_id is None or task_id in seen:
            continue
        task_ids.append(task_id)
        seen.add(task_id)
    return task_ids


def normalize_user_id(value: object) -> str:
    """Normalize external user IDs to KG patient IDs."""
    text = _normalize_optional_text(value)
    if text is None:
        return ""
    if text.endswith("_old"):
        return text[: -len("_old")]
    return text


def _resolve_gender(payload: dict[str, Any], behavior: dict[str, Any]) -> str | None:
    behavior_gender = _normalize_optional_text(behavior.get("gender"))
    if behavior_gender is not None:
        return behavior_gender

    sex = payload.get("sex")
    if sex in (1, "1", "男", "male", "Male", "M", "m"):
        return "男"
    if sex in (2, "2", "女", "female", "Female", "F", "f"):
        return "女"
    return _normalize_optional_text(payload.get("gender"))


def _resolve_education(
    payload: dict[str, Any],
    behavior: dict[str, Any],
) -> str | None:
    behavior_education = _normalize_optional_text(behavior.get("edu"))
    if behavior_education is not None:
        return behavior_education
    return _normalize_optional_text(payload.get("education"))


def _resolve_disease_names(
    payload: dict[str, Any],
    behavior: dict[str, Any],
) -> list[str]:
    names = _normalize_text_list(payload.get("sicksName"))
    if names:
        return names
    behavior_sicks = _normalize_optional_text(behavior.get("sicks"))
    return [behavior_sicks] if behavior_sicks is not None else []


def _normalize_text_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (str, int, float)):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        return []

    normalized: list[str] = []
    seen: set[str] = set()
    for item in values:
        text = _normalize_optional_text(item)
        if text is None or text in seen:
            continue
        normalized.append(text)
        seen.add(text)
    return normalized


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_positive_int(value: object, *, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"Field '{field_name}' must be a positive integer.")
    return value


def _normalize_bool(value: object, *, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"Field '{field_name}' must be a boolean.")
    return value


def _normalize_output_level(value: object) -> str:
    text = _normalize_optional_text(value) or DEFAULT_OUTPUT_LEVEL
    if text not in {"ids", "scores", "full"}:
        raise ValueError("Field 'output_level' must be one of: ids, scores, full.")
    return text


def _resolve_ba_dalt_length(payload: dict[str, Any]) -> int:
    pre_score_ba = payload.get("pre_score_ba")
    if isinstance(pre_score_ba, list):
        return len(pre_score_ba)
    ba = payload.get("ba")
    if isinstance(ba, list):
        return len(ba)
    return 0


def _normalize_response_task_id(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value
