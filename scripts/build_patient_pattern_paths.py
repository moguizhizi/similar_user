"""Build and persist patient pattern paths from Neo4j.

这个脚本是相似用户流程的第一步：

1. 按 `patient_id`、日期窗口、路径模式和查询族从 Neo4j 查询 paths。
2. 将查询结果组装为带 `retrieval_context` 的离线结果。
3. 把结果保存到配置中的 pattern path 存储目录，供 path 打分和候选用户构建脚本继续使用。

它只负责“构建并保存 paths”，不会给 path 打分，也不会聚合候选相似用户。

外层参数只表达业务选择：

- `--pattern` 选择路径模式，只接受公开别名。默认 `patient_game_patient`。
- `--query-family` 选择同一路径模式下的查询语义族。默认 `training_order`。
  `training_order` 会要求 s1/s2 满足训练日期顺序；`date_window` 只按 s1 的训练日期窗口取路径。
- `--base-date` 是右开窗口的结束日期，`--window-days` 决定向前回看多少天。

常用执行方式：

    python scripts/build_patient_pattern_paths.py 30010096 \
        --base-date 2022-05-22 \
        --window-days 14 \
        --pattern patient_game_patient \
        --query-family training_order
"""

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
from similar_user.data_access.pattern_registry import available_path_pattern_aliases
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger
from similar_user.utils.pattern_storage import save_pattern_result


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
DEFAULT_PATTERN = "patient_game_patient"
DEFAULT_QUERY_FAMILY = "training_order"
LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for building one patient's offline pattern paths."""
    parser = argparse.ArgumentParser(
        description="Build and persist patient fixed-pattern paths."
    )
    parser.add_argument("patient_id", help="Patient ID used as the start node.")
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
        "--window-days",
        type=int,
        required=True,
        help="Number of days before base_date included in the left-closed window.",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        choices=available_path_pattern_aliases(),
        help=(
            "Path pattern alias. Supported aliases are shown in the choices list."
        ),
    )
    parser.add_argument(
        "--query-family",
        default=DEFAULT_QUERY_FAMILY,
        choices=("training_order", "date_window"),
        help=(
            "Query family for both statistics and randomized paths. "
            "training_order enforces s1/s2 training-date order; "
            "date_window only filters by the s1 date window."
        ),
    )
    return parser.parse_args()


def run_patient_pattern_path_flow(
    patient_id: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    *,
    base_date: str,
    window_days: int,
    pattern: str = DEFAULT_PATTERN,
    query_family: str = DEFAULT_QUERY_FAMILY,
) -> dict[str, object]:
    """Build one patient's pattern paths from Neo4j and persist the result."""
    LOGGER.info(
        "Starting patient pattern path build: patient_id=%s, pattern=%s, query_family=%s, base_date=%s, window_days=%s, config_path=%s",
        patient_id,
        pattern,
        query_family,
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
            pattern=pattern,
            query_family=query_family,
        )
        output_path = save_pattern_result(result, repository.config_path)
        retrieval_context = result.get("retrieval_context") or {}
        LOGGER.info(
            "Completed patient pattern path build: patient_id=%s, path_window=%s, path_count=%s, output_path=%s",
            patient_id,
            retrieval_context.get("path_window"),
            len(retrieval_context.get("paths", [])),
            output_path,
        )
        return result


def main() -> int:
    """CLI entrypoint for building and saving one patient's pattern paths."""
    args = parse_args()
    try:
        run_patient_pattern_path_flow(
            args.patient_id,
            config_path=args.config,
            base_date=args.base_date,
            window_days=args.window_days,
            pattern=getattr(args, "pattern", DEFAULT_PATTERN),
            query_family=getattr(args, "query_family", DEFAULT_QUERY_FAMILY),
        )
    except Exception as exc:
        LOGGER.exception(
            "Patient pattern path build failed: patient_id=%s, config_path=%s",
            args.patient_id,
            args.config,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
