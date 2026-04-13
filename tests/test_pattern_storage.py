"""Tests for offline pattern path storage helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.similar_user.utils.pattern_storage import (
    PatternResultStore,
    get_patient_pattern_result_output_path,
    get_pattern_result_output_dir,
    save_pattern_result,
)


class PatternStorageTest(unittest.TestCase):
    def test_get_pattern_result_output_dir_uses_yaml_config(self) -> None:
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

            output_dir = get_pattern_result_output_dir(
                config_path,
                "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            )

        self.assertEqual(
            output_dir,
            Path("custom/output/PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"),
        )

    def test_get_patient_pattern_result_output_path_uses_bucketed_layout(self) -> None:
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

            output_path = get_patient_pattern_result_output_path(
                config_path,
                "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "30010096",
            )

        self.assertEqual(
            output_path,
            output_dir
            / "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"
            / "30"
            / "30010096.json",
        )

    def test_save_pattern_result_overwrites_same_patient_file(self) -> None:
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

            first_result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "paths": [{"g": 1}],
            }
            second_result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "paths": [{"g": 2}],
            }

            output_path = save_pattern_result(first_result, config_path)
            save_pattern_result(second_result, config_path)
            store = PatternResultStore(config_path)

            self.assertTrue(output_path.exists())
            self.assertEqual(store.load(second_result["pattern"], "30010096"), second_result)

    def test_iter_pattern_results_reads_multiple_patient_files(self) -> None:
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

            pattern = "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"
            save_pattern_result(
                {"patient_id": "30010096", "pattern": pattern, "paths": []},
                config_path,
            )
            save_pattern_result(
                {"patient_id": "19000001", "pattern": pattern, "paths": [{"g": 1}]},
                config_path,
            )

            store = PatternResultStore(config_path)
            records = list(store.iter_pattern_results(pattern))

        self.assertEqual(len(records), 2)
        self.assertEqual(
            {record["patient_id"] for record in records},
            {"30010096", "19000001"},
        )


if __name__ == "__main__":
    unittest.main()
