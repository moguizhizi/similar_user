"""Build and persist pattern paths from Neo4j.

这个脚本是路径生成流程的统一入口：

1. 按 `source_id`、配置中的日期窗口和路径模式从 Neo4j 查询 paths。
2. 将查询结果组装为带 `retrieval_context` 的离线结果。
3. 把结果保存到配置中的 pattern path 存储目录，供后续流程继续使用。

它只负责“构建并保存 paths”，不会给 path 打分，也不会聚合候选结果。

外层参数只表达业务选择：

- `--source-id` 是当前模式的起点 ID，例如 patient 模式下是 patient_id，
  disease_patient 模式下是 disease_id。
- `--pattern` 选择路径模式，只接受公开别名。
- `--patterns-from-config` 从 YAML 的 `candidate_ranking.patterns` 读取多个 patient 起点模式并依次构建。
- `--query-family` 只适用于带 statistics 的 patient 系列模式。默认 `training_order`。
  `training_order` 会要求 s1/s2 满足训练日期顺序；`date_window` 只按 s1 的训练日期窗口取路径。
- `--base-date` 是右开窗口的结束日期，向前回看的天数来自
  `query.patient_path.window_days`。

常用执行方式：

    python scripts/build_pattern_paths.py \
        --source-id 30010096 \
        --pattern patient_game_patient \
        --base-date 2022-05-22 \
        --query-family training_order

    python scripts/build_pattern_paths.py \
        --source-id AU_DIS_0013 \
        --pattern disease_patient \
        --base-date 2022-05-22

    python scripts/build_pattern_paths.py \
        --source-id 30010096 \
        --patterns-from-config \
        --base-date 2022-05-22
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import load_query_settings
from similar_user.data_access.kg_repository import KgRepository
from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.data_access.pattern_registry import (
    PatternQueryMode,
    available_path_pattern_aliases,
    get_path_pattern_spec,
    resolve_path_pattern,
)
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger
from similar_user.utils.pattern_storage import save_pattern_result


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
DEFAULT_PATTERN = "patient_game_patient"
DEFAULT_QUERY_FAMILY = "training_order"
LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for building one source's offline pattern paths."""
    parser = argparse.ArgumentParser(
        description="Build and persist fixed-pattern paths."
    )
    parser.add_argument(
        "--source-id",
        required=True,
        help="Source node ID for the selected pattern.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="YAML config path for Neo4j and query/output settings.",
    )
    parser.add_argument(
        "--base-date",
        required=True,
        help="Exclusive end date of the path window, for example 2022-05-22.",
    )
    parser.add_argument(
        "--pattern",
        default=None,
        choices=available_path_pattern_aliases(),
        help=(
            "Path pattern alias. Supported aliases are shown in the choices list."
        ),
    )
    parser.add_argument(
        "--patterns-from-config",
        action="store_true",
        help=(
            "Build all patient-source patterns configured in "
            "candidate_ranking.patterns."
        ),
    )
    parser.add_argument(
        "--query-family",
        default=None,
        choices=("training_order", "date_window"),
        help=(
            "Query family for paired-statistics patterns. Defaults to training_order "
            "for patient-series patterns and is not allowed for direct patterns. "
            "training_order enforces s1/s2 training-date order; "
            "date_window only filters by the s1 date window."
        ),
    )
    args = parser.parse_args()
    if args.pattern is None and not args.patterns_from_config:
        parser.error("one of --pattern or --patterns-from-config is required")
    if args.pattern is not None and args.patterns_from_config:
        parser.error("--pattern and --patterns-from-config cannot be used together")
    return args


def run_pattern_path_flow(
    source_id: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    base_date: str,
    pattern: str = DEFAULT_PATTERN,
    query_family: str | None = None,
) -> dict[str, object]:
    """Build one source's pattern paths from Neo4j and persist the result."""
    started_at = time.perf_counter()
    resolved_window_days = _resolve_patient_path_window_days(config_path)
    effective_query_family = _resolve_effective_query_family(pattern, query_family)
    LOGGER.info(
        "Starting pattern path build: source_id=%s, pattern=%s, query_family=%s, base_date=%s, window_days=%s, config_path=%s",
        source_id,
        pattern,
        effective_query_family,
        base_date,
        resolved_window_days,
        config_path,
    )
    with Neo4jClient.from_config(config_path) as client:
        repository = KgRepository(client=client, config_path=Path(config_path))
        service = UserService(kg_repository=repository)
        result = service.get_pattern_paths(
            source_id,
            base_date=base_date,
            window_days=resolved_window_days,
            pattern=pattern,
            query_family=effective_query_family,
        )
        output_path = save_pattern_result(result, repository.config_path)
        retrieval_context = result.get("retrieval_context") or {}
        path_count = len(retrieval_context.get("paths", []))
        LOGGER.info(
            "Completed pattern path build: source_id=%s, pattern=%s, query_family=%s, path_window=%s, path_count=%s, output_path=%s, elapsed_seconds=%s",
            source_id,
            pattern,
            effective_query_family,
            retrieval_context.get("path_window"),
            path_count,
            output_path,
            round(time.perf_counter() - started_at, 3),
        )
        return result


def run_configured_pattern_path_flows(
    source_id: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    base_date: str,
    query_family: str | None = None,
) -> list[dict[str, object]]:
    """Build all configured patient-source pattern paths for one source patient."""
    started_at = time.perf_counter()
    query_settings = load_query_settings(config_path)
    ranking_settings = query_settings.candidate_ranking
    resolved_window_days = _resolve_patient_path_window_days(config_path)
    selected_patterns = tuple(ranking_settings.patterns)
    _validate_patient_source_patterns(selected_patterns)
    effective_query_family = query_family or DEFAULT_QUERY_FAMILY
    LOGGER.info(
        "Starting configured pattern path build: source_id=%s, patterns=%s, query_family=%s, base_date=%s, window_days=%s, config_path=%s",
        source_id,
        selected_patterns,
        effective_query_family,
        base_date,
        resolved_window_days,
        config_path,
    )
    results = [
        run_pattern_path_flow(
            source_id,
            config_path=config_path,
            base_date=base_date,
            pattern=pattern,
            query_family=effective_query_family,
        )
        for pattern in selected_patterns
    ]
    LOGGER.info(
        "Completed configured pattern path build: source_id=%s, pattern_count=%s, total_path_count=%s, elapsed_seconds=%s",
        source_id,
        len(selected_patterns),
        sum(_extract_path_count(result) for result in results),
        round(time.perf_counter() - started_at, 3),
    )
    return results


def _validate_patient_source_patterns(patterns: tuple[str, ...]) -> None:
    """Ensure configured batch patterns can share one patient_id source."""
    invalid_patterns = []
    for pattern in patterns:
        spec = get_path_pattern_spec(resolve_path_pattern(pattern))
        if spec.source_parameter != "patient_id":
            invalid_patterns.append(pattern)
    if invalid_patterns:
        invalid = ", ".join(invalid_patterns)
        raise ValueError(
            "patterns-from-config only supports patient-source patterns; "
            f"invalid patterns: {invalid}"
        )


def _extract_path_count(result: dict[str, object]) -> int:
    retrieval_context = result.get("retrieval_context")
    if not isinstance(retrieval_context, dict):
        return 0
    paths = retrieval_context.get("paths")
    return len(paths) if isinstance(paths, list) else 0


def _resolve_effective_query_family(
    pattern: str,
    query_family: str | None,
) -> str | None:
    """Return the query family that will be used for logging and service calls."""
    spec = get_path_pattern_spec(resolve_path_pattern(pattern))
    if spec.query_mode == PatternQueryMode.PAIRED_STATISTICS and query_family is None:
        return DEFAULT_QUERY_FAMILY
    return query_family


def _resolve_patient_path_window_days(
    config_path: str | Path,
) -> int:
    """Return patient path window-days from args or YAML config."""
    return load_query_settings(config_path).patient_path.window_days


def main() -> int:
    """CLI entrypoint for building and saving one source's pattern paths."""
    args = parse_args()
    try:
        if getattr(args, "patterns_from_config", False) is True:
            run_configured_pattern_path_flows(
                args.source_id,
                config_path=args.config,
                base_date=args.base_date,
                query_family=getattr(args, "query_family", None),
            )
        else:
            run_pattern_path_flow(
                args.source_id,
                config_path=args.config,
                base_date=args.base_date,
                pattern=getattr(args, "pattern", DEFAULT_PATTERN),
                query_family=getattr(args, "query_family", None),
            )
    except Exception as exc:
        LOGGER.exception(
            "Pattern path build failed: source_id=%s, config_path=%s",
            args.source_id,
            args.config,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
