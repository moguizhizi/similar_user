"""Client for the external training-task score service."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import requests


class TrainingTaskScoreError(RuntimeError):
    """Raised when the external score service cannot return usable scores."""


@dataclass(frozen=True)
class TrainingTaskScoreClient:
    """Call the external ``/training_task_score`` endpoint."""

    url: str
    timeout_seconds: float = 10.0
    session: requests.Session | None = None

    def score_tasks(
        self,
        task_ids: list[str],
        *,
        ai_params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Return task scores aligned with the requested task ID order."""
        normalized_task_ids = _normalize_task_ids(task_ids)
        if not normalized_task_ids:
            return []

        payload = build_training_task_score_payload(
            normalized_task_ids,
            ai_params=ai_params,
        )
        session = self.session or requests.Session()
        try:
            response = session.post(
                self.url,
                json=payload,
                timeout=self.timeout_seconds,
            )
            response.raise_for_status()
            response_payload = response.json()
        except requests.Timeout as exc:
            raise TrainingTaskScoreError("Training task score request timed out.") from exc
        except requests.RequestException as exc:
            raise TrainingTaskScoreError(
                f"Training task score request failed: {exc}"
            ) from exc
        except ValueError as exc:
            raise TrainingTaskScoreError(
                "Training task score response must be valid JSON."
            ) from exc

        scores = _extract_scores(response_payload, len(normalized_task_ids))
        return [
            {
                "task_id": task_id,
                "score": score,
            }
            for task_id, score in zip(normalized_task_ids, scores)
        ]


def build_training_task_score_payload(
    task_ids: list[str],
    *,
    ai_params: dict[str, Any],
) -> dict[str, Any]:
    """Build the request body expected by the score service."""
    ba_scores = ai_params.get("pre_score_ba", ai_params.get("ba"))
    if not isinstance(ba_scores, list):
        raise TrainingTaskScoreError("ai_params must contain list field 'pre_score_ba' or 'ba'.")

    return {
        "tt_list": _normalize_task_ids(task_ids),
        "pre_score_ba": ba_scores,
        "sex": ai_params.get("sex"),
        "education": ai_params.get("education"),
        "age": ai_params.get("age"),
        "sicksName": ai_params.get("sicksName") or [],
    }


def _normalize_task_ids(task_ids: list[str]) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for task_id in task_ids:
        text = str(task_id).strip()
        if not text or text in seen:
            continue
        normalized.append(text)
        seen.add(text)
    return normalized


def _extract_scores(response_payload: Any, expected_count: int) -> list[float]:
    if not isinstance(response_payload, dict):
        raise TrainingTaskScoreError("Training task score response must be an object.")
    raw_scores = response_payload.get("score")
    if not isinstance(raw_scores, list):
        raise TrainingTaskScoreError("Training task score response must contain list field 'score'.")
    if len(raw_scores) != expected_count:
        raise TrainingTaskScoreError(
            "Training task score count does not match requested task count: "
            f"expected {expected_count}, got {len(raw_scores)}."
        )

    scores: list[float] = []
    for index, raw_score in enumerate(raw_scores):
        if isinstance(raw_score, bool) or not isinstance(raw_score, (int, float)):
            raise TrainingTaskScoreError(
                f"Training task score at index {index} must be a number."
            )
        scores.append(float(raw_score))
    return scores
