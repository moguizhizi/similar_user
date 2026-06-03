"""Run training-task evaluation for one training date per month.

默认从训练日期文件中选择 2024 到 2026 年每个月最新的一天，并依次调用：

    python scripts/evaluate_predict_training_tasks.py --base-date YYYY-MM-DD

默认 keep-going：某个月失败后记录失败并继续执行后续月份。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from similar_user.services.task_prediction import parse_date_value
from similar_user.utils.logger import get_logger

from scripts.export_training_dates import DEFAULT_OUTPUT_PATH as DEFAULT_DATES_FILE
from scripts.score_pattern_paths import DEFAULT_CONFIG_PATH


LOGGER = get_logger(__name__)
DEFAULT_LOG_DIR = Path("logs/monthly_evaluation")
DEFAULT_SELECTED_DATES_OUTPUT = Path(
    "data/training_dates/monthly_training_dates_2024_2026.txt"
)
DEFAULT_START_YEAR = 2024
DEFAULT_END_YEAR = 2026


@dataclass(frozen=True)
class MonthlyEvaluationRun:
    """One selected month/date and the command used for evaluation."""

    month: str
    base_date: str
    patient_export_command: list[str]
    command: list[str]
    log_path: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Run evaluation for one selected training date per month."
    )
    parser.add_argument(
        "--training-dates-file",
        default=str(DEFAULT_DATES_FILE),
        help="File containing one training date per line.",
    )
    parser.add_argument(
        "--start-year",
        type=int,
        default=DEFAULT_START_YEAR,
        help="First year included in monthly date selection.",
    )
    parser.add_argument(
        "--end-year",
        type=int,
        default=DEFAULT_END_YEAR,
        help="Last year included in monthly date selection.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Config path passed to evaluate_predict_training_tasks.py.",
    )
    parser.add_argument(
        "--log-dir",
        default=str(DEFAULT_LOG_DIR),
        help="Directory used for per-date evaluation logs.",
    )
    parser.add_argument(
        "--selected-dates-output",
        default=str(DEFAULT_SELECTED_DATES_OUTPUT),
        help="File used to save the selected monthly training dates.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected dates and commands without running evaluation.",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop after the first failed evaluation. Default is keep-going.",
    )
    parser.add_argument(
        "--use-llm",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Pass LLM/dry-run mode to evaluation; use --no-use-llm for dry-run evaluation.",
    )
    return parser.parse_args()


def read_training_dates(path: str | Path) -> list[str]:
    """Read non-empty training dates from a text file."""
    resolved_path = Path(path)
    return [
        line.strip()
        for line in resolved_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def select_latest_training_date_per_month(
    training_dates: list[str],
    *,
    start_year: int,
    end_year: int,
) -> list[str]:
    """Select the latest available training date for each month in ascending order."""
    if start_year > end_year:
        raise ValueError("start_year must be less than or equal to end_year.")

    latest_by_month: dict[str, date] = {}
    for raw_training_date in training_dates:
        parsed_date = parse_date_value(raw_training_date, "training_date")
        if parsed_date.year < start_year or parsed_date.year > end_year:
            continue
        month_key = f"{parsed_date.year:04d}-{parsed_date.month:02d}"
        existing_date = latest_by_month.get(month_key)
        if existing_date is None or parsed_date > existing_date:
            latest_by_month[month_key] = parsed_date

    return [
        latest_by_month[month_key].isoformat()
        for month_key in sorted(latest_by_month)
    ]


def build_evaluation_command(
    *,
    base_date: str,
    config_path: str | Path,
    use_llm: bool,
) -> list[str]:
    """Build the evaluate_predict_training_tasks.py command."""
    command = [
        sys.executable,
        "scripts/evaluate_predict_training_tasks.py",
        "--base-date",
        base_date,
        "--config",
        str(config_path),
    ]
    if not use_llm:
        command.append("--dry-run")
    return command


def build_patient_export_command(
    *,
    base_date: str,
    config_path: str | Path,
) -> list[str]:
    """Build the command that refreshes the limited patient ID file."""
    return [
        sys.executable,
        "scripts/export_patient_ids_with_training_on_date.py",
        "--base-date",
        base_date,
        "--config",
        str(config_path),
    ]


def write_selected_training_dates(
    selected_dates: list[str],
    output_path: str | Path,
) -> Path:
    """Write selected monthly training dates, one date per line."""
    resolved_output_path = Path(output_path)
    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(
        "".join(f"{selected_date}\n" for selected_date in selected_dates),
        encoding="utf-8",
    )
    return resolved_output_path


def build_monthly_evaluation_runs(
    *,
    selected_dates: list[str],
    config_path: str | Path,
    log_dir: str | Path,
    use_llm: bool,
) -> list[MonthlyEvaluationRun]:
    """Build monthly evaluation run descriptors."""
    resolved_log_dir = Path(log_dir)
    runs: list[MonthlyEvaluationRun] = []
    for selected_date in selected_dates:
        month = selected_date[:7]
        patient_export_command = build_patient_export_command(
            base_date=selected_date,
            config_path=config_path,
        )
        command = build_evaluation_command(
            base_date=selected_date,
            config_path=config_path,
            use_llm=use_llm,
        )
        runs.append(
            MonthlyEvaluationRun(
                month=month,
                base_date=selected_date,
                patient_export_command=patient_export_command,
                command=command,
                log_path=str(resolved_log_dir / f"evaluate_{selected_date}.log"),
            )
        )
    return runs


def run_monthly_evaluations(
    runs: list[MonthlyEvaluationRun],
    *,
    dry_run: bool = False,
    keep_going: bool = True,
) -> dict[str, Any]:
    """Run monthly evaluations and return a compact execution summary."""
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for run in runs:
        if dry_run:
            successes.append(
                {
                    "month": run.month,
                    "base_date": run.base_date,
                    "patient_export_command": run.patient_export_command,
                    "command": run.command,
                    "log_path": run.log_path,
                    "dry_run": True,
                }
            )
            continue

        log_path = Path(run.log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as log_file:
            export_completed = subprocess.run(
                run.patient_export_command,
                cwd=PROJECT_ROOT,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False,
            )
            if export_completed.returncode != 0:
                result_item = {
                    "month": run.month,
                    "base_date": run.base_date,
                    "patient_export_command": run.patient_export_command,
                    "command": run.command,
                    "log_path": run.log_path,
                    "patient_export_returncode": export_completed.returncode,
                    "returncode": export_completed.returncode,
                }
                failures.append(result_item)
                if not keep_going:
                    break
                continue

            completed = subprocess.run(
                run.command,
                cwd=PROJECT_ROOT,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False,
            )
        result_item = {
            "month": run.month,
            "base_date": run.base_date,
            "patient_export_command": run.patient_export_command,
            "command": run.command,
            "log_path": run.log_path,
            "patient_export_returncode": export_completed.returncode,
            "returncode": completed.returncode,
        }
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
        "successes": successes,
        "failures": failures,
    }


def main() -> int:
    """Run monthly evaluation workflow."""
    args = parse_args()
    try:
        training_dates = read_training_dates(args.training_dates_file)
        selected_dates = select_latest_training_date_per_month(
            training_dates,
            start_year=args.start_year,
            end_year=args.end_year,
        )
        selected_dates_path = write_selected_training_dates(
            selected_dates,
            args.selected_dates_output,
        )
        runs = build_monthly_evaluation_runs(
            selected_dates=selected_dates,
            config_path=args.config,
            log_dir=args.log_dir,
            use_llm=args.use_llm,
        )
        result = run_monthly_evaluations(
            runs,
            dry_run=args.dry_run,
            keep_going=not args.stop_on_failure,
        )
        result["selected_dates_output_path"] = str(selected_dates_path)
    except Exception as exc:
        LOGGER.exception("Monthly evaluation workflow failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failed_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
