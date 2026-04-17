"""Build ranked similar-user candidates from top-k scored paths."""

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

from config.settings import load_query_settings
from similar_user.data_access.kg_repository import KgRepository
from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.domain.graph_schema import (
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
)
from similar_user.services.similarity.candidate_service import SimilarUserCandidateService
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger

from scripts.score_patient_pattern_result import (
    DEFAULT_CONFIG_PATH,
    score_patient_pattern_result,
)


LOGGER = get_logger(__name__)


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

    with Neo4jClient.from_config(DEFAULT_CONFIG_PATH) as client:
        user_service = UserService(
            kg_repository=KgRepository(client=client, config_path=DEFAULT_CONFIG_PATH)
        )
        candidate_service = SimilarUserCandidateService(user_service=user_service)
        scored_result = score_patient_pattern_result(
            patient_id,
            pattern=pattern,
            config_path=DEFAULT_CONFIG_PATH,
            top_k=ranking_settings.path_top_k,
        )
        return candidate_service.aggregate_candidates_from_scored_paths(
            scored_result,
            path_top_k=ranking_settings.path_top_k,
            candidate_top_k=ranking_settings.candidate_top_k,
        )


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
