"""Tests for monthly pattern path runner."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import run_monthly_pattern_paths


class RunMonthlyPatternPathsTest(unittest.TestCase):
    def test_build_patient_export_command_uses_output_dir(self) -> None:
        command = run_monthly_pattern_paths.build_patient_export_command(
            base_date="2024-02-23",
            config_path="config/settings.yaml",
            output_dir="data/patient_ids",
        )

        self.assertEqual(
            command[1:],
            [
                "scripts/export_patient_ids_with_training_on_date.py",
                "--base-date",
                "2024-02-23",
                "--config",
                "config/settings.yaml",
                "--output-dir",
                "data/patient_ids",
            ],
        )

    def test_build_pattern_path_command_uses_configured_patterns(self) -> None:
        command = run_monthly_pattern_paths.build_pattern_path_command(
            patient_id="20102686",
            base_date="2024-02-23",
            config_path="config/settings.yaml",
            query_family="training_order",
        )

        self.assertEqual(
            command[1:],
            [
                "scripts/build_pattern_paths.py",
                "--source-id",
                "20102686",
                "--patterns-from-config",
                "--base-date",
                "2024-02-23",
                "--config",
                "config/settings.yaml",
                "--query-family",
                "training_order",
            ],
        )

    def test_build_monthly_pattern_path_runs_reads_refreshed_patient_files(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            patient_file = (
                Path(temp_dir)
                / "base_2024-02-23"
                / "patients_active_2024-02-23.txt"
            )
            patient_file.parent.mkdir(parents=True)
            patient_file.write_text("20102686\n20104662\n", encoding="utf-8")

            runs = run_monthly_pattern_paths.build_monthly_pattern_path_runs(
                selected_dates=["2024-02-23"],
                patient_list_dir=temp_dir,
                config_path="config/settings.yaml",
                log_dir="logs/monthly_pattern_paths",
                query_family=None,
            )

        self.assertEqual([run.patient_id for run in runs], ["20102686", "20104662"])
        self.assertEqual(runs[0].base_date, "2024-02-23")
        self.assertIn("--patterns-from-config", runs[0].command)
        self.assertEqual(
            runs[0].log_path,
            "logs/monthly_pattern_paths/2024-02-23/20102686.log",
        )

    def test_build_patient_file_pattern_path_runs_reads_limited_ids(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            patient_file = Path(temp_dir) / "patients.txt"
            patient_file.write_text(
                "# comment\n20102686\n20104662\n20123188\n",
                encoding="utf-8",
            )

            runs = run_monthly_pattern_paths.build_patient_file_pattern_path_runs(
                patient_ids_file=patient_file,
                patient_limit=2,
                base_date="2026-05-25",
                config_path="config/settings.yaml",
                log_dir="logs/monthly_pattern_paths",
                query_family="training_order",
            )

        self.assertEqual([run.patient_id for run in runs], ["20102686", "20104662"])
        self.assertEqual(runs[0].base_date, "2026-05-25")
        self.assertEqual(runs[0].month, "2026-05")
        self.assertEqual(
            runs[0].command[1:],
            [
                "scripts/build_pattern_paths.py",
                "--source-id",
                "20102686",
                "--patterns-from-config",
                "--base-date",
                "2026-05-25",
                "--config",
                "config/settings.yaml",
                "--query-family",
                "training_order",
            ],
        )
        self.assertEqual(
            runs[0].log_path,
            "logs/monthly_pattern_paths/2026-05-25/20102686.log",
        )

    def test_refresh_patient_lists_keeps_going_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("scripts.run_monthly_pattern_paths.subprocess.run") as mock_run:
                mock_run.side_effect = [
                    Mock(returncode=1),
                    Mock(returncode=0),
                ]

                failures = run_monthly_pattern_paths.refresh_patient_lists(
                    selected_dates=["2024-01-31", "2024-02-23"],
                    config_path="config/settings.yaml",
                    patient_list_dir=temp_dir,
                    dry_run=False,
                    keep_going=True,
                    log_dir=Path(temp_dir) / "logs",
                )

        self.assertEqual(mock_run.call_count, 2)
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]["base_date"], "2024-01-31")

    def test_run_monthly_pattern_paths_keeps_going_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs = [
                run_monthly_pattern_paths.MonthlyPatternPathRun(
                    month="2024-01",
                    base_date="2024-01-31",
                    patient_id="20102686",
                    command=["python", "fail"],
                    log_path=str(Path(temp_dir) / "fail.log"),
                ),
                run_monthly_pattern_paths.MonthlyPatternPathRun(
                    month="2024-02",
                    base_date="2024-02-23",
                    patient_id="20104662",
                    command=["python", "ok"],
                    log_path=str(Path(temp_dir) / "ok.log"),
                ),
            ]

            with patch("scripts.run_monthly_pattern_paths.subprocess.run") as mock_run:
                mock_run.side_effect = [
                    Mock(returncode=1),
                    Mock(returncode=0),
                ]

                result = run_monthly_pattern_paths.run_monthly_pattern_paths(runs)

        self.assertEqual(mock_run.call_count, 2)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["success_count"], 1)

    def test_run_monthly_pattern_paths_dry_run_does_not_call_subprocess(self) -> None:
        runs = [
            run_monthly_pattern_paths.MonthlyPatternPathRun(
                month="2024-02",
                base_date="2024-02-23",
                patient_id="20102686",
                command=["python", "build"],
                log_path="logs/monthly_pattern_paths/2024-02-23/20102686.log",
            )
        ]

        with patch("scripts.run_monthly_pattern_paths.subprocess.run") as mock_run:
            result = run_monthly_pattern_paths.run_monthly_pattern_paths(
                runs,
                dry_run=True,
            )

        mock_run.assert_not_called()
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["successes"][0]["dry_run"], True)


if __name__ == "__main__":
    unittest.main()
