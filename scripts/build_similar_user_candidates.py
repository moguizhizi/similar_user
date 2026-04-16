"""Build ranked similar-user candidates from top-k scored paths."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import load_query_settings
from similar_user.domain.graph_schema import (
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    PathPattern,
)
from similar_user.domain.path_models import (
    PatientTasksetTaskGameTaskTasksetPatientPath,
)
from similar_user.utils.logger import get_logger

from scripts.score_patient_pattern_result import (
    DEFAULT_CONFIG_PATH,
    score_patient_pattern_result,
)


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class ScoredDomainPath:
    """One scored raw path paired with its typed domain path."""

    path_index: int | None
    total_score: float | None
    path: PatientTasksetTaskGameTaskTasksetPatientPath


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for candidate aggregation."""
    parser = argparse.ArgumentParser(
        description="Build ranked similar-user candidates from top-k scored paths."
    )
    parser.add_argument("patient_id", help="Patient identifier used in the stored file.")
    parser.add_argument(
        "--pattern",
        default=PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        help="Pattern name used to locate the saved result.",
    )
    return parser.parse_args()


def build_similar_user_candidates(
    patient_id: str,
    *,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
) -> dict[str, Any]:
    """Aggregate ranked candidate users from top-k scored paths."""
    ranking_settings = load_query_settings(DEFAULT_CONFIG_PATH).candidate_ranking

    scored_result = score_patient_pattern_result(
        patient_id,
        pattern=pattern,
        config_path=DEFAULT_CONFIG_PATH,
        top_k=ranking_settings.path_top_k,
    )
    return aggregate_candidates_from_scored_paths(
        scored_result,
        path_top_k=ranking_settings.path_top_k,
        candidate_top_k=ranking_settings.candidate_top_k,
    )


def aggregate_candidates_from_scored_paths(
    scored_result: dict[str, Any],
    *,
    path_top_k: int,
    candidate_top_k: int,
) -> dict[str, Any]:
    """Deduplicate candidate users from typed scored paths and summarize evidence."""
    if path_top_k <= 0:
        raise ValueError(f"path_top_k must be greater than 0, got {path_top_k}.")
    if candidate_top_k <= 0:
        raise ValueError(
            f"candidate_top_k must be greater than 0, got {candidate_top_k}."
        )

    scored_domain_paths = _build_scored_domain_paths(scored_result)
    retrieval_context = scored_result.get("retrieval_context")
    split_training_date = None
    if isinstance(retrieval_context, dict):
        raw_split_training_date = retrieval_context.get("split_training_date")
        if isinstance(raw_split_training_date, str) and raw_split_training_date.strip():
            split_training_date = raw_split_training_date.strip()

    candidate_buckets: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "patient_id": None,
            "path_indices": [],
            "match_count": 0,
            "best_score": None,
            "avg_score": 0.0,
            "_score_sum": 0.0,
        }
    )

    for scored_path in scored_domain_paths:
        candidate_id = _extract_candidate_patient_id_from_domain_path(scored_path.path)
        bucket = candidate_buckets[candidate_id]
        bucket["patient_id"] = candidate_id
        bucket["match_count"] += 1
        if isinstance(scored_path.path_index, int):
            bucket["path_indices"].append(scored_path.path_index)
        if scored_path.total_score is not None:
            bucket["_score_sum"] += scored_path.total_score
            if (
                bucket["best_score"] is None
                or scored_path.total_score > bucket["best_score"]
            ):
                bucket["best_score"] = scored_path.total_score

    candidates: list[dict[str, Any]] = []
    for bucket in candidate_buckets.values():
        match_count = bucket["match_count"]
        score_sum = bucket.pop("_score_sum")
        bucket["path_indices"] = sorted(set(bucket["path_indices"]))
        bucket["avg_score"] = round(score_sum / match_count, 2) if match_count else 0.0
        if bucket["best_score"] is not None:
            bucket["best_score"] = round(bucket["best_score"], 2)
        candidates.append(bucket)

    candidates.sort(
        key=lambda item: (
            float(item["best_score"]) if item["best_score"] is not None else float("-inf"),
            item["match_count"],
            item["patient_id"],
        ),
        reverse=True,
    )
    candidates = candidates[:candidate_top_k]

    return {
        "patient_id": scored_result.get("patient_id"),
        "pattern": scored_result.get("pattern"),
        "path_top_k": path_top_k,
        "candidate_top_k": candidate_top_k,
        "path_count": scored_result.get("path_count", 0),
        "scored_path_count": scored_result.get("scored_path_count", 0),
        "retrieval_context": {
            "split_training_date": split_training_date,
            "candidate_scope": (
                "候选相似用户来自训练日期小于等于 "
                f"{split_training_date} 的 top-{path_top_k} path 去重结果，"
                f"最终返回 top-{candidate_top_k} 候选用户"
                if split_training_date is not None
                else (
                    f"候选相似用户来自已保存检索集合的 top-{path_top_k} "
                    f"path 去重结果，最终返回 top-{candidate_top_k} 候选用户"
                )
            ),
        },
        "candidate_count": len(candidates),
        "candidates": candidates,
    }


def _build_scored_domain_paths(scored_result: dict[str, Any]) -> list[ScoredDomainPath]:
    """Convert scored raw path payloads to typed scored domain paths."""
    pattern = _coerce_supported_candidate_pattern(scored_result.get("pattern"))
    scored_domain_paths: list[ScoredDomainPath] = []

    for scored_path in scored_result.get("scores", []):
        if not isinstance(scored_path, dict):
            continue
        domain_path = _build_domain_path_from_scored_path(scored_path, pattern)
        if domain_path is None:
            continue
        scored_domain_paths.append(
            ScoredDomainPath(
                path_index=_extract_path_index(scored_path),
                total_score=_extract_total_score(scored_path),
                path=domain_path,
            )
        )

    return scored_domain_paths


def _coerce_supported_candidate_pattern(value: object) -> PathPattern:
    """Validate and normalize the candidate-supported path pattern."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("scored_result.pattern must be a non-empty string.")

    try:
        pattern = PathPattern(value.strip())
    except ValueError as exc:
        raise ValueError(
            f"Unsupported pattern for candidate aggregation: {value.strip()}"
        ) from exc
    if pattern != PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT:
        raise ValueError(f"Unsupported pattern for candidate aggregation: {pattern.value}")
    return pattern


def _build_domain_path_from_scored_path(
    scored_path: dict[str, Any],
    pattern: PathPattern,
) -> PatientTasksetTaskGameTaskTasksetPatientPath | None:
    """Build one typed domain path from a scored raw path payload."""
    raw_path = scored_path.get("path")
    if not isinstance(raw_path, dict):
        return None

    path_payload = {**raw_path, "pattern": pattern.value}
    if pattern == PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT:
        try:
            return PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(path_payload)
        except ValueError:
            return None
    raise ValueError(f"Unsupported pattern for candidate aggregation: {pattern.value}")


def _extract_candidate_patient_id_from_domain_path(
    path: PatientTasksetTaskGameTaskTasksetPatientPath,
) -> str:
    """Extract the similar patient id from a typed domain path."""
    return path.p2.id


def _extract_total_score(scored_path: dict[str, Any]) -> float | None:
    """Extract total score from one scored raw path payload."""
    score = scored_path.get("score")
    if not isinstance(score, dict):
        return None
    raw_total_score = score.get("total_score")
    if not isinstance(raw_total_score, (int, float)):
        return None
    return float(raw_total_score)


def _extract_path_index(scored_path: dict[str, Any]) -> int | None:
    """Extract path index from one scored raw path payload."""
    path_index = scored_path.get("path_index")
    return path_index if isinstance(path_index, int) else None


def main() -> int:
    """Build similar-user candidates and log the JSON result."""
    args = parse_args()
    try:
        result = build_similar_user_candidates(
            args.patient_id,
            pattern=args.pattern,
        )
    except Exception as exc:
        LOGGER.exception("Build similar user candidates failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
