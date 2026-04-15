"""Tests for similar-user candidate aggregation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.build_similar_user_candidates import (
    aggregate_candidates_from_scored_paths,
    build_similar_user_candidates,
    main,
)
from src.similar_user.utils.pattern_storage import save_pattern_result


class SimilarUserCandidatesTest(unittest.TestCase):
    def test_aggregate_candidates_from_scored_paths_deduplicates_and_sorts(self) -> None:
        scored_result = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 3,
            "scored_path_count": 3,
            "scores": [
                {
                    "path_index": 2,
                    "score": {"total_score": 88.0},
                    "path": {"row": {"p2": {"id": "20113562"}}},
                },
                {
                    "path_index": 0,
                    "score": {"total_score": 95.0},
                    "path": {"row": {"p2": {"id": "20113563"}}},
                },
                {
                    "path_index": 1,
                    "score": {"total_score": 90.0},
                    "path": {"row": {"p2": {"id": "20113562"}}},
                },
            ],
        }

        result = aggregate_candidates_from_scored_paths(scored_result, top_k=3)

        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["candidates"][0]["patient_id"], "20113563")
        self.assertEqual(result["candidates"][0]["best_score"], 95.0)
        self.assertEqual(result["candidates"][1]["patient_id"], "20113562")
        self.assertEqual(result["candidates"][1]["match_count"], 2)
        self.assertEqual(result["candidates"][1]["path_indices"], [1, 2])
        self.assertEqual(result["candidates"][1]["best_score"], 90.0)
        self.assertEqual(result["candidates"][1]["avg_score"], 89.0)

    def test_aggregate_candidates_from_scored_paths_raises_for_unsupported_pattern(self) -> None:
        scored_result = {
            "patient_id": "30010096",
            "pattern": "UNSUPPORTED_PATTERN",
            "path_count": 1,
            "scored_path_count": 1,
            "scores": [],
        }

        with self.assertRaisesRegex(ValueError, "Unsupported pattern"):
            aggregate_candidates_from_scored_paths(scored_result, top_k=1)

    def test_aggregate_candidates_from_scored_paths_skips_paths_without_pattern_candidate(self) -> None:
        scored_result = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 2,
            "scored_path_count": 2,
            "scores": [
                {
                    "path_index": 0,
                    "score": {"total_score": 95.0},
                    "path": {"row": {"p2": {"id": "20113563"}}},
                },
                {
                    "path_index": 1,
                    "score": {"total_score": 90.0},
                    "path": {"row": {}},
                },
            ],
        }

        result = aggregate_candidates_from_scored_paths(scored_result, top_k=2)

        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["patient_id"], "20113563")

    def test_build_similar_user_candidates_uses_scored_top_k_paths(self) -> None:
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
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "statistics": None,
                "limit_recommendation": None,
                "paths": [
                    {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
                            "i1": {"id": "30010096_20220522_348_a", "任务类型": "专属", "结果": "完成"},
                            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
                            "i2": {
                                "id": "20113562_20211214_348_a",
                                "结果": "完成",
                                "活跃": "是",
                                "任务类型": "专属",
                            },
                            "s2": {"id": "20113562_20211214", "执行年龄": "64", "执行学历": "本科"},
                            "p2": {"id": "20113562"},
                        }
                    },
                    {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
                            "i1": {"id": "30010096_20220522_348_b", "任务类型": "专属", "结果": "完成"},
                            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
                            "i2": {
                                "id": "20113563_20211214_348_b",
                                "结果": "未完成",
                                "活跃": "否",
                                "任务类型": "自由",
                            },
                            "s2": {"id": "20113563_20211214", "执行年龄": "88", "执行学历": "小学"},
                            "p2": {"id": "20113563"},
                        }
                    },
                    {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
                            "i1": {"id": "30010096_20220522_348_c", "任务类型": "专属", "结果": "完成"},
                            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
                            "i2": {
                                "id": "20113562_20211215_348_c",
                                "结果": "完成",
                                "活跃": "是",
                                "任务类型": "专属",
                            },
                            "s2": {"id": "20113562_20211215", "执行年龄": "65", "执行学历": "本科"},
                            "p2": {"id": "20113562"},
                        }
                    },
                ],
            }
            save_pattern_result(result, config_path)

            candidates = build_similar_user_candidates(
                "30010096",
                top_k=3,
                query_config_path=config_path,
            )

        self.assertEqual(candidates["candidate_count"], 2)
        self.assertEqual(candidates["candidates"][0]["patient_id"], "20113562")
        self.assertEqual(candidates["candidates"][0]["match_count"], 2)
        self.assertEqual(candidates["candidates"][1]["patient_id"], "20113563")

    @patch("scripts.build_similar_user_candidates.LOGGER")
    @patch("scripts.build_similar_user_candidates.parse_args")
    @patch("scripts.build_similar_user_candidates.build_similar_user_candidates")
    def test_main_logs_candidate_result(
        self,
        mock_build_candidates: Mock,
        mock_parse_args: Mock,
        mock_logger: Mock,
    ) -> None:
        expected = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "top_k": 5,
            "path_count": 10,
            "scored_path_count": 5,
            "candidate_count": 2,
            "candidates": [{"patient_id": "20113562"}],
        }
        mock_parse_args.return_value = Mock(
            patient_id="30010096",
            top_k=5,
            pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            query_config="config/query.yaml",
        )
        mock_build_candidates.return_value = expected

        exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_logger.info.assert_called_once_with(
            json.dumps(expected, ensure_ascii=False, indent=2, default=str)
        )


if __name__ == "__main__":
    unittest.main()
