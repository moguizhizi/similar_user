"""Tests for monthly evaluation date runner."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import run_monthly_evaluation_dates


class RunMonthlyEvaluationDatesTest(unittest.TestCase):
    def test_select_latest_training_date_per_month_filters_years(self) -> None:
        selected_dates = (
            run_monthly_evaluation_dates.select_latest_training_date_per_month(
                [
                    "2026-01-02",
                    "2025-02-02",
                    "2025-02-20",
                    "2024-01-30",
                    "2024-01-01",
                    "2023-12-31",
                ],
                start_year=2024,
                end_year=2025,
            )
        )

        self.assertEqual(selected_dates, ["2024-01-30", "2025-02-20"])

    def test_build_evaluation_command_uses_python_and_options(self) -> None:
        command = run_monthly_evaluation_dates.build_evaluation_command(
            base_date="2024-02-23",
            config_path="config/settings.yaml",
            use_llm=False,
        )

        self.assertEqual(
            command[1:],
            [
                "scripts/evaluate_predict_training_tasks.py",
                "--base-date",
                "2024-02-23",
                "--config",
                "config/settings.yaml",
                "--dry-run",
            ],
        )

    def test_build_patient_export_command_refreshes_base_date_file(self) -> None:
        command = run_monthly_evaluation_dates.build_patient_export_command(
            base_date="2024-02-23",
            config_path="config/settings.yaml",
        )

        self.assertEqual(
            command[1:],
            [
                "scripts/export_patient_ids_with_training_on_date.py",
                "--base-date",
                "2024-02-23",
                "--config",
                "config/settings.yaml",
            ],
        )

    def test_write_selected_training_dates_writes_one_date_per_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "monthly_dates.txt"

            written_path = run_monthly_evaluation_dates.write_selected_training_dates(
                ["2024-01-31", "2024-02-29"],
                output_path,
            )

            self.assertEqual(written_path, output_path)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "2024-01-31\n2024-02-29\n",
            )

    def test_run_monthly_evaluations_keeps_going_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs = [
                run_monthly_evaluation_dates.MonthlyEvaluationRun(
                    month="2024-01",
                    base_date="2024-01-31",
                    patient_export_command=["python", "export"],
                    command=["python", "fail"],
                    log_path=str(Path(temp_dir) / "fail.log"),
                ),
                run_monthly_evaluation_dates.MonthlyEvaluationRun(
                    month="2024-02",
                    base_date="2024-02-23",
                    patient_export_command=["python", "export"],
                    command=["python", "ok"],
                    log_path=str(Path(temp_dir) / "ok.log"),
                ),
            ]

            with patch(
                "scripts.run_monthly_evaluation_dates.subprocess.run"
            ) as mock_run:
                mock_run.side_effect = [
                    Mock(returncode=0),
                    Mock(returncode=1),
                    Mock(returncode=0),
                    Mock(returncode=0),
                ]

                result = run_monthly_evaluation_dates.run_monthly_evaluations(runs)

        self.assertEqual(mock_run.call_count, 4)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["success_count"], 1)

    def test_run_monthly_evaluations_stops_after_patient_export_failure(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs = [
                run_monthly_evaluation_dates.MonthlyEvaluationRun(
                    month="2024-01",
                    base_date="2024-01-31",
                    patient_export_command=["python", "export"],
                    command=["python", "evaluate"],
                    log_path=str(Path(temp_dir) / "fail.log"),
                ),
            ]

            with patch(
                "scripts.run_monthly_evaluation_dates.subprocess.run"
            ) as mock_run:
                mock_run.return_value = Mock(returncode=1)

                result = run_monthly_evaluation_dates.run_monthly_evaluations(runs)

        mock_run.assert_called_once()
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["success_count"], 0)
        self.assertEqual(result["failures"][0]["patient_export_returncode"], 1)

    def test_run_monthly_evaluations_can_stop_on_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs = [
                run_monthly_evaluation_dates.MonthlyEvaluationRun(
                    month="2024-01",
                    base_date="2024-01-31",
                    patient_export_command=["python", "export"],
                    command=["python", "fail"],
                    log_path=str(Path(temp_dir) / "fail.log"),
                ),
                run_monthly_evaluation_dates.MonthlyEvaluationRun(
                    month="2024-02",
                    base_date="2024-02-23",
                    patient_export_command=["python", "export"],
                    command=["python", "ok"],
                    log_path=str(Path(temp_dir) / "ok.log"),
                ),
            ]

            with patch(
                "scripts.run_monthly_evaluation_dates.subprocess.run"
            ) as mock_run:
                mock_run.side_effect = [
                    Mock(returncode=0),
                    Mock(returncode=1),
                ]

                result = run_monthly_evaluation_dates.run_monthly_evaluations(
                    runs,
                    keep_going=False,
                )

        self.assertEqual(mock_run.call_count, 2)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["success_count"], 0)

    def test_run_monthly_evaluations_dry_run_does_not_call_subprocess(self) -> None:
        runs = [
            run_monthly_evaluation_dates.MonthlyEvaluationRun(
                month="2024-02",
                base_date="2024-02-23",
                patient_export_command=["python", "export"],
                command=["python", "evaluate"],
                log_path="logs/evaluate_2024-02-23.log",
            )
        ]

        with patch("scripts.run_monthly_evaluation_dates.subprocess.run") as mock_run:
            result = run_monthly_evaluation_dates.run_monthly_evaluations(
                runs,
                dry_run=True,
            )

        mock_run.assert_not_called()
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["successes"][0]["dry_run"], True)


if __name__ == "__main__":
    unittest.main()
