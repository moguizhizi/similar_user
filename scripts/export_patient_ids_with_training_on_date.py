"""Export patient IDs with training records on a given date.

常用执行方式：

    python scripts/export_patient_ids_with_training_on_date.py --base-date 2023-10-15

默认输出到：

    data/patient_ids/base_2023-10-15/patients_active_2023-10-15.txt
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

from similar_user.data_access.kg_repository import KgRepository
from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.services.task_prediction import parse_date_value
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger

from scripts.score_pattern_paths import DEFAULT_CONFIG_PATH


LOGGER = get_logger(__name__)
DEFAULT_OUTPUT_DIR = Path("data/patient_ids")
DEFAULT_PATIENT_ID_LIMIT = 100


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Export patient IDs with training records on base_date."
    )
    parser.add_argument(
        "--base-date",
        required=True,
        help="Training date used to find active patient IDs.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Base directory for the generated patient ID file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=DEFAULT_PATIENT_ID_LIMIT,
        help="Fetch at most this many patient IDs in the Neo4j query.",
    )
    return parser.parse_args()


def build_patient_ids_output_path(
    *,
    base_date: str,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> Path:
    """Build the date-specific output path."""
    parsed_base_date = parse_date_value(base_date, "base_date")
    normalized_base_date = parsed_base_date.isoformat()
    return (
        Path(output_dir)
        / f"base_{normalized_base_date}"
        / f"patients_active_{normalized_base_date}.txt"
    )


def write_patient_ids(patient_ids: list[str], output_path: str | Path) -> Path:
    """Write one patient ID per line."""
    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(
        "".join(f"{patient_id}\n" for patient_id in patient_ids),
        encoding="utf-8",
    )
    return resolved_output_path


def export_patient_ids_with_training_on_date(
    *,
    base_date: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    limit: int | None = DEFAULT_PATIENT_ID_LIMIT,
) -> dict[str, Any]:
    """Fetch active patient IDs from Neo4j and write them to a date-specific file."""
    parsed_base_date = parse_date_value(base_date, "base_date")
    normalized_base_date = parsed_base_date.isoformat()
    if limit is not None and limit <= 0:
        raise ValueError("limit must be a positive integer.")
    output_path = build_patient_ids_output_path(
        base_date=normalized_base_date,
        output_dir=output_dir,
    )
    with Neo4jClient.from_config(config_path) as client:
        user_service = UserService(
            kg_repository=KgRepository(
                client=client,
                config_path=Path(config_path),
            )
        )
        patient_ids = user_service.get_patient_ids_with_training_on_date(
            normalized_base_date,
            limit,
        )

    written_path = write_patient_ids(patient_ids, output_path)
    return {
        "base_date": normalized_base_date,
        "limit": limit,
        "patient_count": len(patient_ids),
        "output_path": str(written_path),
    }


def main() -> int:
    """Run the export workflow."""
    args = parse_args()
    try:
        result = export_patient_ids_with_training_on_date(
            base_date=args.base_date,
            config_path=args.config,
            output_dir=args.output_dir,
            limit=args.limit,
        )
    except Exception as exc:
        LOGGER.exception("Failed to export patient IDs: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
