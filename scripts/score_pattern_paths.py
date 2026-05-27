"""Score saved pattern paths.

这个脚本处在“path 生成”和“候选用户聚合”之间：

1. `scripts/build_pattern_paths.py` 或 pipeline 先从 Neo4j 生成并保存某个患者的 paths。
2. 本脚本从本地 JSON 存储读取这些 paths，用对应 pattern 的 scorer 给每条 path 打分。
3. 下游 `scripts/build_similar_user_candidates.py` 会读取这里的评分结果，按配置保留的 path
   去重候选用户，再计算 candidate_score。

它不会重新查 Neo4j 生成 path，也不会直接推荐 task；它只负责“给已保存 path 排序/筛选”。

常用执行方式：

    python scripts/score_pattern_paths.py --source-id 30010096 --pattern patient_game_patient --base-date 2022-05-22

批量评分配置中的 patient 起点模式：

    python scripts/score_pattern_paths.py --source-id 30010096 --patterns-from-config --base-date 2022-05-22

调试单条 path，不保存评分文件：

    python scripts/score_pattern_paths.py --source-id 30010096 --pattern patient_game_patient --base-date 2022-05-22 --path-index 0

对 disease_patient / symptom_patient / unknown_patient 评分时，需要显式提供源节点年龄和学历：

    python scripts/score_pattern_paths.py --source-id AU_DIS_0013 --pattern disease_patient --base-date 2022-05-22 --age 66 --education 本科
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import load_query_settings
from similar_user.data_access.pattern_registry import (
    available_path_pattern_aliases,
    get_path_pattern_spec,
    resolve_path_pattern,
)
from similar_user.domain.graph_schema import PathPattern
from similar_user.services.path_scoring import PathScoringRules, get_path_scorer
from similar_user.utils.logger import get_logger
from similar_user.utils.pattern_storage import PatternResultStore


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
DEFAULT_PATTERN = "patient_game_patient"
DEFAULT_SCORED_OUTPUT_DIR = Path("data/scored_pattern_paths")
SOURCE_DEMOGRAPHIC_PATTERNS = (
    PathPattern.DISEASE_TASKSET_PATIENT,
    PathPattern.SYMPTOM_TASKSET_PATIENT,
    PathPattern.UNKNOWN_TASKSET_PATIENT,
)
LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for scoring saved pattern results."""
    parser = argparse.ArgumentParser(
        description="Score saved pattern paths from local JSON storage."
    )
    parser.add_argument(
        "--source-id",
        required=True,
        help="Source node ID for the selected pattern.",
    )
    parser.add_argument(
        "--pattern",
        default=None,
        choices=available_path_pattern_aliases(),
        help="Path pattern alias used to locate the saved result.",
    )
    parser.add_argument(
        "--patterns-from-config",
        action="store_true",
        help=(
            "Score all patient-source patterns configured in "
            "candidate_ranking.patterns."
        ),
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
        "--age",
        default=None,
        help=(
            "Source age used by disease_patient, symptom_patient, and unknown_patient "
            "scoring."
        ),
    )
    parser.add_argument(
        "--education",
        default=None,
        help=(
            "Source education used by disease_patient, symptom_patient, and "
            "unknown_patient scoring."
        ),
    )
    parser.add_argument(
        "--scored-paths-dir",
        default=str(DEFAULT_SCORED_OUTPUT_DIR),
        help="Directory used to store scored path detail and summary JSON files.",
    )
    parser.add_argument(
        "--base-date",
        required=True,
        help="Path cache base date used to locate saved raw pattern paths.",
    )
    parser.add_argument(
        "--query-family",
        default=None,
        choices=(
            "training_order",
            "date_window",
            "training_order_local_sampling",
            "training_order_age_only",
            "training_order_layer1_age_completion",
            "training_order_layer2_education_exact",
            "training_order_layer3_activity_task_type",
        ),
        help="Path cache query family used to locate saved raw pattern paths.",
    )
    args = parser.parse_args()
    if args.pattern is None and not args.patterns_from_config:
        parser.error("one of --pattern or --patterns-from-config is required")
    if args.pattern is not None and args.patterns_from_config:
        parser.error("--pattern and --patterns-from-config cannot be used together")
    _validate_source_demographic_args(parser, args)
    return args


def score_pattern_paths(
    source_id: str,
    *,
    pattern: str = DEFAULT_PATTERN,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    path_index: int | None = None,
    base_date: str | None = None,
    query_family: str | None = None,
) -> dict[str, object]:
    """Load a saved pattern result and score its domain paths."""
    started_at = time.perf_counter()
    top_k = load_query_settings(config_path).score_pattern_paths.top_k
    LOGGER.debug(
        "Scoring pattern paths: source_id=%s, pattern=%s, path_index=%s, top_k=%s, config_path=%s",
        source_id,
        pattern,
        path_index,
        top_k,
        config_path,
    )
    stored_result = PatternResultStore(config_path).load(
        pattern,
        source_id,
        base_date=base_date,
        query_family=query_family,
    )
    scorer = get_path_scorer(stored_result.pattern)
    domain_paths = stored_result.to_domain_paths()

    if path_index is not None:
        if path_index < 0 or path_index >= len(domain_paths):
            raise IndexError(
                f"path_index {path_index} is out of range for {len(domain_paths)} paths."
            )
        selected = [(path_index, domain_paths[path_index])]
    else:
        selected = list(enumerate(domain_paths))

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
        "source_id": stored_result.source_id,
        "source_parameter": stored_result.source_parameter,
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
    result["cache_context"] = build_scored_cache_context(
        config_path,
        retrieval_context=stored_result.retrieval_context,
        top_k=top_k,
    )
    LOGGER.debug(
        "Scored pattern result: source_id=%s, source_parameter=%s, path_count=%s, scored_path_count=%s",
        stored_result.source_id,
        stored_result.source_parameter,
        result["path_count"],
        result["scored_path_count"],
    )
    LOGGER.info(
        "Completed pattern path scoring: source_id=%s, pattern=%s, path_count=%s, scored_path_count=%s, elapsed_seconds=%s",
        stored_result.source_id,
        stored_result.pattern,
        result["path_count"],
        result["scored_path_count"],
        round(time.perf_counter() - started_at, 3),
    )
    return result


def score_configured_pattern_paths(
    source_id: str,
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    path_index: int | None = None,
    base_date: str | None = None,
    query_family: str | None = None,
) -> list[dict[str, object]]:
    """Score all configured patient-source pattern paths for one source patient."""
    started_at = time.perf_counter()
    query_settings = load_query_settings(config_path)
    ranking_settings = query_settings.candidate_ranking
    top_k = query_settings.score_pattern_paths.top_k
    selected_patterns = tuple(ranking_settings.patterns)
    _validate_patient_source_patterns(selected_patterns)
    LOGGER.info(
        "Starting configured pattern path scoring: source_id=%s, patterns=%s, path_index=%s, top_k=%s, config_path=%s",
        source_id,
        selected_patterns,
        path_index,
        top_k,
        config_path,
    )
    results = [
        score_pattern_paths(
            source_id,
            pattern=pattern,
            config_path=config_path,
            path_index=path_index,
            **_path_cache_kwargs(
                base_date=base_date,
                query_family=query_family,
            ),
        )
        for pattern in selected_patterns
    ]
    LOGGER.info(
        "Completed configured pattern path scoring: source_id=%s, pattern_count=%s, total_path_count=%s, total_scored_path_count=%s, elapsed_seconds=%s",
        source_id,
        len(selected_patterns),
        sum(_extract_int(result.get("path_count")) for result in results),
        sum(_extract_int(result.get("scored_path_count")) for result in results),
        round(time.perf_counter() - started_at, 3),
    )
    return results


def score_and_save_configured_pattern_paths(
    source_id: str,
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    path_index: int | None = None,
    output_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
    base_date: str | None = None,
    query_family: str | None = None,
) -> list[dict[str, object]]:
    """Score configured patient-source pattern paths and persist each result."""
    results = score_configured_pattern_paths(
        source_id,
        config_path=config_path,
        path_index=path_index,
        **_path_cache_kwargs(
            base_date=base_date,
            query_family=query_family,
        ),
    )
    save_scored_pattern_results(results, output_dir=output_dir)
    return results


def save_scored_pattern_result(
    result: dict[str, object],
    output_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
) -> dict[str, Path]:
    """Save full scored details and a compact summary as two JSON files."""
    detail_path, summary_path = get_scored_pattern_output_paths(result, output_dir)
    _write_json_atomic(detail_path, result)
    _write_json_atomic(summary_path, build_scored_pattern_summary(result))
    LOGGER.info(
        "Saved scored pattern result: source_id=%s, pattern=%s, detail_path=%s, summary_path=%s",
        result.get("source_id"),
        result.get("pattern"),
        detail_path,
        summary_path,
    )
    return {"detail": detail_path, "summary": summary_path}


def save_scored_pattern_results(
    results: dict[str, object] | list[dict[str, object]],
    output_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
) -> list[dict[str, Path]]:
    """Save one or more scored pattern results."""
    scored_results = results if isinstance(results, list) else [results]
    return [
        save_scored_pattern_result(scored_result, output_dir=output_dir)
        for scored_result in scored_results
    ]


def get_scored_pattern_output_paths(
    result: dict[str, object],
    output_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
) -> tuple[Path, Path]:
    """Return detail and summary output paths for one scored result."""
    source_id = _normalize_result_string(result.get("source_id"), "source_id")
    pattern = _normalize_result_string(result.get("pattern"), "pattern")
    scored_key = _extract_scored_key(result.get("cache_context"))
    bucket = source_id[:2] or "unknown"
    output_base = Path(output_dir) / scored_key / pattern / bucket
    return (
        output_base / f"{source_id}.detail.json",
        output_base / f"{source_id}.summary.json",
    )


def build_scored_pattern_summary(result: dict[str, object]) -> dict[str, object]:
    """Build a compact scored result summary for quick score inspection."""
    summary_scores = []
    raw_scores = result.get("scores")
    scores = raw_scores if isinstance(raw_scores, list) else []
    for rank, item in enumerate(scores, start=1):
        if not isinstance(item, dict):
            continue
        score = item.get("score")
        score_data = score if isinstance(score, dict) else {}
        row = _extract_path_row(item.get("path"))
        summary_scores.append(
            {
                "rank": rank,
                "path_index": item.get("path_index"),
                "total_score": score_data.get("total_score"),
                "candidate_id": _extract_node_id(row, "p2"),
                "game_id": _extract_node_id(row, "g"),
                "game_name": _extract_node_name(row, "g"),
                "score": score_data,
            }
        )

    return {
        "source_id": result.get("source_id"),
        "source_parameter": result.get("source_parameter"),
        "pattern": result.get("pattern"),
        "path_count": result.get("path_count"),
        "scored_path_count": result.get("scored_path_count"),
        "retrieval_context": result.get("retrieval_context"),
        "cache_context": result.get("cache_context"),
        "scores": summary_scores,
    }


def build_scored_key(path_key: str, top_k: int | None) -> str:
    """Build a cache key for scored pattern path results."""
    top_k_part = str(top_k) if top_k is not None else "all"
    return f"{path_key}_scoretopk_{top_k_part}"


def build_scored_cache_context(
    config_path: str | Path,
    *,
    retrieval_context: dict[str, object] | None,
    top_k: int | None,
) -> dict[str, object]:
    """Build cache metadata for scored pattern path results."""
    path_cache_context = (
        retrieval_context.get("cache_context")
        if isinstance(retrieval_context, dict)
        else None
    )
    if not isinstance(path_cache_context, dict):
        raise ValueError("Scored path cache requires retrieval_context.cache_context.")
    path_key = path_cache_context.get("path_key")
    if not isinstance(path_key, str) or not path_key.strip():
        raise ValueError("Scored path cache requires cache_context.path_key.")
    path_key = path_key.strip()
    return {
        "cache_type": "scored_pattern_paths",
        "path_key": path_key,
        "scored_key": build_scored_key(path_key, top_k),
        "score_top_k": top_k,
    }


def validate_scored_cache_context(
    scored_result: dict[str, object],
    *,
    expected_scored_key: str,
) -> None:
    """Raise if scored path metadata does not match the expected scored key."""
    cache_context = scored_result.get("cache_context")
    if not isinstance(cache_context, dict):
        raise ValueError(
            "Saved scored pattern result is missing cache_context: "
            f"expected_scored_key={expected_scored_key}."
        )
    actual_scored_key = cache_context.get("scored_key")
    if actual_scored_key != expected_scored_key:
        raise ValueError(
            "Saved scored pattern result cache key mismatch: "
            f"expected={expected_scored_key}, actual={actual_scored_key}."
        )


def _extract_scored_key(cache_context: object) -> str:
    if not isinstance(cache_context, dict):
        raise ValueError("scored result cache_context must be present before saving.")
    scored_key = cache_context.get("scored_key")
    if not isinstance(scored_key, str) or not scored_key.strip():
        raise ValueError("scored result cache_context.scored_key must be non-empty.")
    return scored_key.strip()


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


def _extract_path_row(path: object) -> dict[str, object]:
    if not isinstance(path, dict):
        return {}
    row = path.get("row")
    return row if isinstance(row, dict) else {}


def _extract_node_id(row: dict[str, object], key: str) -> object:
    node = row.get(key)
    if isinstance(node, dict):
        return node.get("id")
    return None


def _extract_node_name(row: dict[str, object], key: str) -> object:
    node = row.get(key)
    if isinstance(node, dict):
        return node.get("name")
    return None


def _normalize_result_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _extract_int(value: object) -> int:
    return value if isinstance(value, int) else 0


def _requires_source_demographics(pattern: PathPattern | str) -> bool:
    return resolve_path_pattern(pattern) in SOURCE_DEMOGRAPHIC_PATTERNS


def _validate_source_demographic_args(
    parser: argparse.ArgumentParser,
    args: argparse.Namespace,
) -> None:
    if args.patterns_from_config:
        return
    pattern = resolve_path_pattern(args.pattern)
    if not _requires_source_demographics(pattern):
        return
    missing = [
        option
        for option, value in (
            ("--age", args.age),
            ("--education", args.education),
        )
        if not isinstance(value, str) or not value.strip()
    ]
    if missing:
        aliases = "disease_patient, symptom_patient, unknown_patient"
        parser.error(
            f"{', '.join(missing)} must be provided for {aliases} scoring patterns."
        )

    if PathScoringRules._parse_int(args.age) is None:
        parser.error("--age must be a numeric age value.")

    supported_education_values = _supported_cli_education_values()
    education = args.education.strip()
    if education not in supported_education_values:
        supported = ", ".join(supported_education_values)
        parser.error(f"--education must be one of: {supported}")


def _supported_cli_education_values() -> tuple[str, ...]:
    return tuple(
        sorted(
            set(PathScoringRules.EDUCATION_RANKS)
            | set(PathScoringRules.EDUCATION_NORMALIZATION)
        )
    )


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


def _write_json_atomic(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_file.write(serialized)
        temp_path = Path(temp_file.name)

    os.replace(temp_path, path)


def main() -> int:
    """Score saved pattern paths and log JSON output."""
    args = parse_args()
    try:
        cache_args = _build_path_cache_args(args)
        if getattr(args, "patterns_from_config", False) is True:
            result = score_configured_pattern_paths(
                args.source_id,
                config_path=args.config,
                path_index=args.path_index,
                **cache_args,
            )
        else:
            result = score_pattern_paths(
                args.source_id,
                pattern=args.pattern,
                config_path=args.config,
                path_index=args.path_index,
                **cache_args,
            )
        if args.path_index is None:
            save_scored_pattern_results(
                result,
                output_dir=args.scored_paths_dir,
            )
    except Exception as exc:
        LOGGER.exception("Score pattern paths failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


def _build_path_cache_args(args: argparse.Namespace) -> dict[str, object]:
    """Return optional path-cache lookup arguments from parsed CLI args."""
    cache_args: dict[str, object] = {}
    base_date = getattr(args, "base_date", None)
    if isinstance(base_date, str) and base_date.strip():
        cache_args["base_date"] = base_date.strip()
    query_family = getattr(args, "query_family", None)
    if isinstance(query_family, str) and query_family.strip():
        cache_args["query_family"] = query_family.strip()
    return cache_args


def _path_cache_kwargs(
    *,
    base_date: str | None,
    query_family: str | None,
) -> dict[str, object]:
    kwargs: dict[str, object] = {}
    if base_date is not None:
        kwargs["base_date"] = base_date
    if query_family is not None:
        kwargs["query_family"] = query_family
    return kwargs


if __name__ == "__main__":
    raise SystemExit(main())
