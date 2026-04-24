"""Predict training tasks from the full similar-user workflow.

这个脚本串联相似用户候选生成和训练任务预测：

1. 调用 `scripts/run_similar_user_pipeline.py` 的流程，构建相似用户候选。
2. 根据目标患者、候选相似用户和训练任务时间窗上下文，构建训练任务推荐输入。
3. 默认调用配置中的 LLM 生成预测结果；使用 `--dry-run` 时跳过 LLM，返回确定性的候选任务结果。
4. 最后按 `--output-level` 输出任务 ID、任务分数或完整端到端结果。

如果已经有可用的离线 path 结果，可以使用 `--skip-path-build` 跳过 path 构建，
直接基于已保存结果生成相似用户候选并预测训练任务。

常用执行方式：

    python scripts/predict_training_tasks.py 40 --base-date 2022-05-22 --window-days 14
    python scripts/predict_training_tasks.py 40 --base-date 2022-05-22 --window-days 14 --save-prompt
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
from similar_user.services.llm_client import LlmClient
from similar_user.services.task_prediction import (
    DEFAULT_TASK_TOP_K,
    TrainingTaskPredictionService,
)
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger

from scripts.run_similar_user_pipeline import run_similar_user_pipeline
from scripts.score_patient_pattern_paths import DEFAULT_CONFIG_PATH
from similar_user.domain.graph_schema import (
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
)


LOGGER = get_logger(__name__)
DEFAULT_PROMPT_OUTPUT_DIR = Path("data/prompts")


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for training-task prediction."""
    parser = argparse.ArgumentParser(
        description="Run similar-user candidate generation and predict training tasks."
    )
    parser.add_argument("patient_id", help="Patient identifier used in Neo4j queries.")
    parser.add_argument(
        "--pattern",
        default=PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        help="Pattern name used to locate the saved similar-user path result.",
    )
    parser.add_argument(
        "--skip-path-build",
        action="store_true",
        help="Use existing saved paths and only run scoring plus candidate ranking.",
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
        "--window-days",
        type=int,
        required=True,
        help="Number of days before base_date used to query candidate-user tasks.",
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
    parser.add_argument(
        "--save-prompt",
        action="store_true",
        help="Save the generated LLM prompt to a text file for later lookup.",
    )
    parser.add_argument(
        "--prompt-output-dir",
        default=str(DEFAULT_PROMPT_OUTPUT_DIR),
        help="Directory used by --save-prompt to store prompt text files.",
    )
    return parser.parse_args()


def run_end_to_end_training_task_prediction(
    patient_id: str,
    *,
    base_date: str,
    window_days: int,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    skip_path_build: bool = False,
    task_top_k: int = DEFAULT_TASK_TOP_K,
    use_llm: bool = True,
    include_prompt: bool = False,
) -> dict[str, Any]:
    """Run similar-user generation and training-task prediction in one workflow."""
    pipeline_result = run_similar_user_pipeline(
        patient_id,
        pattern=pattern,
        config_path=config_path,
        skip_path_build=skip_path_build,
        base_date=base_date,
        window_days=window_days,
    )
    prediction_result = run_training_task_prediction(
        pipeline_result,
        base_date=base_date,
        window_days=window_days,
        config_path=config_path,
        task_top_k=task_top_k,
        use_llm=use_llm,
        include_prompt=include_prompt,
    )
    return {
        "patient_id": prediction_result.get("patient_id", patient_id),
        "similar_user_pipeline": pipeline_result,
        "training_task_prediction": prediction_result,
    }


def run_training_task_prediction(
    pipeline_result: dict[str, Any],
    *,
    base_date: str,
    window_days: int,
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
            window_days=window_days,
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

    prediction_result = result.get("training_task_prediction")
    if isinstance(prediction_result, dict):
        result = prediction_result

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


def write_prompt_to_file(
    result: dict[str, Any],
    *,
    output_dir: str | Path,
    base_date: str,
) -> Path:
    """Write the generated LLM prompt to a searchable text file."""
    prediction_result = result.get("training_task_prediction")
    if isinstance(prediction_result, dict):
        result = prediction_result

    llm_prompt = result.get("llm_prompt")
    if not isinstance(llm_prompt, str) or not llm_prompt.strip():
        raise ValueError("No llm_prompt found in prediction result.")

    patient_id = str(result.get("patient_id") or "").strip()
    if not patient_id:
        raise ValueError("patient_id is required to save the prompt.")

    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    prompt_path = (
        resolved_output_dir
        / f"training_task_prompt_patient_{patient_id}_base_date_{base_date}.txt"
    )
    prompt_path.write_text(llm_prompt.strip() + "\n", encoding="utf-8")
    return prompt_path


def main() -> int:
    """Predict training tasks and log the JSON result."""
    args = parse_args()
    try:
        result = run_end_to_end_training_task_prediction(
            args.patient_id,
            base_date=args.base_date,
            window_days=args.window_days,
            pattern=args.pattern,
            config_path=args.config,
            skip_path_build=args.skip_path_build,
            task_top_k=args.task_top_k,
            use_llm=not args.dry_run,
            include_prompt=(args.include_prompt or args.save_prompt),
        )
        output = summarize_prediction_result(result, output_level=args.output_level)
        prompt_path = None
        if args.save_prompt:
            prompt_path = write_prompt_to_file(
                result,
                output_dir=args.prompt_output_dir,
                base_date=args.base_date,
            )
    except Exception as exc:
        LOGGER.exception("Training task prediction failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    if prompt_path is not None:
        LOGGER.info("Saved training-task prediction prompt to %s", prompt_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
