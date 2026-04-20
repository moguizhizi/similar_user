"""Run the full similar-user pipeline from path retrieval to candidate ranking."""

from __future__ import annotations

import argparse
import json
import sys
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
)
from similar_user.utils.logger import get_logger

from scripts.build_similar_user_candidates import build_similar_user_candidates
from scripts.debug_patient_pattern_paths import run_patient_pattern_path_flow
from scripts.score_patient_pattern_result import DEFAULT_CONFIG_PATH


LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the full similar-user pipeline."""
    parser = argparse.ArgumentParser(
        description="Run path retrieval, path scoring, and similar-user candidate ranking."
    )
    parser.add_argument("patient_id", help="Patient identifier used in Neo4j queries.")
    parser.add_argument(
        "--pattern",
        default=PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        help="Pattern name used to locate the saved result.",
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
    return parser.parse_args()


def run_similar_user_pipeline(
    patient_id: str,
    *,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    config_path: str | Path | None = None,
    skip_path_build: bool = False,
) -> dict[str, Any]:
    """Run path retrieval, scoring, and candidate ranking as one workflow."""
    resolved_config_path = DEFAULT_CONFIG_PATH if config_path is None else config_path
    path_generation = None
    if not skip_path_build:
        path_result = run_patient_pattern_path_flow(
            patient_id,
            config_path=resolved_config_path,
        )
        path_generation = _summarize_path_result(path_result)

    candidate_result = build_similar_user_candidates(
        patient_id,
        pattern=pattern,
        config_path=resolved_config_path,
    )
    return {
        "patient_id": patient_id,
        "pattern": pattern,
        "config_path": str(resolved_config_path),
        "skip_path_build": skip_path_build,
        "path_generation": path_generation,
        "candidate_result": candidate_result,
    }


def _summarize_path_result(path_result: dict[str, object]) -> dict[str, object]:
    """Summarize the saved path result without logging every path row."""
    retrieval_context = path_result.get("retrieval_context")
    paths = []
    split_training_date = None
    if isinstance(retrieval_context, dict):
        raw_paths = retrieval_context.get("paths")
        if isinstance(raw_paths, list):
            paths = raw_paths
        raw_split_training_date = retrieval_context.get("split_training_date")
        if isinstance(raw_split_training_date, str) and raw_split_training_date.strip():
            split_training_date = raw_split_training_date.strip()

    return {
        "patient_id": path_result.get("patient_id"),
        "pattern": path_result.get("pattern"),
        "training_date_count": path_result.get("training_date_count"),
        "split_training_date": split_training_date,
        "path_count": len(paths),
    }


def main() -> int:
    """Run the full pipeline and log the JSON result."""
    args = parse_args()
    try:
        result = run_similar_user_pipeline(
            args.patient_id,
            pattern=args.pattern,
            config_path=args.config,
            skip_path_build=args.skip_path_build,
        )
    except Exception as exc:
        LOGGER.exception(
            "Similar user pipeline failed: patient_id=%s, config_path=%s",
            args.patient_id,
            args.config,
        )
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
