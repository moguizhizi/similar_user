"""Run training-task evaluation over YAML-defined staged experiment overrides.

实验配置文件只描述本阶段基准参数和每组实验要覆盖哪些 YAML 参数；
本脚本会基于默认 settings.yaml 为每组参数生成一份临时配置，并调用
evaluate_predict_training_tasks.py。
"""

from __future__ import annotations

import argparse
import copy
import csv
import itertools
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import DEFAULT_CONFIG_PATH, load_yaml_config
from similar_user.utils.logger import get_logger


LOGGER = get_logger(__name__)
DEFAULT_EXPERIMENT_CONFIG_PATH = Path("config/experiments/evaluation_grid.yaml")
DEFAULT_OUTPUT_ROOT = Path("data/evaluation_grid")
DEFAULT_GENERATED_CONFIG_DIR = DEFAULT_OUTPUT_ROOT / "generated_configs"
DEFAULT_WINDOW_DAYS = 14
DEFAULT_TASK_TOP_K = 7
DEFAULT_RANK_BY = "micro_recall"
LEADERBOARD_FIELDS = (
    "rank",
    "name",
    "rank_metric",
    "micro_recall",
    "micro_f1",
    "task_hit_rate",
    "micro_precision",
    "macro_recall",
    "macro_f1",
    "evaluated_count",
    "success_count",
    "failed_count",
    "avg_elapsed_seconds",
    "summary_path",
    "overrides",
)


@dataclass(frozen=True)
class EvaluationGridRun:
    """One generated evaluation run."""

    index: int
    name: str
    overrides: dict[str, Any]
    config_path: str
    output_dir: str
    command: list[str]


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run evaluate_predict_training_tasks.py over a parameter grid."
    )
    parser.add_argument(
        "--experiment-config",
        default=str(DEFAULT_EXPERIMENT_CONFIG_PATH),
        help="YAML file containing stage, base options, and experiment overrides.",
    )
    parser.add_argument(
        "--settings",
        default=str(DEFAULT_CONFIG_PATH),
        help="Default settings.yaml used as the base config.",
    )
    parser.add_argument(
        "--output-root",
        default=str(DEFAULT_OUTPUT_ROOT),
        help="Root directory for generated configs, logs, and evaluation outputs.",
    )
    parser.add_argument(
        "--generated-config-dir",
        default=None,
        help="Directory for generated per-run YAML configs.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print runs without executing evaluate_predict_training_tasks.py.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Run even when the run output already contains a summary file.",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop after the first failed evaluation. Default is keep-going.",
    )
    parser.add_argument(
        "--rank-by",
        default=DEFAULT_RANK_BY,
        help=(
            "Primary summary metric used to rank completed experiments. "
            "Defaults to micro_recall."
        ),
    )
    return parser.parse_args()


def load_experiment_config(path: str | Path) -> dict[str, Any]:
    """Load experiment config YAML."""
    resolved_path = Path(path)
    with resolved_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Experiment config must contain a mapping: {resolved_path}")
    return data


def get_stage_name(experiment_config: dict[str, Any]) -> str:
    """Return the experiment stage name used to isolate outputs."""
    raw_stage = experiment_config.get("stage")
    if raw_stage is None:
        raise ValueError("experiment config must define a non-empty stage.")
    if not isinstance(raw_stage, str) or not raw_stage.strip():
        raise ValueError("experiment stage must be a non-empty string.")
    return raw_stage.strip()


def build_stage_output_root(output_root: str | Path, stage: str) -> Path:
    """Return the stage-specific output root."""
    return Path(output_root) / _slug_part(stage)


def build_grid_overrides(grid: dict[str, Any]) -> list[dict[str, Any]]:
    """Expand a mapping of dot-path parameters into cartesian-product overrides."""
    if not grid:
        return [{}]
    paths: list[str] = []
    values_by_path: list[list[Any]] = []
    for raw_path, raw_values in grid.items():
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError("Grid parameter names must be non-empty strings.")
        if not isinstance(raw_values, list) or not raw_values:
            raise ValueError(f"Grid parameter must define a non-empty list: {raw_path}")
        paths.append(raw_path)
        values_by_path.append(raw_values)

    overrides: list[dict[str, Any]] = []
    for combination in itertools.product(*values_by_path):
        overrides.append(dict(zip(paths, combination, strict=True)))
    return overrides


def build_named_experiment_overrides(
    experiments: list[Any],
) -> list[tuple[str, dict[str, Any]]]:
    """Read explicitly named experiment overrides from YAML."""
    named_overrides: list[tuple[str, dict[str, Any]]] = []
    for index, experiment in enumerate(experiments, start=1):
        if not isinstance(experiment, dict):
            raise ValueError("Each experiment must be a mapping.")
        raw_name = experiment.get("name") or f"exp_{index:03d}"
        if not isinstance(raw_name, str) or not raw_name.strip():
            raise ValueError("Experiment name must be a non-empty string.")
        overrides = experiment.get("overrides") or {}
        if not isinstance(overrides, dict):
            raise ValueError(f"Experiment overrides must be a mapping: {raw_name}")
        named_overrides.append((raw_name.strip(), dict(overrides)))
    return named_overrides


def build_experiment_override_specs(
    experiment_config: dict[str, Any],
) -> list[tuple[str | None, dict[str, Any]]]:
    """Build override specs from explicit experiments or legacy grid."""
    baseline_overrides = get_baseline_overrides(experiment_config)
    experiments = experiment_config.get("experiments")
    if experiments is not None:
        if not isinstance(experiments, list) or not experiments:
            raise ValueError("experiments must be a non-empty list when provided.")
        return [
            (name, merge_overrides(baseline_overrides, overrides))
            for name, overrides in build_named_experiment_overrides(experiments)
        ]

    grid = experiment_config.get("grid") or {}
    if not isinstance(grid, dict):
        raise ValueError("experiment grid section must be a mapping.")
    return [
        (None, merge_overrides(baseline_overrides, overrides))
        for overrides in build_grid_overrides(grid)
    ]


def get_baseline_overrides(experiment_config: dict[str, Any]) -> dict[str, Any]:
    """Return shared baseline overrides inherited by every experiment."""
    baseline_overrides = experiment_config.get("baseline_overrides") or {}
    if not isinstance(baseline_overrides, dict):
        raise ValueError("baseline_overrides must be a mapping when provided.")
    return dict(baseline_overrides)


def merge_overrides(
    base_overrides: dict[str, Any],
    experiment_overrides: dict[str, Any],
) -> dict[str, Any]:
    """Merge shared and per-experiment overrides, with experiment values winning."""
    return {**base_overrides, **experiment_overrides}


def apply_dot_path_override(
    config: dict[str, Any],
    dot_path: str,
    value: Any,
) -> None:
    """Apply one dot-path override to a nested dictionary."""
    parts = [part for part in dot_path.split(".") if part]
    if not parts:
        raise ValueError("Override path must not be empty.")
    current: dict[str, Any] = config
    for part in parts[:-1]:
        next_value = current.get(part)
        if next_value is None:
            next_value = {}
            current[part] = next_value
        if not isinstance(next_value, dict):
            raise ValueError(f"Cannot set nested override under non-mapping: {dot_path}")
        current = next_value
    current[parts[-1]] = value


def build_config_for_overrides(
    base_config: dict[str, Any],
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """Return a deep-copied config with all overrides applied."""
    config = copy.deepcopy(base_config)
    for dot_path, value in overrides.items():
        apply_dot_path_override(config, dot_path, value)
    return config


def write_generated_config(
    config: dict[str, Any],
    *,
    output_dir: str | Path,
    run_name: str,
) -> Path:
    """Write one generated YAML config."""
    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    config_path = resolved_output_dir / f"{run_name}.yaml"
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    return config_path


def build_run_name(index: int, overrides: dict[str, Any]) -> str:
    """Build a compact filesystem-friendly name for one override set."""
    if not overrides:
        return f"exp_{index:03d}_default"
    parts = [f"exp_{index:03d}"]
    for dot_path, value in overrides.items():
        key = dot_path.split(".")[-1]
        parts.append(f"{_slug_part(key)}-{_slug_part(value)}")
    return "_".join(parts)


def build_named_run_name(index: int, name: str) -> str:
    """Build a stable run name from an explicit experiment name."""
    return f"exp_{index:03d}_{_slug_part(name)}"


def build_evaluation_command(
    *,
    base_options: dict[str, Any],
    config_path: str | Path,
    output_dir: str | Path,
) -> list[str]:
    """Build the evaluate_predict_training_tasks.py command for one run."""
    base_date = base_options.get("base_date")
    if not isinstance(base_date, str) or not base_date.strip():
        raise ValueError("base.base_date must be a non-empty string.")
    window_days = base_options.get("window_days", DEFAULT_WINDOW_DAYS)
    task_top_k = base_options.get("task_top_k", DEFAULT_TASK_TOP_K)
    use_llm = bool(base_options.get("use_llm", True))
    command = [
        sys.executable,
        "scripts/evaluate_predict_training_tasks.py",
        "--base-date",
        base_date,
        "--window-days",
        str(window_days),
        "--config",
        str(config_path),
        "--task-top-k",
        str(task_top_k),
        "--output-dir",
        str(output_dir),
    ]

    optional_args = {
        "patient_id": "--patient-id",
        "patient_list_dir": "--patient-list-dir",
        "pattern": "--pattern",
        "query_family": "--query-family",
        "limit": "--limit",
        "prompt_output_dir": "--prompt-output-dir",
    }
    for option_name, cli_flag in optional_args.items():
        option_value = base_options.get(option_name)
        if option_value is not None:
            command.extend([cli_flag, str(option_value)])

    if not use_llm:
        command.append("--dry-run")
    if bool(base_options.get("skip_path_build", False)):
        command.append("--skip-path-build")
    if bool(base_options.get("no_save_prompt", False)):
        command.append("--no-save-prompt")
    return command


def build_grid_runs(
    *,
    experiment_config: dict[str, Any],
    settings_path: str | Path,
    output_root: str | Path,
    generated_config_dir: str | Path,
) -> list[EvaluationGridRun]:
    """Build all grid runs and generated config files."""
    base_options = experiment_config.get("base") or {}
    if not isinstance(base_options, dict):
        raise ValueError("experiment base section must be a mapping.")

    base_config = load_yaml_config(settings_path)
    runs: list[EvaluationGridRun] = []
    override_specs = build_experiment_override_specs(experiment_config)
    for index, (name, overrides) in enumerate(override_specs, start=1):
        run_name = (
            build_named_run_name(index, name)
            if name is not None
            else build_run_name(index, overrides)
        )
        generated_config = build_config_for_overrides(base_config, overrides)
        config_path = write_generated_config(
            generated_config,
            output_dir=generated_config_dir,
            run_name=run_name,
        )
        output_dir = Path(output_root) / "runs" / run_name
        command = build_evaluation_command(
            base_options=base_options,
            config_path=config_path,
            output_dir=output_dir,
        )
        runs.append(
            EvaluationGridRun(
                index=index,
                name=run_name,
                overrides=overrides,
                config_path=str(config_path),
                output_dir=str(output_dir),
                command=command,
            )
        )
    return runs


def run_evaluation_grid(
    runs: list[EvaluationGridRun],
    *,
    output_root: str | Path,
    dry_run: bool = False,
    force: bool = False,
    keep_going: bool = True,
) -> dict[str, Any]:
    """Run all grid evaluations and write a compact execution summary."""
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    log_dir = Path(output_root) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)

    for run in runs:
        summary_paths = list(Path(run.output_dir).glob("**/predict_training_tasks_summary.json"))
        if summary_paths and not force:
            skipped.append(build_result_item(run, status="skipped_existing"))
            continue
        if dry_run:
            successes.append(build_result_item(run, status="dry_run"))
            continue

        log_path = log_dir / f"{run.name}.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as log_file:
            completed = subprocess.run(
                run.command,
                cwd=PROJECT_ROOT,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False,
            )
        result_item = build_result_item(
            run,
            status="success" if completed.returncode == 0 else "failed",
            log_path=str(log_path),
            returncode=completed.returncode,
        )
        if completed.returncode == 0:
            successes.append(result_item)
        else:
            failures.append(result_item)
            if not keep_going:
                break

    return {
        "selected_count": len(runs),
        "success_count": len(successes),
        "failed_count": len(failures),
        "skipped_count": len(skipped),
        "successes": successes,
        "failures": failures,
        "skipped": skipped,
    }


def build_leaderboard(
    runs: list[EvaluationGridRun],
    *,
    rank_by: str = DEFAULT_RANK_BY,
) -> list[dict[str, Any]]:
    """Build ranked experiment rows from completed evaluation summaries."""
    rows: list[dict[str, Any]] = []
    for run in runs:
        summary_path = find_evaluation_summary_path(run.output_dir)
        if summary_path is None:
            continue
        summary = read_json_object(summary_path)
        row = build_leaderboard_row(
            run,
            summary=summary,
            summary_path=summary_path,
            rank_by=rank_by,
        )
        rows.append(row)

    rows.sort(key=lambda row: build_leaderboard_sort_key(row, rank_by))
    for index, row in enumerate(rows, start=1):
        row["rank"] = index
    return rows


def find_evaluation_summary_path(output_dir: str | Path) -> Path | None:
    """Return the first evaluation summary under a run output directory."""
    summary_paths = sorted(Path(output_dir).glob("**/predict_training_tasks_summary.json"))
    return summary_paths[0] if summary_paths else None


def read_json_object(path: str | Path) -> dict[str, Any]:
    """Read one JSON object from disk."""
    with Path(path).open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"JSON file must contain an object: {path}")
    return data


def build_leaderboard_row(
    run: EvaluationGridRun,
    *,
    summary: dict[str, Any],
    summary_path: str | Path,
    rank_by: str,
) -> dict[str, Any]:
    """Build one leaderboard row from a run and its summary metrics."""
    row: dict[str, Any] = {
        "rank": 0,
        "name": run.name,
        "rank_metric": rank_by,
        "summary_path": str(summary_path),
        "overrides": run.overrides,
    }
    for field_name in LEADERBOARD_FIELDS:
        if field_name in row:
            continue
        row[field_name] = summary.get(field_name)
    return row


def build_leaderboard_sort_key(row: dict[str, Any], rank_by: str) -> tuple[Any, ...]:
    """Sort by primary metric, then stable secondary metrics."""
    return (
        -numeric_metric(row.get(rank_by)),
        -numeric_metric(row.get("micro_f1")),
        -numeric_metric(row.get("task_hit_rate")),
        -numeric_metric(row.get("micro_precision")),
        numeric_metric(row.get("avg_elapsed_seconds")),
        str(row.get("name") or ""),
    )


def numeric_metric(value: Any) -> float:
    """Convert metric-like values to sortable floats."""
    if isinstance(value, bool):
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def build_result_item(
    run: EvaluationGridRun,
    *,
    status: str,
    log_path: str | None = None,
    returncode: int | None = None,
) -> dict[str, Any]:
    """Build a JSON-friendly result item."""
    return {
        "name": run.name,
        "status": status,
        "overrides": run.overrides,
        "config_path": run.config_path,
        "output_dir": run.output_dir,
        "command": run.command,
        "log_path": log_path,
        "returncode": returncode,
    }


def write_grid_summary(summary: dict[str, Any], output_root: str | Path) -> Path:
    """Write the grid execution summary."""
    output_path = Path(output_root) / "grid_summary.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return output_path


def write_leaderboard_outputs(
    leaderboard: list[dict[str, Any]],
    output_root: str | Path,
) -> tuple[Path, Path]:
    """Write JSON and CSV leaderboard outputs."""
    resolved_output_root = Path(output_root)
    resolved_output_root.mkdir(parents=True, exist_ok=True)
    json_path = resolved_output_root / "leaderboard.json"
    csv_path = resolved_output_root / "leaderboard.csv"
    json_path.write_text(
        json.dumps(leaderboard, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=LEADERBOARD_FIELDS)
        writer.writeheader()
        for row in leaderboard:
            writer.writerow(
                {
                    field_name: serialize_csv_value(row.get(field_name))
                    for field_name in LEADERBOARD_FIELDS
                }
            )
    return json_path, csv_path


def serialize_csv_value(value: Any) -> str | int | float | None:
    """Serialize complex values while keeping scalar CSV values readable."""
    if value is None or isinstance(value, (int, float, str)):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)


def _slug_part(value: Any) -> str:
    """Return a filesystem-friendly string."""
    text = str(value if value is not None else "none").strip().lower()
    return "".join(char if char.isalnum() else "-" for char in text) or "none"


def main() -> int:
    """Run the evaluation grid workflow."""
    args = parse_args()
    try:
        experiment_config = load_experiment_config(args.experiment_config)
        stage = get_stage_name(experiment_config)
        output_root = build_stage_output_root(args.output_root, stage)
        generated_config_dir = (
            Path(args.generated_config_dir)
            if args.generated_config_dir is not None
            else output_root / "generated_configs"
        )
        runs = build_grid_runs(
            experiment_config=experiment_config,
            settings_path=args.settings,
            output_root=output_root,
            generated_config_dir=generated_config_dir,
        )
        result = run_evaluation_grid(
            runs,
            output_root=output_root,
            dry_run=args.dry_run,
            force=args.force,
            keep_going=not args.stop_on_failure,
        )
        result["stage"] = stage
        leaderboard = build_leaderboard(runs, rank_by=args.rank_by)
        leaderboard_json_path, leaderboard_csv_path = write_leaderboard_outputs(
            leaderboard,
            output_root,
        )
        result["leaderboard_count"] = len(leaderboard)
        result["leaderboard_json_path"] = str(leaderboard_json_path)
        result["leaderboard_csv_path"] = str(leaderboard_csv_path)
        result["best_experiment"] = leaderboard[0] if leaderboard else None
        summary_path = write_grid_summary(result, output_root)
        result["summary_path"] = str(summary_path)
    except Exception as exc:
        LOGGER.exception("Evaluation grid failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 1 if result["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
