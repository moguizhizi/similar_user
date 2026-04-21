"""Score saved patient pattern paths.

这个脚本处在“path 生成”和“候选用户聚合”之间：

1. `scripts/build_patient_pattern_paths.py` 或 pipeline 先从 Neo4j 生成并保存某个患者的 paths。
2. 本脚本从本地 JSON 存储读取这些 paths，用 `PathScorer` 给每条 path 打分。
3. 下游 `scripts/build_similar_user_candidates.py` 会读取这里的评分结果，按 top-k path
   去重候选用户，再计算 candidate_score。

它不会重新查 Neo4j 生成 path，也不会直接推荐 task；它只负责“给已保存 path 排序/筛选”。

常用执行方式：

    python scripts/score_patient_pattern_paths.py 40 --top-k 50

调试单条 path：

    python scripts/score_patient_pattern_paths.py 40 --path-index 0
"""

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
from similar_user.services.path_scoring import PathScorer
from similar_user.utils.logger import get_logger
from similar_user.utils.pattern_storage import PatternResultStore


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for scoring saved patient results."""
    parser = argparse.ArgumentParser(
        description="Score saved patient pattern paths from local JSON storage."
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
        "--path-index",
        type=int,
        default=None,
        help="Only score one path at the given zero-based index.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Return the top-k scored paths ordered by total_score descending.",
    )
    return parser.parse_args()


def score_patient_pattern_paths(
    patient_id: str,
    *,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    path_index: int | None = None,
    top_k: int | None = None,
) -> dict[str, object]:
    """Load a saved patient result and score its domain paths."""
    LOGGER.debug(
        "Scoring patient pattern paths: patient_id=%s, pattern=%s, path_index=%s, top_k=%s, config_path=%s",
        patient_id,
        pattern,
        path_index,
        top_k,
        config_path,
    )
    stored_result = PatternResultStore(config_path).load(pattern, patient_id)
    domain_paths = stored_result.to_domain_paths()

    if top_k is not None and top_k <= 0:
        raise ValueError(f"top_k must be greater than 0, got {top_k}.")

    if path_index is not None:
        if path_index < 0 or path_index >= len(domain_paths):
            raise IndexError(
                f"path_index {path_index} is out of range for {len(domain_paths)} paths."
            )
        selected = [(path_index, domain_paths[path_index])]
    else:
        selected = list(enumerate(domain_paths))

    scorer = PathScorer()
    scored_paths = [
        {
            "path_index": index,
            "score": scorer.score(path).to_dict(),
            "path": stored_result.paths[index],
        }
        for index, path in selected
    ]
    if path_index is None:
        scored_paths.sort(
            key=lambda item: float(item["score"]["total_score"]),  # type: ignore[index]
            reverse=True,
        )
        if top_k is not None:
            scored_paths = scored_paths[:top_k]

    retrieval_context = stored_result.retrieval_context
    base_date = None
    path_window = None
    legacy_split_training_date = None
    if isinstance(retrieval_context, dict):
        raw_base_date = retrieval_context.get("base_date")
        if isinstance(raw_base_date, str) and raw_base_date.strip():
            base_date = raw_base_date.strip()
        raw_path_window = retrieval_context.get("path_window")
        if isinstance(raw_path_window, dict):
            path_window = raw_path_window
        raw_split_training_date = retrieval_context.get("split_training_date")
        if isinstance(raw_split_training_date, str) and raw_split_training_date.strip():
            legacy_split_training_date = raw_split_training_date.strip()

    result = {
        "patient_id": stored_result.patient_id,
        "pattern": stored_result.pattern,
        "path_count": len(domain_paths),
        "scored_path_count": len(scored_paths),
        "retrieval_context": {
            "base_date": base_date,
            "path_window": path_window,
            "score_end_date": _extract_score_end_date(
                path_window,
                legacy_split_training_date,
            ),
            "path_scope": _build_path_scope(path_window, legacy_split_training_date),
        },
        "scores": scored_paths,
    }
    LOGGER.debug(
        "Scored patient pattern result: patient_id=%s, path_count=%s, scored_path_count=%s",
        stored_result.patient_id,
        result["path_count"],
        result["scored_path_count"],
    )
    return result


def _extract_score_end_date(
    path_window: dict[str, object] | None,
    legacy_split_training_date: str | None,
) -> str | None:
    """Extract the end date used by downstream candidate scoring."""
    if isinstance(path_window, dict):
        raw_end_date = path_window.get("end_date")
        if isinstance(raw_end_date, str) and raw_end_date.strip():
            return raw_end_date.strip()
    return legacy_split_training_date


def _build_path_scope(
    path_window: dict[str, object] | None,
    legacy_split_training_date: str | None,
) -> str:
    """Build a concise human-readable scope for scored paths."""
    if isinstance(path_window, dict):
        start_date = path_window.get("start_date")
        end_date = path_window.get("end_date")
        if start_date is not None and end_date is not None:
            return (
                "当前评分结果中的 paths 来自训练日期 "
                f">= {start_date} 且 < {end_date} 的检索集合"
            )
    if legacy_split_training_date is not None:
        return (
            "当前评分结果中的 paths 来自历史 split 语义下训练日期 "
            f"< {legacy_split_training_date} 的检索集合"
        )
    return "当前评分结果中的 paths 来自已保存的检索集合"


def main() -> int:
    """Score saved patient pattern paths and log JSON output."""
    args = parse_args()
    try:
        result = score_patient_pattern_paths(
            args.patient_id,
            pattern=args.pattern,
            config_path=args.config,
            path_index=args.path_index,
            top_k=args.top_k,
        )
    except Exception as exc:
        LOGGER.exception("Score patient pattern paths failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
