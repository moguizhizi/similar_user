"""Training-task prediction helpers driven by similar-user candidates."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from .llm_client import LlmClient
from .user_service import UserService
from ..utils.logger import get_logger


LOGGER = get_logger(__name__)
DEFAULT_TASK_TOP_K = 5

SYSTEM_PROMPT = """
你是训练任务预测助手。你只能基于输入中的目标用户历史、相似用户历史和候选训练任务进行预测。
不要做医学诊断，不要输出候选任务之外的任务。请返回合法 JSON。
""".strip()


@dataclass(frozen=True)
class SimilarUserCandidate:
    """Similar-user candidate parsed from run_similar_user_pipeline.py output."""

    patient_id: str
    candidate_score: float | None = None

    @property
    def weight(self) -> float:
        if self.candidate_score is None or self.candidate_score <= 0:
            return 1.0
        return self.candidate_score


@dataclass
class TrainingTaskPredictionService:
    """Build task-prediction context and optionally ask an LLM to rank tasks."""

    user_service: UserService
    llm_client: LlmClient | None = None

    def predict_from_pipeline_result(
        self,
        pipeline_result: dict[str, Any],
        *,
        base_date: str,
        window_days: int,
        task_top_k: int = DEFAULT_TASK_TOP_K,
        use_llm: bool = True,
        include_prompt: bool = False,
    ) -> dict[str, Any]:
        """Predict next training tasks from a similar-user pipeline result."""
        resolved_patient_id = self._resolve_patient_id(pipeline_result)
        target_task_window = build_target_task_window(base_date)
        candidate_task_window = build_candidate_task_window(base_date, window_days)
        candidates = extract_similar_user_candidates(pipeline_result)
        if not candidates:
            raise ValueError("similar user pipeline output does not contain candidates.")

        target_history = self.user_service.get_patient_training_task_history_by_date_window(
            resolved_patient_id,
            target_task_window["start_date"],
            target_task_window["end_date"],
        )
        similar_user_histories = {
            candidate.patient_id: self.user_service.get_patient_training_task_history_by_date_window(
                candidate.patient_id,
                candidate_task_window["start_date"],
                candidate_task_window["end_date"],
            )
            for candidate in candidates
        }

        target_summary = summarize_training_history(
            resolved_patient_id,
            target_history,
            task_window=target_task_window,
        )
        similar_summaries = [
            {
                **summarize_training_history(
                    candidate.patient_id,
                    similar_user_histories[candidate.patient_id],
                    task_window=candidate_task_window,
                ),
                "candidate_score": candidate.candidate_score,
            }
            for candidate in candidates
        ]
        candidate_tasks = build_candidate_training_tasks(
            candidates,
            similar_user_histories,
            top_k=max(task_top_k * 3, task_top_k),
        )
        rule_based_tasks = build_rule_based_predictions(
            candidate_tasks,
            top_k=task_top_k,
        )
        prompt = build_task_prediction_prompt(
            patient_id=resolved_patient_id,
            target_history_summary=target_summary,
            similar_user_summaries=similar_summaries,
            candidate_training_tasks=candidate_tasks,
            task_top_k=task_top_k,
        )

        llm_prediction: dict[str, Any] | None = None
        raw_llm_output: str | None = None
        if use_llm:
            if self.llm_client is None:
                raise ValueError("llm_client is required when use_llm is true.")
            raw_llm_output = self.llm_client.chat(
                prompt,
                system_prompt=SYSTEM_PROMPT,
                temperature=0.2,
            )
            llm_prediction = parse_json_object_from_text(raw_llm_output)

        result: dict[str, Any] = {
            "patient_id": resolved_patient_id,
            "candidate_source": {
                "source": "run_similar_user_pipeline.py",
                "candidate_count": len(candidates),
                "candidate_ids": [candidate.patient_id for candidate in candidates],
                "has_candidate_scores": any(
                    candidate.candidate_score is not None for candidate in candidates
                ),
                "candidate_task_window": candidate_task_window,
            },
            "target_history_summary": target_summary,
            "similar_user_summaries": similar_summaries,
            "candidate_training_tasks": candidate_tasks,
            "predicted_training_tasks": _resolve_predicted_tasks(
                llm_prediction,
                rule_based_tasks,
            ),
            "llm_prediction": llm_prediction,
        }
        if include_prompt:
            result["llm_prompt"] = prompt
        if raw_llm_output is not None:
            result["raw_llm_output"] = raw_llm_output

        LOGGER.info(
            "Built training-task prediction: patient_id=%s, candidate_count=%s, predicted_task_count=%s, used_llm=%s",
            resolved_patient_id,
            len(candidates),
            len(result["predicted_training_tasks"]),
            use_llm,
        )
        return result

    @staticmethod
    def _resolve_patient_id(pipeline_result: dict[str, Any]) -> str:
        raw_patient_id = pipeline_result.get("patient_id")
        if raw_patient_id is None:
            candidate_result = pipeline_result.get("candidate_result")
            if isinstance(candidate_result, dict):
                raw_patient_id = candidate_result.get("patient_id")
        if raw_patient_id is None:
            candidate_summary = pipeline_result.get("candidate_summary")
            if isinstance(candidate_summary, dict):
                raw_patient_id = candidate_summary.get("patient_id")

        resolved_patient_id = str(raw_patient_id or "").strip()
        if not resolved_patient_id:
            raise ValueError(
                "patient_id is required in run_similar_user_pipeline.py output."
            )
        return resolved_patient_id


def extract_similar_user_candidates(
    pipeline_result: dict[str, Any],
) -> list[SimilarUserCandidate]:
    """Extract candidate users from ids, scores, or full pipeline output."""
    raw_candidates = _find_raw_candidate_items(pipeline_result)
    candidates: list[SimilarUserCandidate] = []
    seen_patient_ids: set[str] = set()
    for raw_candidate in raw_candidates:
        candidate = _parse_candidate(raw_candidate)
        if candidate is None or candidate.patient_id in seen_patient_ids:
            continue
        candidates.append(candidate)
        seen_patient_ids.add(candidate.patient_id)
    return candidates


def parse_json_object_from_text(text: str) -> dict[str, Any]:
    """Parse a JSON object from plain JSON or logger-prefixed output."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string.")
    stripped = text.strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        value = _parse_first_valid_json_object(stripped)
    if not isinstance(value, dict):
        raise ValueError("JSON payload must be an object.")
    return value


def build_target_task_window(base_date: str) -> dict[str, Any]:
    """Build the target task window: [base_date - 2 days, base_date)."""
    parsed_base_date = parse_date_value(base_date, "base_date")
    start_date = parsed_base_date - timedelta(days=2)
    return {
        "base_date": parsed_base_date.isoformat(),
        "start_date": start_date.isoformat(),
        "end_date": parsed_base_date.isoformat(),
        "includes_base_date": False,
        "range_semantics": "[start_date, end_date)",
    }


def build_candidate_task_window(base_date: str, window_days: int) -> dict[str, Any]:
    """Build the candidate task window: [base_date - window_days, base_date)."""
    parsed_base_date = parse_date_value(base_date, "base_date")
    if (
        not isinstance(window_days, int)
        or isinstance(window_days, bool)
        or window_days <= 0
    ):
        raise ValueError(f"window_days must be a positive integer, got {window_days}.")
    start_date = parsed_base_date - timedelta(days=window_days)
    return {
        "base_date": parsed_base_date.isoformat(),
        "start_date": start_date.isoformat(),
        "end_date": parsed_base_date.isoformat(),
        "window_days": window_days,
        "includes_base_date": False,
        "range_semantics": "[start_date, end_date)",
    }


def parse_date_value(value: str, field_name: str) -> date:
    """Parse yyyy-mm-dd or yyyy-m-d style dates."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty date string.")
    parts = value.strip().split("-")
    if len(parts) != 3:
        raise ValueError(f"{field_name} must use yyyy-mm-dd format.")
    try:
        year, month, day = (int(part) for part in parts)
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid date.") from exc


def summarize_training_history(
    patient_id: str,
    history_rows: list[dict[str, Any]],
    *,
    top_k: int = 5,
    task_window: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact task-history summary suitable for prompt input."""
    normalized_patient_id = patient_id.strip()
    game_counts: dict[str, dict[str, Any]] = {}
    ordered_dates: list[str] = []
    recent_games: list[dict[str, Any]] = []

    for row in history_rows:
        training_date = _normalize_text(row.get("trainingDate"))
        if training_date is not None:
            ordered_dates.append(training_date)
        game = _normalize_node(row.get("g"))
        game_id = _normalize_text(game.get("id")) or _normalize_text(game.get("name"))
        if game_id is None:
            continue
        entry = game_counts.setdefault(
            game_id,
            {
                "game_id": game_id,
                "game_name": _normalize_text(game.get("name")),
                "task_type": _normalize_text(game.get("任务类型")),
                "count": 0,
            },
        )
        entry["count"] += 1
        recent_games.append(
            {
                "training_date": training_date,
                "game_id": game_id,
                "game_name": entry["game_name"],
                "task_type": entry["task_type"],
            }
        )

    frequent_games = sorted(
        game_counts.values(),
        key=lambda item: (-int(item["count"]), str(item["game_id"])),
    )[:top_k]

    summary = {
        "patient_id": normalized_patient_id,
        "row_count": len(history_rows),
        "training_date_count": len(set(ordered_dates)),
        "first_training_date": min(ordered_dates) if ordered_dates else None,
        "last_training_date": max(ordered_dates) if ordered_dates else None,
        "frequent_games": frequent_games,
        "recent_games": _dedupe_recent_games(recent_games, top_k=top_k),
    }
    if task_window is not None:
        summary["task_window"] = task_window
    return summary


def build_candidate_training_tasks(
    candidates: list[SimilarUserCandidate],
    similar_user_histories: dict[str, list[dict[str, Any]]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    """Aggregate weighted task candidates from similar-user histories."""
    task_index: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        rows = similar_user_histories.get(candidate.patient_id, [])
        for row in rows:
            game = _normalize_node(row.get("g"))
            game_id = _normalize_text(game.get("id")) or _normalize_text(
                game.get("name")
            )
            if game_id is None:
                continue
            item = task_index.setdefault(
                game_id,
                {
                    "game_id": game_id,
                    "game_name": _normalize_text(game.get("name")),
                    "task_type": _normalize_text(game.get("任务类型")),
                    "appearance_count": 0,
                    "weighted_score": 0.0,
                    "supporting_candidate_ids": [],
                },
            )
            item["appearance_count"] += 1
            item["weighted_score"] += candidate.weight
            if candidate.patient_id not in item["supporting_candidate_ids"]:
                item["supporting_candidate_ids"].append(candidate.patient_id)

    tasks = sorted(
        task_index.values(),
        key=lambda item: (
            -float(item["weighted_score"]),
            -int(item["appearance_count"]),
            str(item["game_id"]),
        ),
    )[:top_k]
    for task in tasks:
        task["weighted_score"] = round(float(task["weighted_score"]), 4)
    return tasks


def build_rule_based_predictions(
    candidate_training_tasks: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    """Build deterministic fallback predictions from candidate task scores."""
    if not candidate_training_tasks:
        return []
    max_score = max(float(task.get("weighted_score") or 0.0) for task in candidate_training_tasks)
    predictions: list[dict[str, Any]] = []
    for index, task in enumerate(candidate_training_tasks[:top_k], start=1):
        weighted_score = float(task.get("weighted_score") or 0.0)
        predictions.append(
            {
                "rank": index,
                "game_id": task.get("game_id"),
                "game_name": task.get("game_name"),
                "task_type": task.get("task_type"),
                "confidence": round(weighted_score / max_score, 4)
                if max_score > 0
                else 0.0,
                "reason": "相似用户历史中该训练任务的加权出现次数较高。",
                "supporting_candidate_ids": task.get("supporting_candidate_ids", []),
            }
        )
    return predictions


def build_task_prediction_prompt(
    *,
    patient_id: str,
    target_history_summary: dict[str, Any],
    similar_user_summaries: list[dict[str, Any]],
    candidate_training_tasks: list[dict[str, Any]],
    task_top_k: int,
) -> str:
    """Build the JSON-first prompt for LLM task prediction."""
    payload = {
        "patient_id": patient_id,
        "target_user_history": target_history_summary,
        "similar_users": similar_user_summaries,
        "candidate_training_tasks": candidate_training_tasks,
        "output_requirement": {
            "top_k": task_top_k,
            "format": {
                "patient_id": patient_id,
                "predicted_training_tasks": [
                    {
                        "rank": 1,
                        "game_id": "只能来自 candidate_training_tasks",
                        "game_name": "只能来自 candidate_training_tasks",
                        "confidence": 0.0,
                        "reason": "简短说明目标用户和相似用户证据",
                        "supporting_candidate_ids": ["候选用户id"],
                    }
                ],
            },
        },
    }
    return (
        "请根据以下 JSON 数据预测目标用户下一阶段更可能适合的训练任务。"
        "只允许从 candidate_training_tasks 中选择，返回 JSON 对象，不要添加 Markdown。\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}"
    )


def _resolve_predicted_tasks(
    llm_prediction: dict[str, Any] | None,
    rule_based_tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(llm_prediction, dict):
        predicted_tasks = llm_prediction.get("predicted_training_tasks")
        if isinstance(predicted_tasks, list):
            return predicted_tasks
        predicted_tasks = llm_prediction.get("predicted_tasks")
        if isinstance(predicted_tasks, list):
            return predicted_tasks
    return rule_based_tasks


def _find_raw_candidate_items(pipeline_result: dict[str, Any]) -> list[Any]:
    candidate_result = pipeline_result.get("candidate_result")
    if isinstance(candidate_result, dict):
        candidates = candidate_result.get("candidates")
        if isinstance(candidates, list):
            return candidates

    candidate_summary = pipeline_result.get("candidate_summary")
    if isinstance(candidate_summary, dict):
        candidates = candidate_summary.get("candidates")
        if isinstance(candidates, list):
            return candidates
        candidate_ids = candidate_summary.get("candidate_ids")
        if isinstance(candidate_ids, list):
            return candidate_ids

    candidates = pipeline_result.get("candidates")
    if isinstance(candidates, list):
        return candidates
    candidate_ids = pipeline_result.get("candidate_ids")
    if isinstance(candidate_ids, list):
        return candidate_ids
    return []


def _parse_candidate(raw_candidate: Any) -> SimilarUserCandidate | None:
    if isinstance(raw_candidate, str) or isinstance(raw_candidate, int):
        patient_id = str(raw_candidate).strip()
        return SimilarUserCandidate(patient_id) if patient_id else None
    if not isinstance(raw_candidate, dict):
        return None
    raw_patient_id = (
        raw_candidate.get("patient_id")
        or raw_candidate.get("candidate_patient_id")
        or raw_candidate.get("id")
    )
    patient_id = str(raw_patient_id or "").strip()
    if not patient_id:
        return None
    return SimilarUserCandidate(
        patient_id=patient_id,
        candidate_score=_normalize_float(raw_candidate.get("candidate_score")),
    )


def _parse_first_valid_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    while start >= 0:
        try:
            value = json.loads(_extract_json_object_from(text, start))
        except (json.JSONDecodeError, ValueError):
            start = text.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = text.find("{", start + 1)
    raise ValueError("text does not contain a valid JSON object.")


def _extract_json_object_from(text: str, start: int) -> str:
    depth = 0
    in_string = False
    escape_next = False
    for index in range(start, len(text)):
        char = text[index]
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError("text contains an incomplete JSON object.")


def _normalize_node(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        return dict(value)
    except (TypeError, ValueError):
        return {}


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _dedupe_recent_games(
    recent_games: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    seen_game_ids: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for game in reversed(recent_games):
        game_id = _normalize_text(game.get("game_id"))
        if game_id is None or game_id in seen_game_ids:
            continue
        deduped.append(game)
        seen_game_ids.add(game_id)
        if len(deduped) >= top_k:
            break
    return deduped
