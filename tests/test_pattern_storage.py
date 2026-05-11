"""Tests for offline pattern path storage helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.similar_user.utils.pattern_storage import (
    PatternResultStore,
    StoredPatternResult,
    get_pattern_result_output_path,
    get_pattern_result_output_dir,
    save_pattern_result,
)


class PatternStorageTest(unittest.TestCase):
    def test_get_pattern_result_output_dir_uses_yaml_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
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

    def test_get_pattern_result_output_dir_accepts_pattern_alias(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "pattern_path_storage:",
                        '  output_dir: "custom/output"',
                    ]
                ),
                encoding="utf-8",
            )

            output_dir = get_pattern_result_output_dir(
                config_path,
                "patient_game_patient",
            )

        self.assertEqual(
            output_dir,
            Path("custom/output/PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"),
        )

    def test_get_pattern_result_output_path_uses_bucketed_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
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

            output_path = get_pattern_result_output_path(
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
            config_path = Path(temp_dir) / "settings.yaml"
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
            expected_loaded_result = {
                "source_id": "30010096",
                "source_parameter": "patient_id",
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "retrieval_context": {
                    "split_training_date": None,
                    "before_split": {},
                    "post_split_games": [],
                    "limit_recommendation": None,
                    "paths": [{"g": 2}],
                },
            }

            output_path = save_pattern_result(first_result, config_path)
            save_pattern_result(second_result, config_path)
            store = PatternResultStore(config_path)

            self.assertTrue(output_path.exists())
            loaded_result = store.load(second_result["pattern"], "30010096")

            self.assertIsInstance(loaded_result, StoredPatternResult)
            self.assertEqual(loaded_result.to_dict(), expected_loaded_result)

    def test_save_pattern_result_writes_semantic_source_id_field(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            output_dir = Path(temp_dir) / "pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )

            result = {
                "source_id": "AU_DIS_0013",
                "source_parameter": "disease_id",
                "disease_id": "AU_DIS_0013",
                "pattern": "DISEASE_TASKSET_PATIENT",
                "retrieval_context": {
                    "paths": [
                        {
                            "row": {
                                "d": {"id": "AU_DIS_0013"},
                                "s": {"id": "40_20220516"},
                                "p": {"id": "40"},
                            }
                        }
                    ]
                },
            }

            output_path = save_pattern_result(result, config_path)
            store = PatternResultStore(config_path)
            loaded_result = store.load("disease_patient", "AU_DIS_0013")
            alias_output_path = get_pattern_result_output_path(
                config_path,
                "disease_patient",
                "AU_DIS_0013",
            )

        self.assertEqual(
            output_path,
            output_dir / "DISEASE_TASKSET_PATIENT" / "AU" / "AU_DIS_0013.json",
        )
        self.assertEqual(alias_output_path, output_path)
        self.assertEqual(loaded_result.source_id, "AU_DIS_0013")
        self.assertEqual(loaded_result.source_parameter, "disease_id")
        self.assertIsNone(loaded_result.patient_id)
        self.assertEqual(loaded_result.to_dict()["disease_id"], "AU_DIS_0013")

    def test_iter_pattern_results_reads_multiple_patient_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
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
        self.assertTrue(all(isinstance(record, StoredPatternResult) for record in records))
        self.assertEqual(
            {record.patient_id for record in records},
            {"30010096", "19000001"},
        )
        self.assertEqual(
            {record.source_id for record in records},
            {"30010096", "19000001"},
        )


if __name__ == "__main__":
    unittest.main()
