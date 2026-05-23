"""Export distinct patient training dates in descending order.

常用执行方式：

    python scripts/export_training_dates.py

默认输出到：

    data/training_dates/training_dates_desc.txt
"""

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

from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.utils.logger import get_logger

from scripts.score_pattern_paths import DEFAULT_CONFIG_PATH


LOGGER = get_logger(__name__)
DEFAULT_OUTPUT_PATH = Path("data/training_dates/training_dates_desc.txt")

TRAINING_DATES_DESC_QUERY = """
MATCH (:Patient)--(s:TaskInstanceSet)
WHERE s.`训练日期` IS NOT NULL
RETURN DISTINCT toString(date(s.`训练日期`)) AS training_date
ORDER BY training_date DESC
""".strip()


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Export distinct patient training dates in descending order."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output file path for the generated training date list.",
    )
    return parser.parse_args()


def write_training_dates(training_dates: list[str], output_path: str | Path) -> Path:
    """Write one training date per line."""
    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(
        "".join(f"{training_date}\n" for training_date in training_dates),
        encoding="utf-8",
    )
    return resolved_output_path


def export_training_dates(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
) -> dict[str, Any]:
    """Fetch distinct training dates from Neo4j and write them to a file."""
    with Neo4jClient.from_config(config_path) as client:
        rows = client.run_query(TRAINING_DATES_DESC_QUERY, parameters={})

    training_dates = [
        str(row.get("training_date")).strip()
        for row in rows
        if str(row.get("training_date") or "").strip()
    ]
    written_path = write_training_dates(training_dates, output_path)
    return {
        "training_date_count": len(training_dates),
        "output_path": str(written_path),
    }


def main() -> int:
    """Run the export workflow."""
    args = parse_args()
    try:
        result = export_training_dates(
            config_path=args.config,
            output_path=args.output,
        )
    except Exception as exc:
        LOGGER.exception("Failed to export training dates: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
