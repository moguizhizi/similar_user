"""Read one saved patient pattern path result from local storage."""

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
from similar_user.utils.logger import get_logger
from similar_user.utils.pattern_storage import PatternResultStore, StoredPatternResult


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for reading a stored result."""
    parser = argparse.ArgumentParser(
        description="Read a saved patient pattern path result from local JSON storage."
    )
    parser.add_argument("patient_id", help="Patient identifier used in the stored file.")
    parser.add_argument(
        "--pattern",
        default=PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        help="Pattern name used to locate the saved result.",
    )
    parser.add_argument(
        "--config",
        dest="config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--base-date",
        required=True,
        help="Path cache base date used to locate the saved pattern result.",
    )
    parser.add_argument(
        "--query-family",
        default=None,
        choices=(
            "training_order_source_window",
            "date_window",
            "training_order_local_sampling_source_window",
            "training_order_age_source_window",
            "training_order_age_edu_source_window",
            "training_order_age_completed_source_window",
            "training_order_age_edu_completed_source_window",
            "training_order_age_edu_task_completed_source_window",
            "training_order_dual_window",
            "training_order_local_sampling_dual_window",
            "training_order_age_dual_window",
            "training_order_age_edu_dual_window",
            "training_order_age_completed_dual_window",
            "training_order_age_edu_completed_dual_window",
            "training_order_age_edu_task_completed_dual_window",
        ),
        help="Path cache query family used to locate the saved pattern result.",
    )
    return parser.parse_args()


def read_patient_pattern_result(
    patient_id: str,
    *,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    base_date: str,
    query_family: str | None = None,
) -> StoredPatternResult:
    """Load one saved patient pattern result from disk."""
    return PatternResultStore(config_path).load(
        pattern,
        patient_id,
        base_date=base_date,
        query_family=query_family,
    )


def main() -> int:
    """Read and log one saved patient pattern result."""
    args = parse_args()
    try:
        result = read_patient_pattern_result(
            args.patient_id,
            pattern=args.pattern,
            config_path=args.config,
            base_date=args.base_date,
            query_family=args.query_family,
        )
    except Exception as exc:
        LOGGER.exception("Read patient pattern result failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
