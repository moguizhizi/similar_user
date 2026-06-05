"""Fallback task prediction strategies for recommendation failures."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from .task_prediction_failure import build_prediction_success_metadata
from .user_service import UserService


DEFAULT_FALLBACK_TASK_TOP_K = 7


def build_candidate_task_fallback_prediction(
    *,
    patient_id: str,
    candidate_training_tasks: list[dict[str, Any]],
    unlock_train_candidate_tasks: list[dict[str, Any]] | None = None,
    task_top_k: int = DEFAULT_FALLBACK_TASK_TOP_K,
    reason: str,
    failure_stage: str,
    error: Exception | None = None,
    llm_prompt: str | None = None,
    raw_llm_output: str | None = None,
) -> dict[str, Any]:
    """Return deterministic predictions from already-built candidate tasks."""
    resolved_patient_id = _normalize_required_text(patient_id, "patient_id")
    resolved_top_k = _normalize_positive_int(task_top_k, "task_top_k")
    candidates = _dedupe_candidate_tasks(
        [
            dict(task)
            for task in candidate_training_tasks
            if isinstance(task, dict)
            and (_normalize_optional_text(task.get("game_id")) is not None)
        ]
    )
    unlock_train_game_ids = _ordered_game_ids(unlock_train_candidate_tasks or [])
    if unlock_train_game_ids:
        allowed_game_ids = set(unlock_train_game_ids)
        candidates = _dedupe_candidate_tasks(
            [
                task
                for task in candidates
                if _normalize_optional_text(task.get("game_id")) in allowed_game_ids
            ]
        )
        _append_unlock_train_remaining_tasks(
            candidates,
            unlock_train_candidate_tasks or [],
            _candidate_game_id_set(candidates),
            top_k=resolved_top_k,
            fallback_level="unlock_train_remaining_tasks",
            reason="候选任务兜底结果不足，按 unlock_train 白名单顺序补齐。",
        )
    predictions = _rank_candidate_tasks(candidates[:resolved_top_k])
    result: dict[str, Any] = {
        "patient_id": resolved_patient_id,
        **build_prediction_success_metadata(
            fallback_used=True,
            fallback_reason=reason,
            fallback_source="candidate_training_tasks",
            fallback_candidates_count=len(candidates),
            failure_stage=failure_stage,
            failure_reason=reason,
            error_type=type(error).__name__ if error is not None else None,
            error_message=str(error) if error is not None else None,
        ),
        "candidate_source": {
            "source": "candidate_training_tasks_fallback",
            "fallback_source": "candidate_training_tasks",
            "fallback_candidates_count": len(candidates),
            "reason": reason,
            "unlock_train_limited": bool(unlock_train_game_ids),
        },
        "candidate_training_tasks": candidates,
        "predicted_training_tasks": predictions,
        "llm_prediction": None,
    }
    if llm_prompt is not None:
        result["llm_prompt"] = llm_prompt
    if raw_llm_output is not None:
        result["raw_llm_output"] = raw_llm_output
    return result


@dataclass
class TaskPredictionFallbackService:
    """Build task recommendations when path or LLM evidence is unavailable."""

    user_service: UserService
    age_window: int = 5
    relaxed_age_window: int = 10
    broad_age_window: int = 15

    def predict_from_profile(
        self,
        *,
        patient_id: str,
        base_date: str,
        age: int | str | None,
        education: str | None,
        gender: str | None,
        unlock_train_candidate_tasks: list[dict[str, Any]] | None = None,
        task_top_k: int = DEFAULT_FALLBACK_TASK_TOP_K,
        reason: str = "direct_entity_unavailable",
    ) -> dict[str, Any]:
        """Return task predictions from profile, popular, then deterministic random."""
        resolved_patient_id = _normalize_required_text(patient_id, "patient_id")
        resolved_base_date = _normalize_required_text(base_date, "base_date")
        resolved_top_k = _normalize_positive_int(task_top_k, "task_top_k")
        resolved_age = _parse_optional_int(age, "age")
        resolved_education = _normalize_optional_text(education)
        resolved_gender = _normalize_optional_text(gender)
        unlock_train_game_ids = _ordered_game_ids(unlock_train_candidate_tasks or [])
        allowed_game_ids = set(unlock_train_game_ids) if unlock_train_game_ids else None

        selected: list[dict[str, Any]] = []
        seen_game_ids: set[str] = set()
        levels_used: list[str] = []

        for attempt in self._profile_attempts(
            age=resolved_age,
            education=resolved_education,
            gender=resolved_gender,
        ):
            rows = self.user_service.get_profile_matched_exclusive_tasks(
                base_date=resolved_base_date,
                age=attempt["age"],
                min_age=attempt["min_age"],
                max_age=attempt["max_age"],
                gender=attempt["gender"],
                education=attempt["education"],
                limit=resolved_top_k,
            )
            if _append_prediction_rows(
                selected,
                rows,
                seen_game_ids,
                top_k=resolved_top_k,
                fallback_level=attempt["level"],
                reason="画像相近用户历史中该训练任务出现次数较高。",
                allowed_game_ids=allowed_game_ids,
            ):
                levels_used.append(attempt["level"])
            if len(selected) >= resolved_top_k:
                break

        if len(selected) < resolved_top_k:
            rows = self.user_service.get_global_popular_exclusive_tasks(
                base_date=resolved_base_date,
                limit=resolved_top_k,
            )
            if _append_prediction_rows(
                selected,
                rows,
                seen_game_ids,
                top_k=resolved_top_k,
                fallback_level="global_popular_tasks",
                reason="全局历史中该训练任务出现次数较高。",
                allowed_game_ids=allowed_game_ids,
            ):
                levels_used.append("global_popular_tasks")

        if unlock_train_game_ids and len(selected) < resolved_top_k:
            if _append_unlock_train_remaining_tasks(
                selected,
                unlock_train_candidate_tasks or [],
                seen_game_ids,
                top_k=resolved_top_k,
                fallback_level="unlock_train_remaining_tasks",
                reason="高频兜底结果不足，按 unlock_train 白名单顺序补齐。",
            ):
                levels_used.append("unlock_train_remaining_tasks")

        if not unlock_train_game_ids and len(selected) < resolved_top_k:
            rows = self._deterministic_random_rows(
                patient_id=resolved_patient_id,
                base_date=resolved_base_date,
            )
            if _append_prediction_rows(
                selected,
                rows,
                seen_game_ids,
                top_k=resolved_top_k,
                fallback_level="deterministic_random_tasks",
                reason="缺少更强匹配证据，使用稳定随机兜底任务。",
                allowed_game_ids=allowed_game_ids,
            ):
                levels_used.append("deterministic_random_tasks")

        predictions = _rank_profile_predictions(selected)
        fallback_source = levels_used[0] if levels_used else "none"
        return {
            "patient_id": resolved_patient_id,
            **build_prediction_success_metadata(
                fallback_used=True,
                fallback_reason=reason,
                fallback_source=fallback_source,
                fallback_candidates_count=len(selected),
                failure_stage=_fallback_failure_stage(reason),
                failure_reason=reason,
            ),
            "candidate_source": {
                "source": "task_prediction_fallback",
                "fallback_source": fallback_source,
                "fallback_level": fallback_source,
                "levels_used": levels_used,
                "fallback_candidates_count": len(selected),
                "reason": reason,
                "unlock_train_limited": bool(unlock_train_game_ids),
            },
            "target_profile": {
                "age": resolved_age,
                "education": resolved_education,
                "gender": resolved_gender,
            },
            "candidate_training_tasks": selected,
            "predicted_training_tasks": predictions,
            "llm_prediction": None,
        }

    def _profile_attempts(
        self,
        *,
        age: int | None,
        education: str | None,
        gender: str | None,
    ) -> list[dict[str, Any]]:
        attempts: list[dict[str, Any]] = []
        attempts.append(
            self._attempt(
                "profile_matched_tasks",
                age=age,
                age_window=self.age_window,
                education=education,
                gender=gender,
            )
        )
        if education is not None:
            attempts.append(
                self._attempt(
                    "relaxed_age_gender_tasks",
                    age=age,
                    age_window=self.relaxed_age_window,
                    education=None,
                    gender=gender,
                )
            )
        if gender is not None:
            attempts.append(
                self._attempt(
                    "relaxed_age_education_tasks",
                    age=age,
                    age_window=self.relaxed_age_window,
                    education=education,
                    gender=None,
                )
            )
        if age is not None:
            attempts.append(
                self._attempt(
                    "relaxed_age_tasks",
                    age=age,
                    age_window=self.broad_age_window,
                    education=None,
                    gender=None,
                )
            )
        return _dedupe_attempts(attempts)

    @staticmethod
    def _attempt(
        level: str,
        *,
        age: int | None,
        age_window: int,
        education: str | None,
        gender: str | None,
    ) -> dict[str, Any]:
        return {
            "level": level,
            "age": age,
            "min_age": max(age - age_window, 0) if age is not None else None,
            "max_age": age + age_window if age is not None else None,
            "education": education,
            "gender": gender,
        }

    def _deterministic_random_rows(
        self,
        *,
        patient_id: str,
        base_date: str,
    ) -> list[dict[str, Any]]:
        rows = self.user_service.get_distinct_training_games()
        return sorted(
            rows,
            key=lambda row: _stable_sort_key(patient_id, base_date, _extract_game(row)),
        )


class DirectEntityFallbackPredictionService(TaskPredictionFallbackService):
    """Backward-compatible direct-entity fallback facade."""

    def predict(
        self,
        *,
        patient_id: str,
        base_date: str,
        age: int | str | None,
        education: str | None,
        gender: str | None,
        unlock_train_candidate_tasks: list[dict[str, Any]] | None = None,
        task_top_k: int = DEFAULT_FALLBACK_TASK_TOP_K,
        reason: str = "direct_entity_unavailable",
    ) -> dict[str, Any]:
        """Return direct-entity fallback predictions."""
        return self.predict_from_profile(
            patient_id=patient_id,
            base_date=base_date,
            age=age,
            education=education,
            gender=gender,
            unlock_train_candidate_tasks=unlock_train_candidate_tasks,
            task_top_k=task_top_k,
            reason=reason,
        )


def _rank_candidate_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    max_score = max((float(task.get("weighted_score") or 0.0) for task in tasks), default=0.0)
    predictions: list[dict[str, Any]] = []
    for index, task in enumerate(tasks, start=1):
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
                "reason": "候选任务已生成，因推荐排序失败改用候选任务确定性排序。",
                "supporting_candidate_ids": task.get("supporting_candidate_ids", []),
                "fallback_level": "candidate_training_tasks",
            }
        )
    return predictions


def _append_prediction_rows(
    selected: list[dict[str, Any]],
    rows: list[dict[str, Any]],
    seen_game_ids: set[str],
    *,
    top_k: int,
    fallback_level: str,
    reason: str,
    allowed_game_ids: set[str] | None = None,
) -> bool:
    added = False
    max_support = max(
        (int(row.get("support_count") or 0) for row in rows if isinstance(row, dict)),
        default=0,
    )
    for row in rows:
        if len(selected) >= top_k:
            break
        game = _extract_game(row)
        game_id = _normalize_optional_text(game.get("id")) or _normalize_optional_text(
            game.get("name")
        )
        if game_id is None or game_id in seen_game_ids:
            continue
        if allowed_game_ids is not None and game_id not in allowed_game_ids:
            continue
        support_count = _parse_optional_int(row.get("support_count"), "support_count")
        confidence = (
            round(float(support_count) / max_support, 4)
            if support_count is not None and max_support > 0
            else 0.1
        )
        selected.append(
            {
                "game_id": game_id,
                "game_name": _normalize_optional_text(game.get("name")),
                "task_type": _normalize_optional_text(game.get("任务类型")),
                "weighted_score": float(support_count or 0),
                "support_count": support_count,
                "patient_count": _parse_optional_int(
                    row.get("patient_count"),
                    "patient_count",
                ),
                "latest_training_date": _normalize_optional_text(
                    row.get("latest_training_date")
                ),
                "fallback_level": fallback_level,
                "confidence": confidence,
                "reason": reason,
                "supporting_candidate_ids": [],
            }
        )
        seen_game_ids.add(game_id)
        added = True
    return added


def _append_unlock_train_remaining_tasks(
    selected: list[dict[str, Any]],
    unlock_train_candidate_tasks: list[dict[str, Any]],
    seen_game_ids: set[str],
    *,
    top_k: int,
    fallback_level: str,
    reason: str,
) -> bool:
    added = False
    for task in unlock_train_candidate_tasks:
        if len(selected) >= top_k:
            break
        if not isinstance(task, dict):
            continue
        game_id = _normalize_optional_text(task.get("game_id"))
        if game_id is None or game_id in seen_game_ids:
            continue
        selected.append(
            {
                "game_id": game_id,
                "game_name": _normalize_optional_text(task.get("game_name")),
                "task_type": _normalize_optional_text(task.get("task_type")),
                "weighted_score": float(task.get("weighted_score") or 0.0),
                "support_count": _parse_optional_int(
                    task.get("support_count"),
                    "support_count",
                ),
                "patient_count": _parse_optional_int(
                    task.get("patient_count"),
                    "patient_count",
                ),
                "latest_training_date": _normalize_optional_text(
                    task.get("latest_training_date")
                ),
                "fallback_level": fallback_level,
                "confidence": 0.1,
                "reason": reason,
                "supporting_candidate_ids": [],
            }
        )
        seen_game_ids.add(game_id)
        added = True
    return added


def _rank_profile_predictions(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    predictions = []
    for index, task in enumerate(tasks, start=1):
        predictions.append(
            {
                "rank": index,
                "game_id": task.get("game_id"),
                "game_name": task.get("game_name"),
                "task_type": task.get("task_type"),
                "confidence": task.get("confidence"),
                "reason": task.get("reason"),
                "fallback_level": task.get("fallback_level"),
                "supporting_candidate_ids": task.get("supporting_candidate_ids", []),
            }
        )
    return predictions


def _ordered_game_ids(tasks: list[dict[str, Any]]) -> list[str]:
    game_ids: list[str] = []
    seen: set[str] = set()
    for task in tasks:
        if not isinstance(task, dict):
            continue
        game_id = _normalize_optional_text(task.get("game_id"))
        if game_id is None or game_id in seen:
            continue
        game_ids.append(game_id)
        seen.add(game_id)
    return game_ids


def _dedupe_candidate_tasks(tasks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[str] = set()
    for task in tasks:
        game_id = _normalize_optional_text(task.get("game_id"))
        if game_id is None or game_id in seen:
            continue
        deduped.append(task)
        seen.add(game_id)
    return deduped


def _candidate_game_id_set(tasks: list[dict[str, Any]]) -> set[str]:
    return {
        game_id
        for task in tasks
        if isinstance(task, dict)
        for game_id in [_normalize_optional_text(task.get("game_id"))]
        if game_id is not None
    }


def _dedupe_attempts(attempts: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[object, ...]] = set()
    for attempt in attempts:
        key = (
            attempt["age"],
            attempt["min_age"],
            attempt["max_age"],
            attempt["education"],
            attempt["gender"],
        )
        if key in seen:
            continue
        deduped.append(attempt)
        seen.add(key)
    return deduped


def _stable_sort_key(patient_id: str, base_date: str, game: dict[str, Any]) -> str:
    game_id = _normalize_optional_text(game.get("id")) or _normalize_optional_text(
        game.get("name")
    )
    payload = f"{patient_id}|{base_date}|{game_id or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _extract_game(row: dict[str, Any]) -> dict[str, Any]:
    value = row.get("g") if isinstance(row, dict) else None
    return value if isinstance(value, dict) else {}


def _fallback_failure_stage(reason: str) -> str:
    normalized = str(reason or "").strip().lower()
    if normalized in {"missing_entity_input"} or normalized.startswith("missing_"):
        return "input"
    if normalized in {"no_resolved_entity_names"}:
        return "entity_resolution"
    if "llm" in normalized:
        return "llm"
    return "candidate"


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


def _normalize_positive_int(value: object, field_name: str) -> int:
    parsed = _parse_optional_int(value, field_name)
    if parsed is None or parsed <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return parsed


def _parse_optional_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(float(str(value).strip()))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative.")
    return parsed
