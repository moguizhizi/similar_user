"""Build configured pattern paths for one training date per month.

默认从训练日期文件中选择 2024 到 2026 年每个月最新的一天。每个日期先刷新
当天最多 100 个训练患者列表，再逐个调用：

    python scripts/build_pattern_paths.py --source-id PATIENT_ID --patterns-from-config \
        --base-date BASE_DATE --query-family training_order

默认 keep-going：某个患者或日期失败后记录失败并继续后续任务。
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from scripts.export_patient_ids_with_training_on_date import (
    DEFAULT_OUTPUT_DIR as DEFAULT_PATIENT_LIST_DIR,
    build_patient_ids_output_path,
)
from scripts.run_monthly_evaluation_dates import (
    DEFAULT_END_YEAR,
    DEFAULT_SELECTED_DATES_OUTPUT,
    DEFAULT_START_YEAR,
    read_training_dates,
    select_latest_training_date_per_month,
    write_selected_training_dates,
)
from scripts.export_training_dates import DEFAULT_OUTPUT_PATH as DEFAULT_DATES_FILE
from scripts.score_pattern_paths import DEFAULT_CONFIG_PATH
from similar_user.utils.logger import get_logger


LOGGER = get_logger(__name__)
DEFAULT_LOG_DIR = Path("logs/monthly_pattern_paths")


@dataclass(frozen=True)
class MonthlyPatternPathRun:
    """One patient's pattern path build command for a selected date."""

    month: str
    base_date: str
    patient_id: str
    command: list[str]
    log_path: str


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Build configured pattern paths for monthly selected dates."
    )
    parser.add_argument(
        "--training-dates-file",
        default=str(DEFAULT_DATES_FILE),
        help="File containing one training date per line.",
    )
    parser.add_argument(
        "--base-date",
        help=(
            "Single base date used with --patient-ids-file. "
            "When set, monthly date selection is skipped."
        ),
    )
    parser.add_argument(
        "--patient-ids-file",
        help=(
            "Optional patient ID file. When set, the script reads this file "
            "instead of refreshing monthly patient files."
        ),
    )
    parser.add_argument(
        "--patient-limit",
        type=int,
        default=100,
        help="Maximum number of patient IDs read from --patient-ids-file.",
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
        help="Config path passed to child scripts.",
    )
    parser.add_argument(
        "--patient-list-dir",
        default=str(DEFAULT_PATIENT_LIST_DIR),
        help="Base directory for refreshed patient ID files.",
    )
    parser.add_argument(
        "--log-dir",
        default=str(DEFAULT_LOG_DIR),
        help="Directory used for per-patient path build logs.",
    )
    parser.add_argument(
        "--selected-dates-output",
        default=str(DEFAULT_SELECTED_DATES_OUTPUT),
        help="File used to save the selected monthly training dates.",
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
        help="Query family passed to build_pattern_paths.py.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected dates and commands without running path builds.",
    )
    parser.add_argument(
        "--stop-on-failure",
        action="store_true",
        help="Stop after the first failed command. Default is keep-going.",
    )
    return parser.parse_args()


def read_patient_ids(path: str | Path) -> list[str]:
    """Read non-empty patient IDs from a text file."""
    return [
        line.strip()
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]


def read_limited_patient_ids(path: str | Path, limit: int | None) -> list[str]:
    """Read patient IDs and optionally keep only the first N."""
    patient_ids = read_patient_ids(path)
    if limit is None:
        return patient_ids
    if limit <= 0:
        raise ValueError("patient_limit must be a positive integer.")
    return patient_ids[:limit]


def build_pattern_path_command(
    *,
    patient_id: str,
    base_date: str,
    config_path: str | Path,
    query_family: str | None,
) -> list[str]:
    """Build the configured pattern path command for one patient."""
    command = [
        sys.executable,
        "scripts/build_pattern_paths.py",
        "--source-id",
        patient_id,
        "--patterns-from-config",
        "--base-date",
        base_date,
        "--config",
        str(config_path),
    ]
    if query_family is not None:
        command.extend(["--query-family", query_family])
    return command


def build_patient_export_command(
    *,
    base_date: str,
    config_path: str | Path,
    output_dir: str | Path,
) -> list[str]:
    """Build the command that refreshes the limited patient ID file."""
    return [
        sys.executable,
        "scripts/export_patient_ids_with_training_on_date.py",
        "--base-date",
        base_date,
        "--config",
        str(config_path),
        "--output-dir",
        str(output_dir),
    ]


def build_monthly_pattern_path_runs(
    *,
    selected_dates: list[str],
    patient_list_dir: str | Path,
    config_path: str | Path,
    log_dir: str | Path,
    query_family: str | None,
) -> list[MonthlyPatternPathRun]:
    """Build per-patient pattern path run descriptors from refreshed patient files."""
    resolved_log_dir = Path(log_dir)
    runs: list[MonthlyPatternPathRun] = []
    for selected_date in selected_dates:
        patient_ids_path = build_patient_ids_output_path(
            base_date=selected_date,
            output_dir=patient_list_dir,
        )
        for patient_id in read_patient_ids(patient_ids_path):
            command = build_pattern_path_command(
                patient_id=patient_id,
                base_date=selected_date,
                config_path=config_path,
                query_family=query_family,
            )
            runs.append(
                MonthlyPatternPathRun(
                    month=selected_date[:7],
                    base_date=selected_date,
                    patient_id=patient_id,
                    command=command,
                    log_path=str(
                        resolved_log_dir / selected_date / f"{patient_id}.log"
                    ),
                )
            )
    return runs


def build_patient_file_pattern_path_runs(
    *,
    patient_ids_file: str | Path,
    patient_limit: int | None,
    base_date: str,
    config_path: str | Path,
    log_dir: str | Path,
    query_family: str | None,
) -> list[MonthlyPatternPathRun]:
    """Build pattern path run descriptors from an explicit patient ID file."""
    resolved_log_dir = Path(log_dir)
    runs: list[MonthlyPatternPathRun] = []
    for patient_id in read_limited_patient_ids(patient_ids_file, patient_limit):
        command = build_pattern_path_command(
            patient_id=patient_id,
            base_date=base_date,
            config_path=config_path,
            query_family=query_family,
        )
        runs.append(
            MonthlyPatternPathRun(
                month=base_date[:7],
                base_date=base_date,
                patient_id=patient_id,
                command=command,
                log_path=str(resolved_log_dir / base_date / f"{patient_id}.log"),
            )
        )
    return runs


def refresh_patient_lists(
    *,
    selected_dates: list[str],
    config_path: str | Path,
    patient_list_dir: str | Path,
    dry_run: bool,
    keep_going: bool,
    log_dir: str | Path,
) -> list[dict[str, Any]]:
    """Refresh limited patient files for selected dates and return failures."""
    failures: list[dict[str, Any]] = []
    for selected_date in selected_dates:
        command = build_patient_export_command(
            base_date=selected_date,
            config_path=config_path,
            output_dir=patient_list_dir,
        )
        if dry_run:
            continue

        log_path = Path(log_dir) / selected_date / "patient_export.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as log_file:
            completed = subprocess.run(
                command,
                cwd=PROJECT_ROOT,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False,
            )
        if completed.returncode != 0:
            failures.append(
                {
                    "base_date": selected_date,
                    "patient_export_command": command,
                    "log_path": str(log_path),
                    "returncode": completed.returncode,
                }
            )
            if not keep_going:
                break
    return failures


def run_monthly_pattern_paths(
    runs: list[MonthlyPatternPathRun],
    *,
    dry_run: bool = False,
    keep_going: bool = True,
) -> dict[str, Any]:
    """Run pattern path builds and return a compact execution summary."""
    successes: list[dict[str, Any]] = []
    failures: list[dict[str, Any]] = []

    for run in runs:
        result_item = {
            "month": run.month,
            "base_date": run.base_date,
            "patient_id": run.patient_id,
            "command": run.command,
            "log_path": run.log_path,
        }
        if dry_run:
            successes.append({**result_item, "dry_run": True})
            continue

        log_path = Path(run.log_path)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        with log_path.open("w", encoding="utf-8") as log_file:
            completed = subprocess.run(
                run.command,
                cwd=PROJECT_ROOT,
                stdout=log_file,
                stderr=subprocess.STDOUT,
                check=False,
            )
        result_item["returncode"] = completed.returncode
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
    """Run monthly pattern path workflow."""
    args = parse_args()
    try:
        keep_going = not args.stop_on_failure

        if args.patient_ids_file:
            if not args.base_date:
                raise ValueError("--base-date is required when --patient-ids-file is set.")
            selected_dates_path = None
            patient_export_failures: list[dict[str, Any]] = []
            runs = build_patient_file_pattern_path_runs(
                patient_ids_file=args.patient_ids_file,
                patient_limit=args.patient_limit,
                base_date=args.base_date,
                config_path=args.config,
                log_dir=args.log_dir,
                query_family=args.query_family,
            )
        else:
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
            patient_export_failures = refresh_patient_lists(
                selected_dates=selected_dates,
                config_path=args.config,
                patient_list_dir=args.patient_list_dir,
                dry_run=args.dry_run,
                keep_going=keep_going,
                log_dir=args.log_dir,
            )
            runs = (
                []
                if patient_export_failures and not keep_going
                else build_monthly_pattern_path_runs(
                    selected_dates=selected_dates,
                    patient_list_dir=args.patient_list_dir,
                    config_path=args.config,
                    log_dir=args.log_dir,
                    query_family=args.query_family,
                )
            )

        result = run_monthly_pattern_paths(
            runs,
            dry_run=args.dry_run,
            keep_going=keep_going,
        )
        result["patient_export_failures"] = patient_export_failures
        result["selected_dates_output_path"] = (
            str(selected_dates_path) if selected_dates_path is not None else None
        )
        if args.patient_ids_file:
            result["patient_ids_file"] = args.patient_ids_file
            result["patient_limit"] = args.patient_limit
    except Exception as exc:
        LOGGER.exception("Monthly pattern path workflow failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result["failed_count"] or result["patient_export_failures"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
