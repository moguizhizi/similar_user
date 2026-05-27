"""Analyze evaluation-grid outputs and write a compact report."""

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

from similar_user.utils.logger import get_logger


LOGGER = get_logger(__name__)
DEFAULT_REPORT_JSON = "analysis_report.json"
DEFAULT_REPORT_MARKDOWN = "analysis_report.md"
METRIC_FIELDS = (
    "avg_score_delta",
    "avg_kg_score",
    "avg_csv_score",
    "score_evaluated_count",
    "micro_recall",
    "micro_f1",
    "task_hit_rate",
    "micro_precision",
    "macro_recall",
    "macro_f1",
    "avg_elapsed_seconds",
)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Analyze one data/evaluation_grid/<stage> directory."
    )
    parser.add_argument(
        "--grid-dir",
        required=True,
        help="Stage output directory, e.g. data/evaluation_grid/coarse-100-users.",
    )
    parser.add_argument(
        "--json-file",
        default=DEFAULT_REPORT_JSON,
        help="Analysis JSON filename under grid-dir.",
    )
    parser.add_argument(
        "--markdown-file",
        default=DEFAULT_REPORT_MARKDOWN,
        help="Analysis Markdown filename under grid-dir.",
    )
    return parser.parse_args()


def analyze_and_write_evaluation_grid_report(
    grid_dir: str | Path,
    *,
    json_file: str = DEFAULT_REPORT_JSON,
    markdown_file: str = DEFAULT_REPORT_MARKDOWN,
) -> dict[str, Path]:
    """Analyze one grid directory and write JSON plus Markdown reports."""
    grid_path = Path(grid_dir)
    analysis = analyze_evaluation_grid(grid_path)
    json_path = grid_path / json_file
    markdown_path = grid_path / markdown_file
    json_path.write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    markdown_path.write_text(
        build_markdown_report(analysis),
        encoding="utf-8",
    )
    return {"json": json_path, "markdown": markdown_path}


def analyze_evaluation_grid(grid_dir: str | Path) -> dict[str, Any]:
    """Build deterministic analysis from leaderboard and per-run summaries."""
    grid_path = Path(grid_dir)
    leaderboard_path = grid_path / "leaderboard.json"
    grid_summary_path = grid_path / "grid_summary.json"
    leaderboard = read_json_array(leaderboard_path)
    grid_summary = read_json_object_if_exists(grid_summary_path)
    if not leaderboard:
        return {
            "grid_dir": str(grid_path),
            "leaderboard_path": str(leaderboard_path),
            "grid_summary_path": str(grid_summary_path),
            "status": "no_leaderboard_rows",
            "recommendation": "没有可分析的 leaderboard 行，先确认实验是否成功生成 summary。",
        }

    best = leaderboard[0]
    second_best = leaderboard[1] if len(leaderboard) > 1 else None
    baseline = find_baseline_row(leaderboard)
    best_summary = read_json_object_if_exists(best.get("summary_path"))
    baseline_summary = (
        read_json_object_if_exists(baseline.get("summary_path")) if baseline else {}
    )
    metric_comparison = build_metric_comparison(best, baseline)
    second_best_metric_comparison = build_metric_comparison_to_reference(
        second_best or {},
        baseline,
        reference_label="baseline",
    )
    parameter_diff = build_parameter_diff(
        baseline.get("overrides") if baseline else {},
        best.get("overrides"),
    )
    second_best_parameter_diff = build_parameter_diff_to_reference(
        baseline.get("overrides") if baseline else {},
        second_best.get("overrides") if second_best else {},
        reference_label="baseline",
    )
    warnings = build_warnings(leaderboard, best_summary, grid_summary)
    recommendation = build_recommendation(
        best,
        baseline,
        metric_comparison,
        warnings,
    )

    return {
        "grid_dir": str(grid_path),
        "leaderboard_path": str(leaderboard_path),
        "grid_summary_path": str(grid_summary_path),
        "status": "ok",
        "rank_by": best.get("rank_metric"),
        "best_experiment": compact_experiment_row(best),
        "second_best_experiment": compact_experiment_row(second_best)
        if second_best
        else None,
        "baseline_experiment": compact_experiment_row(baseline) if baseline else None,
        "metric_comparison": metric_comparison,
        "second_best_metric_comparison": second_best_metric_comparison,
        "parameter_diff": parameter_diff,
        "second_best_parameter_diff": second_best_parameter_diff,
        "warnings": warnings,
        "recommendation": recommendation,
        "best_summary": pick_summary_fields(best_summary),
        "baseline_summary": pick_summary_fields(baseline_summary),
    }


def read_json_array(path: str | Path) -> list[dict[str, Any]]:
    """Read a JSON list of objects."""
    resolved_path = Path(path)
    with resolved_path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    if not isinstance(value, list):
        raise ValueError(f"JSON file must contain a list: {resolved_path}")
    return [item for item in value if isinstance(item, dict)]


def read_json_object_if_exists(path: object) -> dict[str, Any]:
    """Read a JSON object when the path exists; otherwise return an empty dict."""
    if not isinstance(path, (str, Path)):
        return {}
    resolved_path = Path(path)
    if not resolved_path.exists():
        return {}
    with resolved_path.open("r", encoding="utf-8") as file:
        value = json.load(file)
    return value if isinstance(value, dict) else {}


def find_baseline_row(leaderboard: list[dict[str, Any]]) -> dict[str, Any] | None:
    """Return the baseline row, preferring names that contain baseline."""
    for row in leaderboard:
        name = str(row.get("name") or "").lower()
        if "baseline" in name:
            return row
    return None


def build_metric_comparison(
    best: dict[str, Any],
    baseline: dict[str, Any] | None,
) -> dict[str, Any]:
    """Compare best metrics against baseline metrics."""
    return build_metric_comparison_to_reference(
        best,
        baseline,
        reference_label="baseline",
    )


def build_metric_comparison_to_reference(
    best: dict[str, Any],
    reference: dict[str, Any] | None,
    *,
    reference_label: str,
) -> dict[str, Any]:
    """Compare best metrics against a named reference experiment."""
    comparison: dict[str, Any] = {}
    for field_name in METRIC_FIELDS:
        best_value = numeric_metric(best.get(field_name))
        reference_value = numeric_metric(reference.get(field_name)) if reference else 0.0
        comparison[field_name] = {
            "best": best_value,
            reference_label: reference_value if reference else None,
            "delta": round(best_value - reference_value, 4) if reference else None,
            "relative_delta": round(
                (best_value - reference_value) / reference_value,
                4,
            )
            if reference and reference_value
            else None,
        }
    return comparison


def build_parameter_diff(
    baseline_overrides: object,
    best_overrides: object,
) -> dict[str, Any]:
    """Compare baseline and best override dictionaries."""
    return build_parameter_diff_to_reference(
        baseline_overrides,
        best_overrides,
        reference_label="baseline",
    )


def build_parameter_diff_to_reference(
    reference_overrides: object,
    best_overrides: object,
    *,
    reference_label: str,
) -> dict[str, Any]:
    """Compare a reference override dictionary with the best override dictionary."""
    reference = reference_overrides if isinstance(reference_overrides, dict) else {}
    best = best_overrides if isinstance(best_overrides, dict) else {}
    diff: dict[str, Any] = {}
    for key in sorted(set(reference) | set(best)):
        reference_value = reference.get(key)
        best_value = best.get(key)
        if reference_value == best_value:
            continue
        diff[key] = {
            reference_label: reference_value,
            "best": best_value,
        }
    return diff


def build_warnings(
    leaderboard: list[dict[str, Any]],
    best_summary: dict[str, Any],
    grid_summary: dict[str, Any],
) -> list[str]:
    """Build lightweight warnings from execution and coverage metrics."""
    warnings: list[str] = []
    failed_count = int(numeric_metric(grid_summary.get("failed_count")))
    if failed_count:
        warnings.append(f"grid 有 {failed_count} 组实验失败。")
    if int(numeric_metric(best_summary.get("failed_count"))):
        warnings.append("最优实验内部存在 failed_count，建议先查看 details。")
    actual_missing_rate = numeric_metric(
        best_summary.get("candidate_training_tasks_actual_missing_rate")
    )
    if actual_missing_rate > 0:
        warnings.append(
            "最优实验真实任务存在候选池缺失，candidate_training_tasks_actual_missing_rate="
            f"{round(actual_missing_rate, 4)}。"
        )
    if len(leaderboard) < 2:
        warnings.append("leaderboard 少于 2 组实验，参数对比依据较弱。")
    return warnings


def build_recommendation(
    best: dict[str, Any],
    baseline: dict[str, Any] | None,
    metric_comparison: dict[str, Any],
    warnings: list[str],
) -> str:
    """Build a concise deterministic recommendation."""
    if baseline is None:
        return "未找到 baseline 实验，建议补充 baseline_best 后再比较。"
    if best.get("name") == baseline.get("name"):
        return "当前 baseline 已是排行榜第一，可暂不调整 baseline。"
    rank_metric = str(best.get("rank_metric") or "")
    if rank_metric in {"avg_score_delta", "avg_kg_score", "avg_csv_score"}:
        score_delta = metric_comparison.get("avg_score_delta", {}).get("delta")
        if isinstance(score_delta, (int, float)) and score_delta > 0:
            return (
                f"{best.get('name')} 的 avg_score_delta 相比 baseline 提升 "
                f"{round(float(score_delta), 4)}，建议进入下一阶段复验。"
            )
        kg_score_delta = metric_comparison.get("avg_kg_score", {}).get("delta")
        if isinstance(kg_score_delta, (int, float)) and kg_score_delta > 0:
            return (
                f"{best.get('name')} 的 avg_kg_score 有提升；"
                "建议结合 avg_score_delta 判断是否继续复验。"
            )
        if warnings:
            return "存在告警项，建议先排查告警再决定是否提升参数。"
        return "最优实验相对 baseline 的 score 指标提升不明显，建议保留当前 baseline。"
    recall_delta = metric_comparison.get("micro_recall", {}).get("delta")
    f1_delta = metric_comparison.get("micro_f1", {}).get("delta")
    if isinstance(recall_delta, (int, float)) and recall_delta > 0:
        return (
            f"{best.get('name')} 的 micro_recall 相比 baseline 提升 "
            f"{round(float(recall_delta), 4)}，建议进入下一阶段复验。"
        )
    if isinstance(f1_delta, (int, float)) and f1_delta > 0:
        return (
            f"{best.get('name')} 的 micro_f1 有提升，但 recall 未提升；"
            "建议结合业务目标决定是否继续复验。"
        )
    if warnings:
        return "存在告警项，建议先排查告警再决定是否提升参数。"
    return "最优实验相对 baseline 提升不明显，建议保留当前 baseline。"


def compact_experiment_row(row: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return high-signal fields from a leaderboard row."""
    if row is None:
        return None
    result = {
        "rank": row.get("rank"),
        "name": row.get("name"),
        "summary_path": row.get("summary_path"),
        "overrides": row.get("overrides"),
    }
    for field_name in METRIC_FIELDS:
        result[field_name] = row.get(field_name)
    return result


def pick_summary_fields(summary: dict[str, Any]) -> dict[str, Any]:
    """Pick high-signal summary fields for report JSON."""
    field_names = (
        "total_count",
        "success_count",
        "failed_count",
        "evaluated_count",
        "score_evaluated_count",
        "avg_kg_score",
        "avg_csv_score",
        "avg_score_delta",
        "task_hit_rate",
        "micro_precision",
        "micro_recall",
        "micro_f1",
        "avg_elapsed_seconds",
        "candidate_training_tasks_actual_missing_rate",
        "similar_user_game_counts_actual_missing_rate",
    )
    return {field_name: summary.get(field_name) for field_name in field_names}


def build_markdown_report(analysis: dict[str, Any]) -> str:
    """Build a readable Markdown report."""
    if analysis.get("status") != "ok":
        return (
            "# Evaluation Grid Analysis\n\n"
            f"Status: {analysis.get('status')}\n\n"
            f"{analysis.get('recommendation')}\n"
        )

    best = analysis.get("best_experiment") or {}
    second_best = analysis.get("second_best_experiment") or {}
    baseline = analysis.get("baseline_experiment") or {}
    comparison = analysis.get("metric_comparison") or {}
    second_best_comparison = analysis.get("second_best_metric_comparison") or {}
    parameter_diff = analysis.get("parameter_diff") or {}
    second_best_parameter_diff = analysis.get("second_best_parameter_diff") or {}
    warnings = analysis.get("warnings") or []
    lines = [
        "# Evaluation Grid Analysis",
        "",
        f"- Grid dir: `{analysis.get('grid_dir')}`",
        f"- Rank by: `{analysis.get('rank_by')}`",
        f"- Best experiment: `{best.get('name')}`",
        f"- Second-best experiment: `{second_best.get('name')}`",
        f"- Baseline experiment: `{baseline.get('name')}`",
        "",
        "## Metric Comparison: Best vs Baseline",
        "",
        "| Metric | Baseline | Best | Delta | Relative Delta |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for field_name in METRIC_FIELDS:
        item = comparison.get(field_name) or {}
        lines.append(
            "| "
            f"{field_name} | "
            f"{format_metric(item.get('baseline'))} | "
            f"{format_metric(item.get('best'))} | "
            f"{format_metric(item.get('delta'))} | "
            f"{format_metric(item.get('relative_delta'))} |"
        )

    lines.extend(
        [
            "",
            "## Metric Comparison: Second-best vs Baseline",
            "",
            "| Metric | Baseline | Second-best | Delta | Relative Delta |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for field_name in METRIC_FIELDS:
        item = second_best_comparison.get(field_name) or {}
        lines.append(
            "| "
            f"{field_name} | "
            f"{format_metric(item.get('baseline'))} | "
            f"{format_metric(item.get('best'))} | "
            f"{format_metric(item.get('delta'))} | "
            f"{format_metric(item.get('relative_delta'))} |"
        )

    lines.extend(["", "## Parameter Diff: Best vs Baseline", ""])
    if parameter_diff:
        lines.extend(
            f"- `{key}`: `{value.get('baseline')}` -> `{value.get('best')}`"
            for key, value in parameter_diff.items()
        )
    else:
        lines.append("- No parameter differences from baseline.")

    lines.extend(["", "## Parameter Diff: Second-best vs Baseline", ""])
    if second_best_parameter_diff:
        lines.extend(
            f"- `{key}`: `{value.get('baseline')}` -> `{value.get('best')}`"
            for key, value in second_best_parameter_diff.items()
        )
    else:
        lines.append("- No parameter differences from baseline.")

    lines.extend(["", "## Warnings", ""])
    if warnings:
        lines.extend(f"- {warning}" for warning in warnings)
    else:
        lines.append("- No warnings.")

    lines.extend(["", "## Recommendation", "", str(analysis.get("recommendation"))])
    return "\n".join(lines) + "\n"


def numeric_metric(value: Any) -> float:
    """Convert metric-like values to floats."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def format_metric(value: Any) -> str:
    """Format metric values for Markdown."""
    if value is None:
        return "-"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return str(round(float(value), 4))
    return str(value)


def main() -> int:
    """Analyze one evaluation grid directory."""
    args = parse_args()
    try:
        output_paths = analyze_and_write_evaluation_grid_report(
            args.grid_dir,
            json_file=args.json_file,
            markdown_file=args.markdown_file,
        )
    except Exception as exc:
        LOGGER.exception("Evaluation grid analysis failed: %s", exc)
        return 1

    LOGGER.info(
        "Wrote evaluation grid analysis: json_path=%s, markdown_path=%s",
        output_paths["json"],
        output_paths["markdown"],
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
