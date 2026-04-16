"""Score saved patient pattern paths with a rule-based scorer."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from similar_user.domain.graph_schema import (
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
)
from similar_user.services.path_scoring import PathScorer
from similar_user.utils.logger import get_logger
from similar_user.utils.pattern_storage import PatternResultStore


DEFAULT_QUERY_CONFIG_PATH = Path("config/settings.yaml")
LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for scoring saved patient results."""
    parser = argparse.ArgumentParser(
        description="Score saved patient pattern paths from local JSON storage."
    )
    parser.add_argument("patient_id", help="Patient identifier used in the stored file.")
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
    parser.add_argument(
        "--path-index",
        type=int,
        default=None,
        help="Only score one path at the given zero-based index.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Return the top-k scored paths ordered by total_score descending.",
    )
    return parser.parse_args()


def score_patient_pattern_result(
    patient_id: str,
    *,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    query_config_path: str | Path = DEFAULT_QUERY_CONFIG_PATH,
    path_index: int | None = None,
    top_k: int | None = None,
) -> dict[str, object]:
    """Load a saved patient result and score its domain paths."""
    stored_result = PatternResultStore(query_config_path).load(pattern, patient_id)
    domain_paths = stored_result.to_domain_paths()

    if top_k is not None and top_k <= 0:
        raise ValueError(f"top_k must be greater than 0, got {top_k}.")

    if path_index is not None:
        if path_index < 0 or path_index >= len(domain_paths):
            raise IndexError(
                f"path_index {path_index} is out of range for {len(domain_paths)} paths."
            )
        selected = [(path_index, domain_paths[path_index])]
    else:
        selected = list(enumerate(domain_paths))

    scorer = PathScorer()
    scored_paths = [
        {
            "path_index": index,
            "score": scorer.score(path).to_dict(),
            "path": stored_result.paths[index],
        }
        for index, path in selected
    ]
    if path_index is None:
        scored_paths.sort(
            key=lambda item: float(item["score"]["total_score"]),  # type: ignore[index]
            reverse=True,
        )
        if top_k is not None:
            scored_paths = scored_paths[:top_k]

    retrieval_context = stored_result.retrieval_context
    split_training_date = None
    if isinstance(retrieval_context, dict):
        raw_split_training_date = retrieval_context.get("split_training_date")
        if isinstance(raw_split_training_date, str) and raw_split_training_date.strip():
            split_training_date = raw_split_training_date.strip()

    return {
        "patient_id": stored_result.patient_id,
        "pattern": stored_result.pattern,
        "path_count": len(domain_paths),
        "scored_path_count": len(scored_paths),
        "retrieval_context": {
            "split_training_date": split_training_date,
            "path_scope": (
                f"当前评分结果中的 paths 来自训练日期小于等于 {split_training_date} 的检索集合"
                if split_training_date is not None
                else "当前评分结果中的 paths 来自已保存的检索集合"
            ),
        },
        "scores": scored_paths,
    }


def main() -> int:
    """Score saved patient pattern paths and log JSON output."""
    args = parse_args()
    try:
        result = score_patient_pattern_result(
            args.patient_id,
            pattern=args.pattern,
            query_config_path=args.query_config,
            path_index=args.path_index,
            top_k=args.top_k,
        )
    except Exception as exc:
        LOGGER.exception("Score patient pattern result failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
