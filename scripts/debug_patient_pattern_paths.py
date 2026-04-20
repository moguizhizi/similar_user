"""Run the patient pattern path flow against a configured Neo4j instance."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from similar_user.data_access.kg_repository import KgRepository
from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger
from similar_user.utils.pattern_storage import save_pattern_result


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the patient path flow."""
    parser = argparse.ArgumentParser(
        description="Run the patient fixed-pattern path flow."
    )
    parser.add_argument("patient_id", help="Patient identifier used in Neo4j queries.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the Neo4j YAML config file.",
    )
    parser.add_argument(
        "--base-date",
        required=True,
        help="Exclusive window end date used to build paths, for example 2022-05-22.",
    )
    parser.add_argument(
        "--window-days",
        type=int,
        required=True,
        help="Number of days before base_date included in path retrieval.",
    )
    return parser.parse_args()


def run_patient_pattern_path_flow(
    patient_id: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    base_date: str,
    window_days: int,
) -> dict[str, object]:
    """Connect to Neo4j and run the patient pattern path orchestration."""
    LOGGER.info(
        "Starting patient pattern path flow: patient_id=%s, base_date=%s, window_days=%s, config_path=%s",
        patient_id,
        base_date,
        window_days,
        config_path,
    )
    with Neo4jClient.from_config(config_path) as client:
        repository = KgRepository(client=client, config_path=Path(config_path))
        service = UserService(kg_repository=repository)
        result = service.get_patient_pattern_paths(
            patient_id,
            base_date=base_date,
            window_days=window_days,
        )
        output_path = save_pattern_result(result, repository.config_path)
        retrieval_context = result.get("retrieval_context") or {}
        LOGGER.info(
            "Completed patient pattern path flow: patient_id=%s, path_window=%s, path_count=%s, output_path=%s",
            patient_id,
            retrieval_context.get("path_window"),
            len(retrieval_context.get("paths", [])),
            output_path,
        )
        return result


def main() -> int:
    """Run the patient pattern path flow and persist the JSON result."""
    args = parse_args()
    try:
        run_patient_pattern_path_flow(
            args.patient_id,
            config_path=args.config,
            base_date=args.base_date,
            window_days=args.window_days,
        )
    except Exception as exc:
        LOGGER.exception(
            "Patient pattern path flow failed: patient_id=%s, config_path=%s",
            args.patient_id,
            args.config,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
