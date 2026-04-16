"""Tests for reading stored patient pattern path results."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.read_patient_pattern_result import main, read_patient_pattern_result
from similar_user.domain import GameNode
from similar_user.utils.pattern_storage import (
    StoredPatternResult,
    StoredPatternStatistics,
    StoredTrainingDateGames,
    save_pattern_result,
)


class ReadPatientPatternResultScriptTest(unittest.TestCase):
    def test_read_patient_pattern_result_returns_typed_result(self) -> None:
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
            expected_result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "ordered_training_dates": ["2022-01-01", "2022-01-13"],
                "first_training_date": "2022-01-01",
                "last_training_date": "2022-01-13",
                "training_date_count": 2,
                "retrieval_context": None,
            }
            save_pattern_result(expected_result, config_path)

            loaded_result = read_patient_pattern_result(
                "30010096",
                pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                config_path=config_path,
            )

        self.assertIsInstance(loaded_result, StoredPatternResult)
        self.assertEqual(loaded_result.to_dict(), expected_result)

    @patch("scripts.read_patient_pattern_result.LOGGER")
    @patch("scripts.read_patient_pattern_result.parse_args")
    def test_main_logs_loaded_result_json(
        self,
        mock_parse_args: Mock,
        mock_logger: Mock,
    ) -> None:
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
            expected_result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "retrieval_context": None,
            }
            save_pattern_result(expected_result, config_path)
            mock_parse_args.return_value = Mock(
                patient_id="30010096",
                pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                config=str(config_path),
            )

            exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_logger.info.assert_called_once_with(
            json.dumps(expected_result, ensure_ascii=False, indent=2, default=str)
        )

    def test_stored_pattern_result_can_convert_paths_to_domain_objects(self) -> None:
        result = StoredPatternResult.from_dict(
            {
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
                    "paths": [
                        {
                            "row": {
                                "p": {"id": "30010096", "name": "患者_30010096"},
                                "s1": {"id": "30010096_20220113", "训练日期": "2022-01-13"},
                                "i1": {"id": "30010096_20220113_42_x"},
                                "g": {"id": "42", "name": "打怪物"},
                                "i2": {"id": "20113562_20211214_42_y"},
                                "s2": {"id": "20113562_20211214", "训练日期": "2021-12-14"},
                                "p2": {"id": "20113562", "name": "患者_20113562"},
                            }
                        }
                    ],
                },
            }
        )

        domain_paths = result.to_domain_paths()

        self.assertEqual(len(domain_paths), 1)
        self.assertEqual(domain_paths[0].p.id, "30010096")
        self.assertEqual(domain_paths[0].g.name, "打怪物")
        self.assertEqual(domain_paths[0].s2.训练日期, "2021-12-14")

    def test_stored_pattern_result_can_convert_disease_paths_to_domain_objects(
        self,
    ) -> None:
        result = StoredPatternResult.from_dict(
            {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "retrieval_context": {
                    "split_training_date": None,
                    "before_split": {},
                    "post_split_games": [],
                    "limit_recommendation": None,
                    "paths": [
                        {
                            "row": {
                                "p": {"id": "30010096", "name": "患者_30010096"},
                                "s1": {"id": "30010096_20220113", "训练日期": "2022-01-13"},
                                "dis": {
                                    "id": "AU_DIS_0013",
                                    "name": "遗忘型轻度认知障碍",
                                },
                                "s2": {"id": "20113562_20211214", "训练日期": "2021-12-14"},
                                "p2": {"id": "20113562", "name": "患者_20113562"},
                            }
                        }
                    ],
                },
            }
        )

        domain_paths = result.to_domain_paths()

        self.assertEqual(len(domain_paths), 1)
        self.assertEqual(domain_paths[0].p.id, "30010096")
        self.assertEqual(domain_paths[0].dis.name, "遗忘型轻度认知障碍")
        self.assertEqual(domain_paths[0].p2.id, "20113562")

    def test_stored_pattern_result_can_convert_symptom_paths_to_domain_objects(
        self,
    ) -> None:
        result = StoredPatternResult.from_dict(
            {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "retrieval_context": {
                    "split_training_date": None,
                    "before_split": {},
                    "post_split_games": [],
                    "limit_recommendation": None,
                    "paths": [
                        {
                            "row": {
                                "p": {"id": "30010096", "name": "患者_30010096"},
                                "s1": {"id": "30010096_20220113", "训练日期": "2022-01-13"},
                                "sym": {
                                    "id": "AU_SYM_0007",
                                    "name": "睡眠障碍",
                                },
                                "s2": {"id": "20113562_20211214", "训练日期": "2021-12-14"},
                                "p2": {"id": "20113562", "name": "患者_20113562"},
                            }
                        }
                    ],
                },
            }
        )

        domain_paths = result.to_domain_paths()

        self.assertEqual(len(domain_paths), 1)
        self.assertEqual(domain_paths[0].p.id, "30010096")
        self.assertEqual(domain_paths[0].sym.name, "睡眠障碍")
        self.assertEqual(domain_paths[0].p2.id, "20113562")

    def test_stored_pattern_result_can_convert_statistics_to_typed_object(self) -> None:
        result = StoredPatternResult.from_dict(
            {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "ordered_training_dates": ["2022-05-01", "2022-05-22"],
                "first_training_date": "2022-05-01",
                "last_training_date": "2022-05-22",
                "training_date_count": 2,
                "retrieval_context": {
                    "split_training_date": "2022-05-22",
                    "before_split": {"totalPaths": 10, "gCount": 4, "p2Count": 3},
                    "post_split_games": [
                        {
                            "trainingDate": "2022-05-22",
                            "games": [
                                {"name": "数字筛选•进阶", "id": "41"},
                                {"name": "大浪淘沙", "id": "48"},
                            ],
                        }
                    ],
                    "limit_recommendation": None,
                    "paths": [],
                },
            }
        )

        self.assertIsInstance(result.statistics, dict)
        statistics = result.to_stored_statistics()

        self.assertIsInstance(statistics, StoredPatternStatistics)
        assert statistics is not None
        self.assertIsInstance(
            statistics.post_split_games[0],
            StoredTrainingDateGames,
        )
        self.assertIsInstance(
            statistics.post_split_games[0].games[0],
            GameNode,
        )
        self.assertEqual(
            statistics.post_split_games[0].training_date,
            "2022-05-22",
        )
        self.assertEqual(
            statistics.post_split_games[0].games[0].name,
            "数字筛选•进阶",
        )
        self.assertEqual(
            result.to_dict()["retrieval_context"]["post_split_games"][0]["games"][1]["id"],
            "48",
        )


if __name__ == "__main__":
    unittest.main()
