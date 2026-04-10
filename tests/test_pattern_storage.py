"""Tests for offline pattern path storage helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from src.similar_user.utils.pattern_storage import (
    append_pattern_result,
    get_pattern_result_output_path,
)


class PatternStorageTest(unittest.TestCase):
    def test_get_pattern_result_output_path_uses_yaml_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "query.yaml"
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
                        '  output_dir: "custom/output"',
                    ]
                ),
                encoding="utf-8",
            )

            output_path = get_pattern_result_output_path(
                config_path,
                "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            )

        self.assertEqual(
            output_path,
            Path("custom/output/PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT.jsonl"),
        )

    def test_append_pattern_result_writes_jsonl_record(self) -> None:
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

            result = {
                "patient_id": "40",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "paths": [],
            }

            output_path = append_pattern_result(result, config_path)

            self.assertTrue(output_path.exists())
            lines = output_path.read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(lines), 1)
            self.assertEqual(json.loads(lines[0]), result)


if __name__ == "__main__":
    unittest.main()
