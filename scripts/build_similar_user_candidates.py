"""Build similar-user candidates from scored paths.

这个脚本处在“path 打分”和“训练任务推荐”之间：

1. `scripts/score_pattern_paths.py` 会保存各模式的 scored paths。
2. 本脚本读取已保存的 scored detail，把 path 中出现的 `p2` 患者去重成候选相似用户。
3. 对每个候选用户继续查询 Neo4j 中的历史画像/游戏表现，计算 candidate_score。
4. 下游推荐任务流程会使用这里输出的候选用户历史数据。

它不会生成 path，也不会直接预测 task；它只负责“从已评分 path 聚合并排序候选用户”。

常用执行方式：

    python scripts/build_similar_user_candidates.py 40

默认从 `config/settings.yaml` 的 `candidate_ranking.patterns` 读取多模式列表。
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

from config.settings import load_query_settings
from similar_user.data_access.kg_repository import KgRepository
from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.data_access.pattern_registry import resolve_path_pattern
from similar_user.services.similarity.candidate_service import SimilarUserCandidateService
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger

from scripts.score_pattern_paths import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_SCORED_OUTPUT_DIR,
)


LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for candidate aggregation."""
    parser = argparse.ArgumentParser(
        description="Build ranked similar-user candidates from top-k scored paths."
    )
    parser.add_argument("patient_id", help="Patient identifier used in the stored file.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--scored-paths-dir",
        default=str(DEFAULT_SCORED_OUTPUT_DIR),
        help="Directory containing saved scored detail JSON files.",
    )
    return parser.parse_args()


def build_similar_user_candidates(
    patient_id: str,
    *,
    config_path: str | Path | None = None,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
) -> dict[str, Any]:
    """Aggregate ranked candidate users from top-k scored paths."""
    resolved_config_path = DEFAULT_CONFIG_PATH if config_path is None else config_path
    ranking_settings = load_query_settings(resolved_config_path).candidate_ranking
    selected_patterns = tuple(ranking_settings.patterns)
    LOGGER.debug(
        "Building similar-user candidates from saved scored paths: patient_id=%s, patterns=%s, candidate_top_k=%s, config_path=%s, scored_paths_dir=%s",
        patient_id,
        selected_patterns,
        ranking_settings.candidate_top_k,
        resolved_config_path,
        scored_paths_dir,
    )

    with Neo4jClient.from_config(resolved_config_path) as client:
        user_service = UserService(
            kg_repository=KgRepository(
                client=client,
                config_path=Path(resolved_config_path),
            )
        )
        candidate_service = SimilarUserCandidateService(user_service=user_service)
        scored_results = [
            load_saved_scored_pattern_result(
                patient_id,
                pattern=item,
                scored_paths_dir=scored_paths_dir,
            )
            for item in selected_patterns
        ]
        result = candidate_service.aggregate_candidates_from_multiple_scored_results(
            scored_results,
            candidate_top_k=ranking_settings.candidate_top_k,
        )
    LOGGER.debug(
        "Built similar-user candidates from scored paths: patient_id=%s, candidate_count=%s, scored_path_count=%s",
        patient_id,
        result.get("candidate_count"),
        result.get("scored_path_count"),
    )
    return result


def load_saved_scored_pattern_result(
    source_id: str,
    *,
    pattern: str,
    scored_paths_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
) -> dict[str, Any]:
    """Load one saved scored detail file produced by score_pattern_paths.py."""
    normalized_source_id = _normalize_required_string(source_id, "source_id")
    normalized_pattern = resolve_path_pattern(pattern).value
    detail_path = (
        Path(scored_paths_dir)
        / normalized_pattern
        / (normalized_source_id[:2] or "unknown")
        / f"{normalized_source_id}.detail.json"
    )
    if not detail_path.exists():
        raise FileNotFoundError(
            f"Saved scored detail not found for pattern {normalized_pattern}: {detail_path}"
        )
    with detail_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"Saved scored detail must contain a JSON object: {detail_path}")
    return data


def _normalize_required_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def main() -> int:
    """Build similar-user candidates and log the JSON result."""
    args = parse_args()
    try:
        result = build_similar_user_candidates(
            args.patient_id,
            config_path=args.config,
            scored_paths_dir=args.scored_paths_dir,
        )
    except Exception as exc:
        LOGGER.exception("Build similar user candidates from scored paths failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
