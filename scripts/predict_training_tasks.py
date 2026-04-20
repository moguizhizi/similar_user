"""Predict training tasks from run_similar_user_pipeline.py output."""

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
from similar_user.services.llm_client import LlmClient
from similar_user.services.task_prediction import (
    DEFAULT_TASK_TOP_K,
    TrainingTaskPredictionService,
    parse_json_object_from_text,
)
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger

from scripts.score_patient_pattern_result import DEFAULT_CONFIG_PATH


LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for training-task prediction."""
    parser = argparse.ArgumentParser(
        description="Predict training tasks from similar-user pipeline output."
    )
    parser.add_argument(
        "--similar-users-file",
        help="Path to JSON output from scripts/run_similar_user_pipeline.py.",
    )
    parser.add_argument(
        "--from-stdin",
        action="store_true",
        help="Read run_similar_user_pipeline.py output from stdin.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--base-date",
        required=True,
        help="Prediction base date; target tasks use the two days before this date.",
    )
    parser.add_argument(
        "--task-top-k",
        type=int,
        default=DEFAULT_TASK_TOP_K,
        help="Number of predicted training tasks to return.",
    )
    parser.add_argument(
        "--output-level",
        choices=("ids", "scores", "full"),
        default="ids",
        help="Output detail level: ids, scores, or full.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip the LLM call and return deterministic candidate-task predictions.",
    )
    parser.add_argument(
        "--include-prompt",
        action="store_true",
        help="Include the generated LLM prompt in full output.",
    )
    return parser.parse_args()


def run_training_task_prediction(
    pipeline_result: dict[str, Any],
    *,
    base_date: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    task_top_k: int = DEFAULT_TASK_TOP_K,
    use_llm: bool = True,
    include_prompt: bool = False,
) -> dict[str, Any]:
    """Run training-task prediction from an existing candidate result."""
    with Neo4jClient.from_config(config_path) as client:
        user_service = UserService(
            kg_repository=KgRepository(
                client=client,
                config_path=Path(config_path),
            )
        )
        llm_client = LlmClient.from_config(config_path) if use_llm else None
        service = TrainingTaskPredictionService(
            user_service=user_service,
            llm_client=llm_client,
        )
        return service.predict_from_pipeline_result(
            pipeline_result,
            base_date=base_date,
            task_top_k=task_top_k,
            use_llm=use_llm,
            include_prompt=include_prompt,
        )


def summarize_prediction_result(
    result: dict[str, Any],
    *,
    output_level: str,
) -> dict[str, Any]:
    """Build compact CLI output."""
    if output_level == "full":
        return result
    predictions = result.get("predicted_training_tasks")
    if not isinstance(predictions, list):
        predictions = []
    if output_level == "ids":
        return {
            "patient_id": result.get("patient_id"),
            "predicted_training_task_ids": [
                prediction.get("game_id")
                for prediction in predictions
                if isinstance(prediction, dict)
            ],
        }
    if output_level == "scores":
        return {
            "patient_id": result.get("patient_id"),
            "predicted_training_tasks": [
                {
                    "game_id": prediction.get("game_id"),
                    "game_name": prediction.get("game_name"),
                    "confidence": prediction.get("confidence"),
                }
                for prediction in predictions
                if isinstance(prediction, dict)
            ],
        }
    raise ValueError(f"Unsupported output level: {output_level}.")


def _read_pipeline_result(args: argparse.Namespace) -> dict[str, Any]:
    if args.from_stdin and args.similar_users_file:
        raise ValueError("--from-stdin and --similar-users-file cannot be used together.")
    if args.from_stdin:
        return parse_json_object_from_text(sys.stdin.read())
    if args.similar_users_file:
        path = Path(args.similar_users_file)
        return parse_json_object_from_text(path.read_text(encoding="utf-8"))
    raise ValueError(
        "similar-user pipeline output is required. Use --similar-users-file or --from-stdin."
    )


def main() -> int:
    """Predict training tasks and log the JSON result."""
    args = parse_args()
    try:
        pipeline_result = _read_pipeline_result(args)
        result = run_training_task_prediction(
            pipeline_result,
            base_date=args.base_date,
            config_path=args.config,
            task_top_k=args.task_top_k,
            use_llm=not args.dry_run,
            include_prompt=args.include_prompt,
        )
        output = summarize_prediction_result(result, output_level=args.output_level)
    except Exception as exc:
        LOGGER.exception("Training task prediction failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
