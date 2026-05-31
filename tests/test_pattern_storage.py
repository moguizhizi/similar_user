"""Tests for offline pattern path storage helpers."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src.similar_user.data_access.user_cache_index import UserCacheIndexStore
from src.similar_user.utils.pattern_storage import (
    PatternResultStore,
    StoredPatternResult,
    build_direct_path_cache_context,
    build_path_key,
    build_raw_path_user_cache_config_hash,
    get_pattern_result_output_dir,
    get_pattern_result_output_path,
    save_pattern_result,
    save_direct_pattern_result,
)


def _retrieval_context(paths: list[dict[str, object]] | None = None) -> dict[str, object]:
    return {
        "base_date": "2024-01-31",
        "query_family": "training_order_source_window",
        "path_window": {
            "start_date": "2024-01-17",
            "end_date": "2024-01-31",
        },
        "paths": [] if paths is None else paths,
    }


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
                        "pattern_path_storage:",
                        '  output_dir: "custom/output"',
                    ]
                ),
                encoding="utf-8",
            )
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )

            output_dir = get_pattern_result_output_dir(
                config_path,
                "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                path_key=path_key,
            )

        self.assertEqual(
            output_dir,
            Path("custom/output")
            / path_key
            / "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
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
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )

            output_dir = get_pattern_result_output_dir(
                config_path,
                "patient_game_patient",
                path_key=path_key,
            )

        self.assertEqual(
            output_dir,
            Path("custom/output")
            / path_key
            / "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
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
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )

            output_path = get_pattern_result_output_path(
                config_path,
                "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "30010096",
                path_key=path_key,
            )

        self.assertEqual(
            output_path,
            output_dir
            / path_key
            / "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"
            / "30"
            / "30010096.json",
        )

    def test_get_pattern_result_output_path_requires_path_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(["graph_path_limit:", "  bands:", "    - per_g: 1"]),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "path_key"):
                get_pattern_result_output_path(
                    config_path,
                    "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                    "30010096",
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
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            first_result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "retrieval_context": _retrieval_context([{"g": 1}]),
            }
            second_result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "retrieval_context": _retrieval_context([{"g": 2}]),
            }
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )
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
                    "before_split": None,
                    "post_split_games": [],
                    "limit_recommendation": None,
                    "base_date": "2024-01-31",
                    "query_family": "training_order_source_window",
                    "path_window": {
                        "start_date": "2024-01-17",
                        "end_date": "2024-01-31",
                    },
                    "paths": [{"g": 2}],
                    "cache_context": {
                        "cache_type": "pattern_paths",
                        "path_key": path_key,
                        "base_date": "2024-01-31",
                        "window_days": 14,
                        "query_family": "training_order_source_window",
                        "path_config_hash": path_key.rsplit("_", 1)[-1],
                        "path_config": {
                            "graph_path_limit": {
                                "bands": [{"max_g_count": None, "per_g": 1}],
                                "max_limit_source": "total_paths",
                                "per_g_strategy": "band",
                            }
                        },
                    },
                },
            }

            output_path = save_pattern_result(first_result, config_path)
            save_pattern_result(second_result, config_path)
            loaded_result = PatternResultStore(config_path).load(
                second_result["pattern"],
                "30010096",
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )
            output_exists = output_path.exists()

        self.assertTrue(output_exists)
        self.assertIn(path_key, str(output_path))
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
                    "base_date": "2024-01-31",
                    "query_family": None,
                    "path_window": {
                        "start_date": "2024-01-17",
                        "end_date": "2024-01-31",
                    },
                    "paths": [
                        {
                            "row": {
                                "d": {"id": "AU_DIS_0013"},
                                "s": {"id": "40_20220516"},
                                "p": {"id": "40"},
                            }
                        }
                    ],
                },
            }
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family=None,
            )

            output_path = save_pattern_result(result, config_path)
            loaded_result = PatternResultStore(config_path).load(
                "disease_patient",
                "AU_DIS_0013",
                base_date="2024-01-31",
                query_family=None,
            )
            alias_output_path = get_pattern_result_output_path(
                config_path,
                "disease_patient",
                "AU_DIS_0013",
                path_key=path_key,
            )

        self.assertEqual(
            output_path,
            output_dir
            / path_key
            / "DISEASE_TASKSET_PATIENT"
            / "AU"
            / "AU_DIS_0013.json",
        )
        self.assertEqual(alias_output_path, output_path)
        self.assertEqual(loaded_result.source_id, "AU_DIS_0013")
        self.assertEqual(loaded_result.source_parameter, "disease_id")
        self.assertIsNone(loaded_result.patient_id)
        self.assertEqual(loaded_result.to_dict()["disease_id"], "AU_DIS_0013")

    def test_save_pattern_result_requires_path_cache_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(["graph_path_limit:", "  bands:", "    - per_g: 1"]),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "base_date"):
                save_pattern_result(
                    {
                        "patient_id": "30010096",
                        "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                        "paths": [],
                    },
                    config_path,
                )

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
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            pattern = "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"
            save_pattern_result(
                {
                    "patient_id": "30010096",
                    "pattern": pattern,
                    "retrieval_context": _retrieval_context(),
                },
                config_path,
            )
            save_pattern_result(
                {
                    "patient_id": "19000001",
                    "pattern": pattern,
                    "retrieval_context": _retrieval_context([{"g": 1}]),
                },
                config_path,
            )
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )

            records = list(
                PatternResultStore(config_path).iter_pattern_results(
                    pattern,
                    path_key=path_key,
                )
            )

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

    def test_save_pattern_result_uses_windowed_path_key(self) -> None:
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
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "retrieval_context": _retrieval_context(),
            }
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )

            output_path = save_pattern_result(result, config_path)
            loaded_result = PatternResultStore(config_path).load(
                result["pattern"],
                "30010096",
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )

        self.assertEqual(
            output_path,
            output_dir
            / path_key
            / "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"
            / "30"
            / "30010096.json",
        )
        self.assertEqual(
            loaded_result.retrieval_context["cache_context"]["path_key"],
            path_key,
        )

    def test_save_pattern_result_registers_raw_path_user_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "settings.yaml"
            output_dir = root / "pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "patient_path:",
                        "  window_days: 14",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                        "user_cache:",
                        "  enabled: true",
                        f'  sqlite_path: "{root / "user_cache" / "cache_index.sqlite"}"',
                        "  patient_raw_paths_valid_days: 30",
                        "  direct_raw_paths_valid_days: 60",
                    ]
                ),
                encoding="utf-8",
            )
            result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "retrieval_context": _retrieval_context(),
            }

            output_path = save_pattern_result(result, config_path)
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )
            found = UserCacheIndexStore(
                root / "user_cache" / "cache_index.sqlite"
            ).find_latest_valid_source_entry(
                cache_type="raw_paths",
                source_type="patient",
                source_id="30010096",
                query_family="training_order_source_window",
                window_days=14,
                config_hash=build_raw_path_user_cache_config_hash(path_key),
                request_base_date="2024-02-03",
            )

        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.cached_base_date, "2024-01-31")
        self.assertEqual(found.valid_days, 30)
        self.assertEqual(found.data_path, str(output_path))
        self.assertEqual(found.payload["path_key"], path_key)

    def test_save_direct_pattern_result_registers_source_raw_path_user_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "settings.yaml"
            output_dir = root / "pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                        "user_cache:",
                        "  enabled: true",
                        f'  sqlite_path: "{root / "user_cache" / "cache_index.sqlite"}"',
                        "  patient_raw_paths_valid_days: 30",
                        "  direct_raw_paths_valid_days: 60",
                    ]
                ),
                encoding="utf-8",
            )
            path_context = build_direct_path_cache_context(
                base_date="2024-01-31",
                window_days=90,
                direct_path_limit=50,
            )
            result = {
                "source_id": "AU_DIS_0029",
                "source_parameter": "disease_id",
                "disease_id": "AU_DIS_0029",
                "pattern": "DISEASE_TASKSET_PATIENT",
                "retrieval_context": _retrieval_context(),
            }

            output_path = save_direct_pattern_result(
                result,
                config_path,
                path_context=path_context,
            )
            found = UserCacheIndexStore(
                root / "user_cache" / "cache_index.sqlite"
            ).find_latest_valid_source_entry(
                cache_type="raw_paths",
                source_type="disease",
                source_id="AU_DIS_0029",
                query_family="direct_entity",
                window_days=90,
                config_hash=build_raw_path_user_cache_config_hash(
                    str(path_context["path_key"])
                ),
                request_base_date="2024-02-03",
            )

        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.valid_days, 60)
        self.assertEqual(found.data_path, str(output_path))
        self.assertEqual(found.payload["path_key"], path_context["path_key"])


if __name__ == "__main__":
    unittest.main()
