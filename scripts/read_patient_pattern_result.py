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
from similar_user.utils.pattern_storage import PatternResultStore, StoredPatternResult


DEFAULT_QUERY_CONFIG_PATH = Path("config/query.yaml")


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
        "--query-config",
        default=str(DEFAULT_QUERY_CONFIG_PATH),
        help="Path to the query YAML config file.",
    )
    return parser.parse_args()


def read_patient_pattern_result(
    patient_id: str,
    *,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    query_config_path: str | Path = DEFAULT_QUERY_CONFIG_PATH,
) -> StoredPatternResult:
    """Load one saved patient pattern result from disk."""
    return PatternResultStore(query_config_path).load(pattern, patient_id)


def main() -> int:
    """Read and print one saved patient pattern result."""
    args = parse_args()
    try:
        result = read_patient_pattern_result(
            args.patient_id,
            pattern=args.pattern,
            query_config_path=args.query_config,
        )
    except Exception as exc:
        print(f"Read patient pattern result failed: {exc}", file=sys.stderr)
        return 1

    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
