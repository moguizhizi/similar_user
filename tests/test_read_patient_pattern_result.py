"""Tests for reading stored patient pattern path results."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.read_patient_pattern_result import main, read_patient_pattern_result
from similar_user.utils.pattern_storage import (
    StoredPatternResult,
    save_pattern_result,
)


class ReadPatientPatternResultScriptTest(unittest.TestCase):
    def test_read_patient_pattern_result_returns_typed_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "query.yaml"
            output_dir = Path(temp_dir) / "pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "training_date_split:",
                        "  min_training_dates: 5",
                        "  before_ratio: 4",
                        "  after_ratio: 1",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            expected_result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "ordered_training_dates": ["2022-01-01", "2022-01-13"],
                "first_training_date": "2022-01-01",
                "last_training_date": "2022-01-13",
                "training_date_count": 2,
                "statistics": None,
                "limit_recommendation": None,
                "paths": [],
            }
            save_pattern_result(expected_result, config_path)

            loaded_result = read_patient_pattern_result(
                "30010096",
                pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                query_config_path=config_path,
            )

        self.assertIsInstance(loaded_result, StoredPatternResult)
        self.assertEqual(loaded_result.to_dict(), expected_result)

    @patch("scripts.read_patient_pattern_result.parse_args")
    @patch("builtins.print")
    def test_main_prints_loaded_result_json(
        self,
        mock_print: Mock,
        mock_parse_args: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "query.yaml"
            output_dir = Path(temp_dir) / "pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "training_date_split:",
                        "  min_training_dates: 5",
                        "  before_ratio: 4",
                        "  after_ratio: 1",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            expected_result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "statistics": None,
                "limit_recommendation": None,
                "paths": [],
            }
            save_pattern_result(expected_result, config_path)
            mock_parse_args.return_value = Mock(
                patient_id="30010096",
                pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                query_config=str(config_path),
            )

            exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_print.assert_called_once_with(
            json.dumps(expected_result, ensure_ascii=False, indent=2, default=str)
        )


if __name__ == "__main__":
    unittest.main()
