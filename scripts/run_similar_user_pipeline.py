"""Run the full similar-user pipeline from path building to candidate ranking.

这个脚本把相似用户候选生成流程串成一个入口：

1. 默认先调用 `scripts/build_patient_pattern_paths.py`，按时间窗口构建并保存固定模式 paths。
2. 再调用候选构建逻辑，读取已保存 paths、完成 path 打分，并聚合候选相似用户。
3. 最后按 `--output-level` 输出候选 ID、候选分数或完整结果。

如果已经有可用的离线 path 结果，可以使用 `--skip-path-build` 跳过第一步，直接基于已有结果打分并构建候选用户。

常用执行方式：

    python scripts/run_similar_user_pipeline.py 40 --base-date 2022-05-22 --window-days 14
"""

from __future__ import annotations

import argparse
import json
import sys
import time
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
from scripts.build_patient_pattern_paths import run_patient_pattern_path_flow
from scripts.score_patient_pattern_paths import DEFAULT_CONFIG_PATH


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
    parser.add_argument(
        "--output-level",
        choices=("ids", "scores", "full"),
        default="ids",
        help="Output detail level: ids, scores, or full.",
    )
    return parser.parse_args()


def run_similar_user_pipeline(
    patient_id: str,
    *,
    base_date: str,
    window_days: int,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    config_path: str | Path | None = None,
    skip_path_build: bool = False,
) -> dict[str, Any]:
    """Run path retrieval, scoring, and candidate ranking as one workflow."""
    resolved_config_path = DEFAULT_CONFIG_PATH if config_path is None else config_path
    started_at = time.perf_counter()
    LOGGER.debug(
        "Starting similar-user pipeline: patient_id=%s, pattern=%s, skip_path_build=%s, base_date=%s, window_days=%s, config_path=%s",
        patient_id,
        pattern,
        skip_path_build,
        base_date,
        window_days,
        resolved_config_path,
    )
    path_generation = None
    if not skip_path_build:
        path_result = run_patient_pattern_path_flow(
            patient_id,
            config_path=resolved_config_path,
            base_date=base_date,
            window_days=window_days,
        )
        path_generation = _summarize_path_result(path_result)
        _raise_if_path_result_empty(
            path_generation,
            patient_id=patient_id,
            base_date=base_date,
            window_days=window_days,
        )

    candidate_result = build_similar_user_candidates(
        patient_id,
        pattern=pattern,
        config_path=resolved_config_path,
    )
    result = {
        "patient_id": patient_id,
        "pattern": pattern,
        "config_path": str(resolved_config_path),
        "skip_path_build": skip_path_build,
        "base_date": base_date,
        "window_days": window_days,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "path_generation": path_generation,
        "candidate_result": candidate_result,
    }
    LOGGER.debug(
        "Completed similar-user pipeline: patient_id=%s, candidate_count=%s, elapsed_seconds=%s",
        patient_id,
        candidate_result.get("candidate_count"),
        result["elapsed_seconds"],
    )
    return result


def _summarize_path_result(path_result: dict[str, object]) -> dict[str, object]:
    """Summarize the saved path result without logging every path row."""
    retrieval_context = path_result.get("retrieval_context")
    paths = []
    path_window = None
    if isinstance(retrieval_context, dict):
        raw_paths = retrieval_context.get("paths")
        if isinstance(raw_paths, list):
            paths = raw_paths
        raw_path_window = retrieval_context.get("path_window")
        if isinstance(raw_path_window, dict):
            path_window = raw_path_window

    return {
        "patient_id": path_result.get("patient_id"),
        "pattern": path_result.get("pattern"),
        "path_window": path_window,
        "path_count": len(paths),
    }


def _raise_if_path_result_empty(
    path_generation: dict[str, object],
    *,
    patient_id: str,
    base_date: str,
    window_days: int,
) -> None:
    """Stop the pipeline when freshly built path data is empty."""
    path_count = path_generation.get("path_count")
    if isinstance(path_count, int) and path_count > 0:
        return
    raise ValueError(
        "path_result does not contain paths: "
        f"patient_id={patient_id}, base_date={base_date}, window_days={window_days}."
    )


def summarize_pipeline_result(
    result: dict[str, Any],
    *,
    output_level: str = "ids",
) -> dict[str, Any]:
    """Build the compact pipeline output used by default CLI logging."""
    if output_level not in {"ids", "scores"}:
        raise ValueError(f"Unsupported summary output level: {output_level}.")
    candidate_result = result.get("candidate_result")
    candidate_summary: dict[str, Any] | None = None
    if isinstance(candidate_result, dict):
        candidate_summary = {
            "patient_id": candidate_result.get("patient_id"),
            "pattern": candidate_result.get("pattern"),
            "path_top_k": candidate_result.get("path_top_k"),
            "candidate_top_k": candidate_result.get("candidate_top_k"),
            "path_count": candidate_result.get("path_count"),
            "scored_path_count": candidate_result.get("scored_path_count"),
            "path_window": _extract_path_window(candidate_result),
            "candidate_count": candidate_result.get("candidate_count"),
        }
        candidates = candidate_result.get("candidates")
        if output_level == "ids":
            candidate_summary["candidate_ids"] = _extract_candidate_ids(candidates)
        else:
            candidate_summary["candidates"] = _extract_candidate_scores(candidates)

    return {
        "patient_id": result.get("patient_id"),
        "pattern": result.get("pattern"),
        "config_path": result.get("config_path"),
        "skip_path_build": result.get("skip_path_build"),
        "base_date": result.get("base_date"),
        "window_days": result.get("window_days"),
        "elapsed_seconds": result.get("elapsed_seconds"),
        "path_generation": result.get("path_generation"),
        "candidate_summary": candidate_summary,
    }


def _extract_path_window(candidate_result: dict[str, Any]) -> object:
    retrieval_context = candidate_result.get("retrieval_context")
    if not isinstance(retrieval_context, dict):
        return None
    return retrieval_context.get("path_window")


def _extract_candidate_ids(candidates: object) -> list[object]:
    if not isinstance(candidates, list):
        return []

    candidate_ids: list[object] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_ids.append(candidate.get("patient_id"))
    return candidate_ids


def _extract_candidate_scores(candidates: object) -> list[dict[str, object]]:
    if not isinstance(candidates, list):
        return []

    candidate_scores: list[dict[str, object]] = []
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        candidate_scores.append(
            {
                "patient_id": candidate.get("patient_id"),
                "candidate_score": candidate.get("candidate_score"),
            }
        )
    return candidate_scores


def main() -> int:
    """Run the full pipeline and log the JSON result."""
    args = parse_args()
    try:
        result = run_similar_user_pipeline(
            args.patient_id,
            pattern=args.pattern,
            config_path=args.config,
            skip_path_build=args.skip_path_build,
            base_date=args.base_date,
            window_days=args.window_days,
        )
    except Exception as exc:
        LOGGER.exception(
            "Similar user pipeline failed: patient_id=%s, config_path=%s",
            args.patient_id,
            args.config,
        )
        return 1

    output = (
        result
        if args.output_level == "full"
        else summarize_pipeline_result(result, output_level=args.output_level)
    )
    LOGGER.info(json.dumps(output, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
