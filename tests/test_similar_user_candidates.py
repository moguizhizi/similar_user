"""Tests for similar-user candidate aggregation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.build_similar_user_candidates import (
    build_similar_user_candidates,
    main,
)
from similar_user.services.similarity import SimilarUserCandidateService
from similar_user.utils.pattern_storage import save_pattern_result


class SimilarUserCandidatesTest(unittest.TestCase):
    def test_aggregate_candidates_from_scored_paths_deduplicates_and_sorts(self) -> None:
        valid_row_a = {
            "p": {"id": "30010096"},
            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
            "i1": {"id": "30010096_20220522_348_a", "任务类型": "专属", "结果": "完成"},
            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
            "i2": {"id": "20113562_20211214_348_a", "结果": "完成", "活跃": "是", "任务类型": "专属"},
            "s2": {"id": "20113562_20211214", "执行年龄": "64", "执行学历": "本科"},
            "p2": {"id": "20113562"},
        }
        valid_row_b = {
            "p": {"id": "30010096"},
            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
            "i1": {"id": "30010096_20220522_348_b", "任务类型": "专属", "结果": "完成"},
            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
            "i2": {"id": "20113563_20211214_348_b", "结果": "完成", "活跃": "是", "任务类型": "专属"},
            "s2": {"id": "20113563_20211214", "执行年龄": "65", "执行学历": "本科"},
            "p2": {"id": "20113563"},
        }
        scored_result = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 3,
            "scored_path_count": 3,
            "retrieval_context": {"split_training_date": "2022-01-13"},
            "scores": [
                {
                    "path_index": 2,
                    "score": {"total_score": 88.0},
                    "path": {"row": valid_row_a},
                },
                {
                    "path_index": 0,
                    "score": {"total_score": 95.0},
                    "path": {"row": valid_row_b},
                },
                {
                    "path_index": 1,
                    "score": {"total_score": 90.0},
                    "path": {"row": valid_row_a},
                },
            ],
        }
        mock_user_service = Mock()
        mock_user_service.get_patient_game_norm_score_series_comparison_by_end_date = Mock(
            side_effect=lambda primary, comparison, end_date: [
                {
                    "game": "打怪物",
                    "scores_p1": ["80"],
                    "scores_p2": ["80" if comparison == "20113563" else "100"],
                },
                {
                    "game": "真假句辨别",
                    "scores_p1": ["90"],
                    "scores_p2": ["90"],
                },
                {
                    "game": "空间搜索",
                    "scores_p1": ["100"],
                    "scores_p2": ["95" if comparison == "20113563" else "80"],
                },
            ]
        )
        mock_user_service.get_patient_distinct_games_by_end_date = Mock(
            side_effect=lambda patient_id, end_date: [
                {"g": {"id": "348", "name": "真假句辨别"}},
                {"g": {"id": "777", "name": "空间搜索"}},
            ]
            if patient_id == "20113563"
            else [
                {"g": {"id": "348", "name": "真假句辨别"}},
                {"g": {"id": "999", "name": "打怪物"}},
            ]
            if patient_id == "30010096"
            else [
                {"g": {"id": "348", "name": "真假句辨别"}},
            ]
        )
        mock_user_service.get_patient_disease_set_comparison_by_end_date = Mock(
            side_effect=lambda primary, comparison, end_date: [
                {
                    "diseases1": [
                        {"id": "D1", "name": "疾病1"},
                        {"id": "D2", "name": "疾病2"},
                    ],
                    "diseases2": [{"id": "D1", "name": "疾病1"}],
                }
            ]
        )
        mock_user_service.get_patient_symptom_set_comparison_by_end_date = Mock(
            side_effect=lambda primary, comparison, end_date: [
                {
                    "symptoms1": [{"id": "S1", "name": "症状1"}],
                    "symptoms2": [
                        {"id": "S1", "name": "症状1"},
                        {"id": "S2", "name": "症状2"},
                    ],
                }
            ]
        )
        mock_user_service.get_patient_unknown_set_comparison_by_end_date = Mock(
            side_effect=lambda primary, comparison, end_date: [
                {
                    "unknowns1": [{"id": "U1", "name": "其他1"}],
                    "unknowns2": [{"id": "U2", "name": "其他2"}],
                }
            ]
        )

        result = SimilarUserCandidateService(
            user_service=mock_user_service
        ).aggregate_candidates_from_scored_paths(
            scored_result,
            path_top_k=3,
            candidate_top_k=3,
        )

        self.assertEqual(result["retrieval_context"]["split_training_date"], "2022-01-13")
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["candidates"][0]["patient_id"], "20113563")
        self.assertEqual(result["candidates"][0]["candidate_score"], 0.982)
        self.assertEqual(
            result["candidates"][0]["score_details"]["game_similarity_with_diversity_score"]["score"],
            0.25,
        )
        self.assertEqual(
            result["candidates"][0]["score_details"]["set_same_scores"]["disease"]["score"],
            0.5,
        )
        self.assertEqual(
            result["candidates"][0]["score_details"]["set_same_scores"]["symptom"]["score"],
            0.5,
        )
        self.assertEqual(
            result["candidates"][0]["score_details"]["set_same_scores"]["unknown"]["score"],
            0.0,
        )
        self.assertEqual(result["candidates"][0]["best_score"], 95.0)
        self.assertEqual(result["candidates"][1]["patient_id"], "20113562")
        self.assertAlmostEqual(result["candidates"][1]["candidate_score"], -1.0)
        self.assertEqual(result["candidates"][1]["match_count"], 2)
        self.assertEqual(result["candidates"][1]["path_indices"], [1, 2])
        self.assertEqual(result["candidates"][1]["best_score"], 90.0)
        self.assertEqual(result["candidates"][1]["avg_score"], 89.0)
        self.assertEqual(
            mock_user_service.get_patient_game_norm_score_series_comparison_by_end_date.call_count,
            2,
        )
        self.assertEqual(mock_user_service.get_patient_distinct_games_by_end_date.call_count, 4)
        self.assertEqual(
            mock_user_service.get_patient_disease_set_comparison_by_end_date.call_count,
            2,
        )
        self.assertEqual(
            mock_user_service.get_patient_symptom_set_comparison_by_end_date.call_count,
            2,
        )
        self.assertEqual(
            mock_user_service.get_patient_unknown_set_comparison_by_end_date.call_count,
            2,
        )

    def test_aggregate_candidates_from_scored_paths_raises_for_unsupported_pattern(self) -> None:
        scored_result = {
            "patient_id": "30010096",
            "pattern": "UNSUPPORTED_PATTERN",
            "path_count": 1,
            "scored_path_count": 1,
            "scores": [],
        }

        with self.assertRaisesRegex(ValueError, "Unsupported pattern"):
            SimilarUserCandidateService().aggregate_candidates_from_scored_paths(
                scored_result,
                path_top_k=1,
                candidate_top_k=1,
            )

    def test_aggregate_candidates_from_scored_paths_applies_candidate_top_k(self) -> None:
        def build_row(candidate_id: str) -> dict[str, object]:
            return {
                "p": {"id": "30010096"},
                "s1": {
                    "id": "30010096_20220522",
                    "执行年龄": "66",
                    "执行学历": "本科",
                },
                "i1": {
                    "id": f"30010096_20220522_348_{candidate_id}",
                    "任务类型": "专属",
                    "结果": "完成",
                },
                "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
                "i2": {
                    "id": f"{candidate_id}_20211214_348_a",
                    "结果": "完成",
                    "活跃": "是",
                    "任务类型": "专属",
                },
                "s2": {
                    "id": f"{candidate_id}_20211214",
                    "执行年龄": "64",
                    "执行学历": "本科",
                },
                "p2": {"id": candidate_id},
            }

        scored_result = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 3,
            "scored_path_count": 3,
            "retrieval_context": {"split_training_date": "2022-01-13"},
            "scores": [
                {
                    "path_index": 0,
                    "score": {"total_score": 95.0},
                    "path": {"row": build_row("20113562")},
                },
                {
                    "path_index": 1,
                    "score": {"total_score": 90.0},
                    "path": {"row": build_row("20113563")},
                },
                {
                    "path_index": 2,
                    "score": {"total_score": 85.0},
                    "path": {"row": build_row("20113564")},
                },
            ],
        }
        score_by_candidate = {
            "20113562": ["100", "90", "80"],
            "20113563": ["80", "90", "100"],
            "20113564": ["80", "90", "100"],
        }
        mock_user_service = Mock()
        mock_user_service.get_patient_game_norm_score_series_comparison_by_end_date = Mock(
            side_effect=lambda primary, comparison, end_date: [
                {"game": "打怪物", "scores_p1": ["80"], "scores_p2": [score_by_candidate[comparison][0]]},
                {"game": "真假句辨别", "scores_p1": ["90"], "scores_p2": [score_by_candidate[comparison][1]]},
                {"game": "空间搜索", "scores_p1": ["100"], "scores_p2": [score_by_candidate[comparison][2]]},
            ]
        )
        mock_user_service.get_patient_distinct_games_by_end_date = Mock(
            return_value=[{"g": {"id": "348", "name": "真假句辨别"}}]
        )

        result = SimilarUserCandidateService(
            user_service=mock_user_service
        ).aggregate_candidates_from_scored_paths(
            scored_result,
            path_top_k=3,
            candidate_top_k=2,
        )

        self.assertEqual(result["path_top_k"], 3)
        self.assertEqual(result["candidate_top_k"], 2)
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(
            [candidate["patient_id"] for candidate in result["candidates"]],
            ["20113563", "20113564"],
        )

    def test_aggregate_candidates_from_scored_paths_validates_top_k_values(self) -> None:
        scored_result = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 0,
            "scored_path_count": 0,
            "scores": [],
        }

        with self.assertRaisesRegex(ValueError, "path_top_k"):
            SimilarUserCandidateService().aggregate_candidates_from_scored_paths(
                scored_result,
                path_top_k=0,
                candidate_top_k=1,
            )
        with self.assertRaisesRegex(ValueError, "candidate_top_k"):
            SimilarUserCandidateService().aggregate_candidates_from_scored_paths(
                scored_result,
                path_top_k=1,
                candidate_top_k=0,
            )

    def test_aggregate_candidates_from_scored_paths_skips_paths_without_pattern_candidate(self) -> None:
        valid_row = {
            "p": {"id": "30010096"},
            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
            "i1": {"id": "30010096_20220522_348_x", "任务类型": "专属", "结果": "完成"},
            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
            "i2": {"id": "20113563_20211214_348_x", "结果": "完成", "活跃": "是", "任务类型": "专属"},
            "s2": {"id": "20113563_20211214", "执行年龄": "65", "执行学历": "本科"},
            "p2": {"id": "20113563"},
        }
        scored_result = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 2,
            "scored_path_count": 2,
            "scores": [
                {
                    "path_index": 0,
                    "score": {"total_score": 95.0},
                    "path": {"row": valid_row},
                },
                {
                    "path_index": 1,
                    "score": {"total_score": 90.0},
                    "path": {"row": {}},
                },
            ],
        }

        result = SimilarUserCandidateService().aggregate_candidates_from_scored_paths(
            scored_result,
            path_top_k=2,
            candidate_top_k=2,
        )

        self.assertEqual(result["retrieval_context"]["split_training_date"], None)
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["patient_id"], "20113563")

    def test_build_similar_user_candidates_uses_scored_top_k_paths(self) -> None:
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
                        "candidate_ranking:",
                        "  path_top_k: 3",
                        "  candidate_top_k: 2",
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
                "retrieval_context": {
                    "split_training_date": "2022-01-13",
                    "before_split": {"totalPaths": 20, "gCount": 5, "p2Count": 6},
                    "post_split_games": [],
                    "limit_recommendation": {"per_g": 5, "limit": 10},
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
                },
            }
            save_pattern_result(result, config_path)

            with patch(
                "scripts.build_similar_user_candidates.DEFAULT_CONFIG_PATH",
                config_path,
            ), patch(
                "scripts.build_similar_user_candidates.Neo4jClient.from_config",
            ) as mock_from_config, patch(
                "scripts.build_similar_user_candidates.UserService",
            ) as mock_user_service_cls:
                mock_client_context = Mock()
                mock_client_context.__enter__ = Mock(return_value=Mock())
                mock_client_context.__exit__ = Mock(return_value=None)
                mock_from_config.return_value = mock_client_context
                mock_user_service = Mock()
                mock_user_service.get_patient_game_norm_score_series_comparison_by_end_date.side_effect = (
                    lambda primary, comparison, end_date: [
                        {
                            "game": "打怪物",
                            "scores_p1": ["80"],
                            "scores_p2": ["80" if comparison == "20113562" else "100"],
                        },
                        {
                            "game": "真假句辨别",
                            "scores_p1": ["90"],
                            "scores_p2": ["90"],
                        },
                        {
                            "game": "空间搜索",
                            "scores_p1": ["100"],
                            "scores_p2": ["100" if comparison == "20113562" else "80"],
                        },
                    ]
                )
                mock_user_service.get_patient_distinct_games_by_end_date.return_value = [
                    {"g": {"id": "348", "name": "真假句辨别"}}
                ]
                mock_user_service_cls.return_value = mock_user_service
                candidates = build_similar_user_candidates("30010096")

        self.assertEqual(candidates["candidate_count"], 2)
        self.assertEqual(candidates["retrieval_context"]["split_training_date"], "2022-01-13")
        self.assertEqual(candidates["candidates"][0]["patient_id"], "20113562")
        self.assertEqual(candidates["candidates"][0]["match_count"], 2)
        self.assertEqual(candidates["candidates"][1]["patient_id"], "20113563")

    def test_build_similar_user_candidates_reads_top_k_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "candidate_ranking:",
                        "  path_top_k: 2",
                        "  candidate_top_k: 1",
                    ]
                ),
                encoding="utf-8",
            )
            valid_row = {
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
            scored_result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "path_count": 2,
                "scored_path_count": 1,
                "scores": [
                    {
                        "path_index": 0,
                        "score": {"total_score": 95.0},
                        "path": {"row": valid_row},
                    }
                ],
            }
            with patch(
                "scripts.build_similar_user_candidates.DEFAULT_CONFIG_PATH",
                config_path,
            ), patch(
                "scripts.build_similar_user_candidates.Neo4jClient.from_config",
            ) as mock_from_config, patch(
                "scripts.build_similar_user_candidates.UserService",
            ) as mock_user_service_cls, patch(
                "scripts.build_similar_user_candidates.score_patient_pattern_result",
                return_value=scored_result,
            ) as mock_score:
                mock_client_context = Mock()
                mock_client_context.__enter__ = Mock(return_value=Mock())
                mock_client_context.__exit__ = Mock(return_value=None)
                mock_from_config.return_value = mock_client_context
                mock_user_service = Mock()
                mock_user_service.get_patient_game_norm_score_series_comparison_by_end_date.side_effect = (
                    lambda primary, comparison, end_date: [
                        {"game": "打怪物", "scores_p1": ["80"], "scores_p2": ["80"]},
                        {"game": "真假句辨别", "scores_p1": ["90"], "scores_p2": ["90"]},
                    ]
                )
                mock_user_service.get_patient_distinct_games_by_end_date.return_value = [
                    {"g": {"id": "348", "name": "真假句辨别"}}
                ]
                mock_user_service_cls.return_value = mock_user_service
                candidates = build_similar_user_candidates("30010096")

        self.assertEqual(candidates["path_top_k"], 2)
        self.assertEqual(candidates["candidate_top_k"], 1)
        self.assertEqual(candidates["candidate_count"], 1)
        self.assertEqual(candidates["candidates"][0]["patient_id"], "20113562")
        mock_score.assert_called_once_with(
            "30010096",
            pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            config_path=config_path,
            top_k=2,
        )

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
            "path_top_k": 5,
            "candidate_top_k": 2,
            "path_count": 10,
            "scored_path_count": 5,
            "retrieval_context": {
                "split_training_date": "2022-01-13",
                "candidate_scope": "候选相似用户来自训练日期小于等于 2022-01-13 的 top-5 path 去重结果，最终返回 top-2 候选用户",
            },
            "candidate_count": 2,
            "candidates": [{"patient_id": "20113562"}],
        }
        mock_parse_args.return_value = Mock(
            patient_id="30010096",
            pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
        )
        mock_build_candidates.return_value = expected

        exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_logger.info.assert_called_once_with(
            json.dumps(expected, ensure_ascii=False, indent=2, default=str)
        )


if __name__ == "__main__":
    unittest.main()
