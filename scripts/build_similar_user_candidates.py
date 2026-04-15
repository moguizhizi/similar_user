"""Build deduplicated similar-user candidates from top-k scored paths."""

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

from similar_user.domain.graph_schema import (
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    PathPattern,
)
from similar_user.domain.path_models import (
    PatientTasksetTaskGameTaskTasksetPatientPath,
)
from similar_user.utils.logger import get_logger

from scripts.score_patient_pattern_result import (
    DEFAULT_QUERY_CONFIG_PATH,
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
        description="Build deduplicated similar-user candidates from top-k scored paths."
    )
    parser.add_argument("patient_id", help="Patient identifier used in the stored file.")
    parser.add_argument(
        "--top-k",
        type=int,
        required=True,
        help="Use the top-k scored paths as the candidate source.",
    )
    parser.add_argument(
        "--pattern",
        default=PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        help="Pattern name used to locate the saved result.",
    )
    parser.add_argument(
        "--query-config",
        default=str(DEFAULT_QUERY_CONFIG_PATH),
        help="Path to the query YAML config file.",
    )
    return parser.parse_args()


def build_similar_user_candidates(
    patient_id: str,
    *,
    top_k: int,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    query_config_path: str | Path = DEFAULT_QUERY_CONFIG_PATH,
) -> dict[str, Any]:
    """Aggregate deduplicated candidate users from top-k scored paths."""
    scored_result = score_patient_pattern_result(
        patient_id,
        pattern=pattern,
        query_config_path=query_config_path,
        top_k=top_k,
    )
    return aggregate_candidates_from_scored_paths(scored_result, top_k=top_k)


def aggregate_candidates_from_scored_paths(
    scored_result: dict[str, Any],
    *,
    top_k: int,
) -> dict[str, Any]:
    """Deduplicate candidate users from typed scored paths and summarize evidence."""
    scored_domain_paths = _build_scored_domain_paths(scored_result)

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

    return {
        "patient_id": scored_result.get("patient_id"),
        "pattern": scored_result.get("pattern"),
        "top_k": top_k,
        "path_count": scored_result.get("path_count", 0),
        "scored_path_count": scored_result.get("scored_path_count", 0),
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
            top_k=args.top_k,
            pattern=args.pattern,
            query_config_path=args.query_config,
        )
    except Exception as exc:
        LOGGER.exception("Build similar user candidates failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
