"""Tests for similar-user candidate aggregation."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import ANY, Mock, patch

from config.settings import (
    CandidateScoringSettings,
    SetSameScoringSettings,
    load_query_settings,
)
from scripts.build_similar_user_candidates import (
    build_candidate_cache_context,
    build_direct_entity_candidate_cache_context,
    build_direct_entity_scored_key,
    build_direct_entity_topk_candidate_user_cache_context,
    build_topk_candidate_user_cache_context,
    build_similar_user_candidate_summary,
    build_similar_user_candidates as _build_similar_user_candidates,
    classify_skipped_scored_patterns,
    load_cached_topk_candidate_result,
    load_saved_direct_entity_scored_results,
    load_saved_scored_pattern_result,
    main,
    save_similar_user_candidates_result,
)
from scripts.score_pattern_paths import (
    build_scored_path_user_cache_context,
    build_scored_key,
    save_scored_pattern_result as _save_scored_pattern_result,
)
from scripts.run_similar_user_pipeline import (
    EmptyPathResultsError,
    _build_patient_candidates_with_auto_refresh,
    _build_patient_raw_paths_with_limit,
    main as pipeline_main,
    run_similar_user_pipeline,
    summarize_pipeline_result,
)
from similar_user.data_access.user_cache_index import UserCacheEntry, UserCacheIndexStore
from similar_user.services.similarity import SimilarUserCandidateService
from similar_user.utils.pattern_storage import build_path_key, save_pattern_result


def _cache_kwargs() -> dict[str, object]:
    return {
        "base_date": "2024-01-31",
        "window_days": 14,
        "query_family": "training_order_source_window",
    }


def _scored_cache_context(output_dir: str | Path) -> dict[str, object]:
    config_path = Path(output_dir).parent / "settings.yaml"
    score_top_k = load_query_settings(config_path).score_pattern_paths.top_k
    path_key = build_path_key(
        config_path,
        base_date="2024-01-31",
        query_family="training_order_source_window",
    )
    return {
        "cache_type": "scored_pattern_paths",
        "path_key": path_key,
        "scored_key": build_scored_key(path_key, score_top_k),
        "score_top_k": score_top_k,
    }


def save_scored_pattern_result(
    result: dict[str, object],
    output_dir: str | Path,
) -> dict[str, Path]:
    if not isinstance(result.get("cache_context"), dict):
        result = {**result, "cache_context": _scored_cache_context(output_dir)}
    return _save_scored_pattern_result(result, output_dir)


def build_similar_user_candidates(*args: object, **kwargs: object) -> dict[str, object]:
    kwargs.setdefault("base_date", "2024-01-31")
    kwargs.setdefault("query_family", "training_order_source_window")
    return _build_similar_user_candidates(*args, **kwargs)


class SimilarUserCandidatesTest(unittest.TestCase):
    def test_build_direct_entity_scored_key_slugs_base_date(self) -> None:
        self.assertEqual(
            build_direct_entity_scored_key(
                base_date="2024/01/31",
                score_top_k=50,
            ),
            "base_2024-01-31_qf_direct_entity_scoretopk_50",
        )

    def test_classify_skipped_scored_patterns_uses_empty_raw_path_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "patient_path:",
                        "  window_days: 14",
                        "score_pattern_paths:",
                        "  top_k: 150",
                        "user_cache:",
                        "  enabled: true",
                        f'  sqlite_path: "{root / "user_cache" / "cache_index.sqlite"}"',
                    ]
                ),
                encoding="utf-8",
            )
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )
            scored_key = build_scored_key(path_key, 150)
            save_pattern_result(
                {
                    "patient_id": "30010096",
                    "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                    "retrieval_context": {
                        "base_date": "2024-01-31",
                        "query_family": "training_order_source_window",
                        "path_window": {
                            "start_date": "2024-01-17",
                            "end_date": "2024-01-31",
                        },
                        "paths": [],
                    },
                },
                config_path,
            )

            empty_raw_patterns, refresh_patterns = classify_skipped_scored_patterns(
                config_path,
                patient_id="30010096",
                patterns=("patient_game_patient", "patient_disease_patient"),
                scored_key=scored_key,
                request_base_date="2024-01-31",
            )

        self.assertEqual(
            empty_raw_patterns,
            ["PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"],
        )
        self.assertEqual(
            refresh_patterns,
            ["PATIENT_TASKSET_DISEASE_TASKSET_PATIENT"],
        )

    @patch("similar_user.services.similarity.candidate_service.LOGGER")
    def test_aggregate_candidates_from_scored_paths_deduplicates_and_sorts(
        self,
        mock_logger: Mock,
    ) -> None:
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
            "source_id": "30010096",
            "source_parameter": "patient_id",
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
        mock_user_service.get_patient_game_set_comparison_by_end_date = Mock(
            side_effect=lambda primary, comparison, end_date: [
                {
                    "games1": [
                        {"id": "348", "name": "真假句辨别"},
                        {"id": "999", "name": "打怪物"},
                    ],
                    "games2": [
                        {"id": "348", "name": "真假句辨别"},
                        {"id": "777", "name": "空间搜索"},
                    ]
                    if comparison == "20113563"
                    else [{"id": "348", "name": "真假句辨别"}],
                }
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
            candidate_top_k=3,
        )

        self.assertEqual(result["retrieval_context"]["score_end_date"], "2022-01-13")
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["pre_score_candidate_count"], 2)
        self.assertEqual(result["disease_course_available_count"], 0)
        self.assertEqual(result["disease_course_missing_count"], 0)
        self.assertEqual(result["candidates"][0]["patient_id"], "20113563")
        self.assertEqual(result["candidates"][0]["candidate_score"], 2.25)
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
        self.assertEqual(
            result["candidates"][0]["score_details"]["set_same_scores"]["score"],
            1.0,
        )
        self.assertEqual(result["candidates"][0]["best_score"], 95.0)
        self.assertEqual(result["candidates"][1]["patient_id"], "20113562")
        self.assertAlmostEqual(result["candidates"][1]["candidate_score"], 1.984)
        self.assertEqual(result["candidates"][1]["match_count"], 2)
        self.assertNotIn("path_indices", result["candidates"][1])
        self.assertEqual(result["candidates"][1]["best_score"], 90.0)
        self.assertEqual(result["candidates"][1]["avg_score"], 89.0)
        self.assertEqual(
            mock_user_service.get_patient_game_norm_score_series_comparison_by_end_date.call_count,
            2,
        )
        self.assertEqual(
            mock_user_service.get_patient_game_set_comparison_by_end_date.call_count,
            2,
        )
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
        mock_logger.info.assert_any_call(
            "Prepared similar-user candidate buckets before scoring: source_id=%s, source_parameter=%s, scored_path_count=%s, pre_score_candidate_count=%s, candidate_top_k=%s",
            "30010096",
            "patient_id",
            3,
            2,
            3,
        )

    def test_calculate_candidate_score_uses_enabled_scoring_components_only(self) -> None:
        mock_user_service = Mock()
        mock_user_service.get_patient_game_norm_score_series_comparison_by_end_date = Mock(
            return_value=[]
        )
        mock_user_service.get_patient_game_set_comparison_by_end_date = Mock(
            return_value=[
                {
                    "games1": [
                        {"id": "G1", "name": "游戏1"},
                        {"id": "G2", "name": "游戏2"},
                    ],
                    "games2": [
                        {"id": "G1", "name": "游戏1"},
                        {"id": "G3", "name": "游戏3"},
                    ],
                }
            ]
        )
        mock_user_service.get_patient_disease_set_comparison_by_end_date = Mock(
            return_value=[
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
            return_value=[]
        )
        mock_user_service.get_patient_unknown_set_comparison_by_end_date = Mock(
            return_value=[]
        )

        candidate_score, score_details = SimilarUserCandidateService(
            user_service=mock_user_service
        ).calculate_candidate_score(
            primary_patient_id="30010096",
            candidate_patient_id="20113562",
            end_date="2022-01-13",
            scoring_settings=CandidateScoringSettings(
                common_game_score_similarity=False,
                game_similarity_with_diversity_score=True,
                set_same=SetSameScoringSettings(
                    disease=True,
                    symptom=False,
                    unknown=False,
                ),
            ),
        )

        self.assertEqual(candidate_score, 0.75)
        self.assertIsNone(score_details["common_game_score_similarity"])
        self.assertEqual(
            score_details["game_similarity_with_diversity_score"]["score"],
            0.25,
        )
        self.assertEqual(score_details["set_same_scores"]["score"], 0.5)
        self.assertEqual(
            score_details["set_same_scores"]["symptom"],
            {"enabled": False, "score": None, "reason": "disabled"},
        )
        mock_user_service.get_patient_game_norm_score_series_comparison_by_end_date.assert_not_called()
        mock_user_service.get_patient_game_set_comparison_by_end_date.assert_called_once()
        mock_user_service.get_patient_disease_set_comparison_by_end_date.assert_called_once()
        mock_user_service.get_patient_symptom_set_comparison_by_end_date.assert_not_called()
        mock_user_service.get_patient_unknown_set_comparison_by_end_date.assert_not_called()

    def test_calculate_candidate_score_includes_disease_course_secondary_ability_score(
        self,
    ) -> None:
        mock_user_service = Mock()
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.side_effect = [
            [
                {
                    "training_date": "2022-01-01",
                    "secondary_ability_scores": {
                        "二级_书写能力": 10,
                        "二级_任务切换": None,
                    },
                }
            ],
            [
                {
                    "training_date": "2022-01-01",
                    "secondary_ability_scores": {
                        "二级_书写能力": 5,
                        "二级_任务切换": 2,
                    },
                }
            ],
        ]

        candidate_score, score_details = SimilarUserCandidateService(
            user_service=mock_user_service
        ).calculate_candidate_score(
            primary_patient_id="30010096",
            candidate_patient_id="20113562",
            end_date="2022-01-13",
            candidate_base_dates=["2021-12-14"],
            disease_course_window_days=365,
            scoring_settings=CandidateScoringSettings(
                common_game_score_similarity=False,
                game_similarity_with_diversity_score=False,
                disease_course_secondary_ability=True,
                set_same=SetSameScoringSettings(
                    disease=False,
                    symptom=False,
                    unknown=False,
                ),
            ),
        )

        self.assertEqual(candidate_score, 0.667)
        disease_course_details = score_details["disease_course_secondary_ability"]
        self.assertEqual(disease_course_details["score"], 0.667)
        self.assertAlmostEqual(disease_course_details["distance"], 0.5)
        self.assertEqual(disease_course_details["used_count"], 1)
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.assert_any_call(
            "30010096",
            "2022-01-13",
            365,
        )
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.assert_any_call(
            "20113562",
            "2021-12-14",
            365,
        )

    def test_calculate_candidate_score_aggregates_disease_course_secondary_ability_window(
        self,
    ) -> None:
        mock_user_service = Mock()
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.side_effect = [
            [
                {
                    "training_date": "2022-01-01",
                    "secondary_ability_scores": {
                        "二级_书写能力": 10,
                        "二级_任务切换": 30,
                    },
                },
                {
                    "training_date": "2022-01-02",
                    "secondary_ability_scores": {
                        "二级_书写能力": 14,
                        "二级_任务切换": None,
                    },
                },
            ],
            [
                {
                    "training_date": "2021-12-01",
                    "secondary_ability_scores": {
                        "二级_书写能力": 6,
                        "二级_任务切换": 15,
                    },
                }
            ],
        ]

        candidate_score, score_details = SimilarUserCandidateService(
            user_service=mock_user_service
        ).calculate_candidate_score(
            primary_patient_id="30010096",
            candidate_patient_id="20113562",
            end_date="2022-01-13",
            candidate_base_dates=["2021-12-14"],
            disease_course_window_days=365,
            scoring_settings=CandidateScoringSettings(
                common_game_score_similarity=False,
                game_similarity_with_diversity_score=False,
                disease_course_secondary_ability=True,
                set_same=SetSameScoringSettings(
                    disease=False,
                    symptom=False,
                    unknown=False,
                ),
            ),
        )

        disease_course_details = score_details["disease_course_secondary_ability"]
        self.assertEqual(candidate_score, 0.586)
        self.assertEqual(disease_course_details["score"], 0.586)
        self.assertAlmostEqual(disease_course_details["distance"], 0.70710678)
        self.assertEqual(disease_course_details["aggregation"], "mean")
        self.assertEqual(disease_course_details["primary_record_count"], 2)
        self.assertEqual(disease_course_details["candidate_record_count"], 1)
        self.assertEqual(disease_course_details["primary_aggregated_ability_count"], 2)
        self.assertEqual(disease_course_details["candidate_aggregated_ability_count"], 2)
        self.assertEqual(disease_course_details["used_count"], 2)

    def test_calculate_candidate_score_skips_disease_course_without_window(
        self,
    ) -> None:
        mock_user_service = Mock()

        candidate_score, score_details = SimilarUserCandidateService(
            user_service=mock_user_service
        ).calculate_candidate_score(
            primary_patient_id="30010096",
            candidate_patient_id="20113562",
            end_date="2022-01-13",
            scoring_settings=CandidateScoringSettings(
                common_game_score_similarity=False,
                game_similarity_with_diversity_score=False,
                disease_course_secondary_ability=True,
                set_same=SetSameScoringSettings(
                    disease=False,
                    symptom=False,
                    unknown=False,
                ),
            ),
        )

        self.assertIsNone(candidate_score)
        self.assertEqual(
            score_details["disease_course_secondary_ability"],
            {
                "enabled": True,
                "score": None,
                "reason": "missing disease_course_window_days",
            },
        )
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.assert_not_called()

    def test_aggregate_candidates_warns_and_skips_disease_course_without_recommended_date(
        self,
    ) -> None:
        scored_result = {
            "source_id": "30010096",
            "source_parameter": "patient_id",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 2,
            "scored_path_count": 2,
            "retrieval_context": {"score_end_date": "2022-01-13"},
            "scores": [
                {
                    "path_index": 0,
                    "score": {"total_score": 90.0},
                    "path": {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220113", "训练日期": "2022-01-13"},
                            "i1": {"id": "30010096_20220113_348_a"},
                            "g": {"id": "348", "name": "真假句辨别"},
                            "i2": {"id": "20113562_20211214_348_a"},
                            "s2": {"id": "20113562_20211214", "训练日期": "2021-12-14"},
                            "p2": {"id": "20113562"},
                        }
                    },
                },
                {
                    "path_index": 1,
                    "score": {"total_score": 95.0},
                    "path": {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220113", "训练日期": "2022-01-13"},
                            "i1": {"id": "30010096_20220113_348_b"},
                            "g": {"id": "348", "name": "真假句辨别"},
                            "i2": {"id": "20113562_20211220_348_b"},
                            "s2": {"id": "20113562_20211220", "训练日期": "2021-12-20"},
                            "p2": {"id": "20113562"},
                        }
                    },
                },
            ],
        }
        mock_user_service = Mock()
        mock_user_service.find_patient_total_score_timepoint_matches.return_value = []

        candidate_service = SimilarUserCandidateService(user_service=mock_user_service)
        candidate_service.get_candidate_disease_course_base_date = Mock(
            return_value="2021-12-18"
        )

        with self.assertLogs(
            "similar_user.services.similarity.candidate_service",
            level="WARNING",
        ) as captured_logs:
            result = candidate_service.aggregate_candidates_from_scored_paths(
                scored_result,
                candidate_top_k=1,
                disease_course_window_days=365,
                scoring_settings=CandidateScoringSettings(
                    common_game_score_similarity=False,
                    game_similarity_with_diversity_score=False,
                    disease_course_secondary_ability=True,
                    set_same=SetSameScoringSettings(
                        disease=False,
                        symptom=False,
                        unknown=False,
                    ),
                ),
            )

        disease_course_details = result["candidates"][0]["score_details"][
            "disease_course_secondary_ability"
        ]
        self.assertEqual(
            disease_course_details,
            {
                "enabled": True,
                "score": None,
                "reason": "missing candidate disease-course base dates",
                "primary_base_date": "2022-01-13",
                "candidate_base_dates": [],
            },
        )
        self.assertTrue(
            any(
                "candidate has no suitable disease-course timepoint" in message
                for message in captured_logs.output
            )
        )
        candidate_service.get_candidate_disease_course_base_date.assert_not_called()
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.assert_not_called()

    def test_aggregate_candidates_uses_total_score_recommended_date_for_disease_course_score(
        self,
    ) -> None:
        scored_result = {
            "source_id": "30010096",
            "source_parameter": "patient_id",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 1,
            "scored_path_count": 1,
            "retrieval_context": {"score_end_date": "2022-01-13"},
            "scores": [
                {
                    "path_index": 0,
                    "score": {"total_score": 90.0},
                    "path": {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220113", "训练日期": "2022-01-13"},
                            "i1": {"id": "30010096_20220113_348_a"},
                            "g": {"id": "348", "name": "真假句辨别"},
                            "i2": {"id": "20113562_20211214_348_a"},
                            "s2": {"id": "20113562_20211214", "训练日期": "2021-12-14"},
                            "p2": {"id": "20113562"},
                        }
                    },
                },
            ],
        }
        mock_user_service = Mock()
        mock_user_service.find_patient_total_score_timepoint_matches.return_value = [
            {
                "matched": {
                    "patient_id": "20113562",
                    "training_date": "2021-12-14",
                    "recommended_date": "2022-06-14",
                }
            }
        ]
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.side_effect = [
            [
                {
                    "training_date": "2022-01-01",
                    "secondary_ability_scores": {"二级_书写能力": 10},
                }
            ],
            [
                {
                    "training_date": "2022-06-01",
                    "secondary_ability_scores": {"二级_书写能力": 10},
                }
            ],
        ]
        candidate_service = SimilarUserCandidateService(user_service=mock_user_service)
        candidate_service.get_candidate_disease_course_base_date = Mock(
            return_value="should-not-be-used"
        )

        result = candidate_service.aggregate_candidates_from_scored_paths(
            scored_result,
            candidate_top_k=1,
            disease_course_window_days=365,
            scoring_settings=CandidateScoringSettings(
                common_game_score_similarity=False,
                game_similarity_with_diversity_score=False,
                disease_course_secondary_ability=True,
                set_same=SetSameScoringSettings(
                    disease=False,
                    symptom=False,
                    unknown=False,
                ),
            ),
        )

        disease_course_details = result["candidates"][0]["score_details"][
            "disease_course_secondary_ability"
        ]
        self.assertEqual(disease_course_details["candidate_base_date"], "2022-06-14")
        mock_user_service.find_patient_total_score_timepoint_matches.assert_called_once_with(
            source_patient_id="30010096",
            source_training_date="2022-01-13",
            comparison_patient_ids=["20113562"],
        )
        candidate_service.get_candidate_disease_course_base_date.assert_not_called()
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.assert_any_call(
            "20113562",
            "2022-06-14",
            365,
        )

    def test_aggregate_candidates_uses_highest_disease_course_score_from_recommended_dates(
        self,
    ) -> None:
        scored_result = {
            "source_id": "30010096",
            "source_parameter": "patient_id",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 1,
            "scored_path_count": 1,
            "retrieval_context": {"score_end_date": "2022-01-13"},
            "scores": [
                {
                    "path_index": 0,
                    "score": {"total_score": 90.0},
                    "path": {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220113", "训练日期": "2022-01-13"},
                            "i1": {"id": "30010096_20220113_348_a"},
                            "g": {"id": "348", "name": "真假句辨别"},
                            "i2": {"id": "20113562_20211214_348_a"},
                            "s2": {"id": "20113562_20211214", "训练日期": "2021-12-14"},
                            "p2": {"id": "20113562"},
                        }
                    },
                },
            ],
        }
        mock_user_service = Mock()
        mock_user_service.find_patient_total_score_timepoint_matches.return_value = [
            {
                "matched": {
                    "patient_id": "20113562",
                    "recommended_date": "2022-06-14",
                }
            },
            {
                "matched": {
                    "patient_id": "20113562",
                    "recommended_date": "2022-07-14",
                }
            },
        ]
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.side_effect = [
            [
                {
                    "training_date": "2022-01-01",
                    "secondary_ability_scores": {"二级_书写能力": 10},
                }
            ],
            [
                {
                    "training_date": "2022-06-01",
                    "secondary_ability_scores": {"二级_书写能力": 5},
                }
            ],
            [
                {
                    "training_date": "2022-01-01",
                    "secondary_ability_scores": {"二级_书写能力": 10},
                }
            ],
            [
                {
                    "training_date": "2022-07-01",
                    "secondary_ability_scores": {"二级_书写能力": 10},
                }
            ],
        ]
        candidate_service = SimilarUserCandidateService(user_service=mock_user_service)

        result = candidate_service.aggregate_candidates_from_scored_paths(
            scored_result,
            candidate_top_k=1,
            disease_course_window_days=365,
            scoring_settings=CandidateScoringSettings(
                common_game_score_similarity=False,
                game_similarity_with_diversity_score=False,
                disease_course_secondary_ability=True,
                set_same=SetSameScoringSettings(
                    disease=False,
                    symptom=False,
                    unknown=False,
                ),
            ),
        )

        disease_course_details = result["candidates"][0]["score_details"][
            "disease_course_secondary_ability"
        ]
        self.assertEqual(result["candidates"][0]["candidate_score"], 1.0)
        self.assertEqual(disease_course_details["candidate_base_date"], "2022-07-14")
        self.assertEqual(disease_course_details["score"], 1.0)
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.assert_any_call(
            "20113562",
            "2022-06-14",
            365,
        )
        mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.assert_any_call(
            "20113562",
            "2022-07-14",
            365,
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
            "source_id": "30010096",
            "source_parameter": "patient_id",
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
            candidate_top_k=2,
        )

        self.assertEqual(result["candidate_top_k"], 2)
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(result["pre_score_candidate_count"], 3)
        self.assertEqual(
            [candidate["patient_id"] for candidate in result["candidates"]],
            ["20113563", "20113564"],
        )

    def test_aggregate_candidates_from_scored_paths_validates_candidate_top_k(self) -> None:
        scored_result = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 0,
            "scored_path_count": 0,
            "scores": [],
        }

        with self.assertRaisesRegex(ValueError, "candidate_top_k"):
            SimilarUserCandidateService().aggregate_candidates_from_scored_paths(
                scored_result,
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
            candidate_top_k=2,
        )

        self.assertEqual(result["retrieval_context"]["score_end_date"], None)
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["patient_id"], "20113563")

    def test_aggregate_candidates_merges_patient_and_direct_entity_paths(self) -> None:
        patient_row = {
            "p": {"id": "30010096"},
            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
            "i1": {"id": "30010096_20220522_348_x", "任务类型": "专属", "结果": "完成"},
            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
            "i2": {"id": "20113563_20211214_348_x", "结果": "完成", "活跃": "是", "任务类型": "专属"},
            "s2": {"id": "20113563_20211214", "执行年龄": "65", "执行学历": "本科"},
            "p2": {"id": "20113563"},
        }
        patient_scored_result = {
            "source_id": "30010096",
            "source_parameter": "patient_id",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 1,
            "scored_path_count": 1,
            "retrieval_context": {"split_training_date": "2022-01-13"},
            "scores": [
                {
                    "path_index": 0,
                    "score": {"total_score": 95.0},
                    "path": {"row": patient_row},
                },
            ],
        }
        direct_entity_scored_result = {
            "source_id": "30010096",
            "source_parameter": "patient_id",
            "pattern": "DIRECT_ENTITY_PATHS",
            "path_count": 2,
            "scored_path_count": 2,
            "scores": [
                {
                    "pattern": "DISEASE_TASKSET_PATIENT",
                    "path_index": 3,
                    "patient_id": "20113563",
                    "score": {"total_score": 88.0},
                },
                {
                    "pattern": "SYMPTOM_TASKSET_PATIENT",
                    "path_index": 4,
                    "patient_id": "20113564",
                    "score": {"total_score": 82.0},
                },
            ],
        }

        result = (
            SimilarUserCandidateService()
            .aggregate_candidates_from_multiple_scored_results(
                [patient_scored_result, direct_entity_scored_result],
                candidate_top_k=10,
            )
        )

        candidates_by_id = {
            candidate["patient_id"]: candidate for candidate in result["candidates"]
        }
        self.assertEqual(result["pre_score_candidate_count"], 2)
        self.assertEqual(candidates_by_id["20113563"]["match_count"], 2)
        self.assertEqual(candidates_by_id["20113563"]["best_score"], 95.0)
        self.assertEqual(candidates_by_id["20113563"]["avg_score"], 91.5)
        self.assertEqual(
            sorted(candidates_by_id["20113563"]["pattern_breakdown"]),
            [
                "DISEASE_TASKSET_PATIENT",
                "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            ],
        )
        self.assertEqual(
            candidates_by_id["20113563"]["pattern_breakdown"][
                "DISEASE_TASKSET_PATIENT"
            ]["source_type"],
            "direct_entity_path",
        )
        self.assertEqual(candidates_by_id["20113564"]["match_count"], 1)

    def test_aggregate_candidates_can_disable_direct_entity_paths(self) -> None:
        patient_row = {
            "p": {"id": "30010096"},
            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
            "i1": {"id": "30010096_20220522_348_x", "任务类型": "专属", "结果": "完成"},
            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
            "i2": {"id": "20113563_20211214_348_x", "结果": "完成", "活跃": "是", "任务类型": "专属"},
            "s2": {"id": "20113563_20211214", "执行年龄": "65", "执行学历": "本科"},
            "p2": {"id": "20113563"},
        }
        patient_scored_result = {
            "source_id": "30010096",
            "source_parameter": "patient_id",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "path_count": 1,
            "scored_path_count": 1,
            "retrieval_context": {"split_training_date": "2022-01-13"},
            "scores": [
                {
                    "path_index": 0,
                    "score": {"total_score": 95.0},
                    "path": {"row": patient_row},
                },
            ],
        }
        direct_entity_scored_result = {
            "source_id": "30010096",
            "source_parameter": "patient_id",
            "pattern": "DIRECT_ENTITY_PATHS",
            "path_count": 1,
            "scored_path_count": 1,
            "scores": [
                {
                    "pattern": "DISEASE_TASKSET_PATIENT",
                    "path_index": 3,
                    "patient_id": "20113564",
                    "score": {"total_score": 88.0},
                },
            ],
        }

        result = (
            SimilarUserCandidateService()
            .aggregate_candidates_from_multiple_scored_results(
                [patient_scored_result, direct_entity_scored_result],
                candidate_top_k=10,
                include_direct_entity_paths=False,
            )
        )

        self.assertEqual(result["pre_score_candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["patient_id"], "20113563")
        self.assertEqual(result["candidates"][0]["match_count"], 1)

    def test_build_similar_user_candidates_uses_saved_scored_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            scored_paths_dir = Path(temp_dir) / "scored_pattern_paths"
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
                        "candidate_ranking:",
                        "  patterns:",
                        "    - patient_game_patient",
                        "  candidate_top_k: 2",
                    ]
                ),
                encoding="utf-8",
            )
            scored_result = {
                "source_id": "30010096",
                "source_parameter": "patient_id",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "path_count": 3,
                "scored_path_count": 3,
                "retrieval_context": {
                    "split_training_date": "2022-01-13",
                },
                "scores": [
                    {
                        "path_index": 0,
                        "score": {"total_score": 95.0},
                        "path": {
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
                    },
                    {
                        "path_index": 1,
                        "score": {"total_score": 80.0},
                        "path": {
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
                    },
                    {
                        "path_index": 2,
                        "score": {"total_score": 90.0},
                        "path": {
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
                    },
                ],
            }
            save_scored_pattern_result(scored_result, scored_paths_dir)

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
                candidates = build_similar_user_candidates(
                    "30010096",
                    scored_paths_dir=scored_paths_dir,
                )

        self.assertEqual(candidates["candidate_count"], 2)
        self.assertEqual(candidates["retrieval_context"]["score_end_date"], "2022-01-13")
        self.assertEqual(candidates["candidates"][0]["patient_id"], "20113562")
        self.assertEqual(candidates["candidates"][0]["match_count"], 2)
        self.assertEqual(candidates["candidates"][1]["patient_id"], "20113563")

    def test_build_similar_user_candidates_reads_candidate_top_k_from_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            scored_paths_dir = Path(temp_dir) / "scored_pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "candidate_ranking:",
                        "  patterns:",
                        "    - patient_game_patient",
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
                "source_id": "30010096",
                "source_parameter": "patient_id",
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
            save_scored_pattern_result(scored_result, scored_paths_dir)
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
                        {"game": "打怪物", "scores_p1": ["80"], "scores_p2": ["80"]},
                        {"game": "真假句辨别", "scores_p1": ["90"], "scores_p2": ["90"]},
                    ]
                )
                mock_user_service.get_patient_distinct_games_by_end_date.return_value = [
                    {"g": {"id": "348", "name": "真假句辨别"}}
                ]
                mock_user_service_cls.return_value = mock_user_service
                candidates = build_similar_user_candidates(
                    "30010096",
                    scored_paths_dir=scored_paths_dir,
                )

        self.assertEqual(candidates["candidate_top_k"], 1)
        self.assertEqual(candidates["candidate_count"], 1)
        self.assertEqual(candidates["candidates"][0]["patient_id"], "20113562")

    @patch("scripts.build_similar_user_candidates.LOGGER")
    def test_build_similar_user_candidates_uses_disease_course_window_override(
        self,
        mock_logger: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            scored_paths_dir = Path(temp_dir) / "scored_pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "candidate_ranking:",
                        "  patterns:",
                        "    - patient_game_patient",
                        "  candidate_top_k: 1",
                        "  disease_course_window_days: 180",
                        "  scoring:",
                        "    common_game_score_similarity: false",
                        "    game_similarity_with_diversity_score: false",
                        "    disease_course_secondary_ability: true",
                        "    set_same:",
                        "      disease: false",
                        "      symptom: false",
                        "      unknown: false",
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
            save_scored_pattern_result(
                {
                    "source_id": "30010096",
                    "source_parameter": "patient_id",
                    "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                    "path_count": 1,
                    "scored_path_count": 1,
                    "retrieval_context": {"score_end_date": "2022-05-22"},
                    "scores": [
                        {
                            "path_index": 0,
                            "score": {"total_score": 95.0},
                            "path": {"row": valid_row},
                        }
                    ],
                },
                scored_paths_dir,
            )
            with patch(
                "scripts.build_similar_user_candidates.Neo4jClient.from_config",
            ) as mock_from_config, patch(
                "scripts.build_similar_user_candidates.UserService",
            ) as mock_user_service_cls:
                mock_client_context = Mock()
                mock_client_context.__enter__ = Mock(return_value=Mock())
                mock_client_context.__exit__ = Mock(return_value=None)
                mock_from_config.return_value = mock_client_context
                mock_user_service = Mock()
                mock_user_service.find_patient_total_score_timepoint_matches.return_value = [
                    {
                        "matched": {
                            "patient_id": "20113562",
                            "recommended_date": "2022-02-01",
                        }
                    }
                ]
                mock_user_service.get_patient_secondary_ability_scores_by_disease_course_window.side_effect = [
                    [
                        {
                            "training_date": "2022-05-22",
                            "secondary_ability_scores": {"二级_书写能力": 10},
                        }
                    ],
                    [
                        {
                            "training_date": "2022-02-01",
                            "secondary_ability_scores": {"二级_书写能力": 10},
                        }
                    ],
                ]
                mock_user_service_cls.return_value = mock_user_service
                candidates = build_similar_user_candidates(
                    "30010096",
                    config_path=config_path,
                    scored_paths_dir=scored_paths_dir,
                    disease_course_window_days=90,
                )

        self.assertEqual(
            candidates["retrieval_context"]["disease_course_window_days"],
            90,
        )
        self.assertEqual(candidates["pre_score_candidate_count"], 1)
        self.assertEqual(candidates["disease_course_available_count"], 1)
        self.assertEqual(candidates["disease_course_missing_count"], 0)
        mock_logger.info.assert_any_call(
            "Completed similar-user candidate build: patient_id=%s, pre_score_candidate_count=%s, candidate_count=%s, scored_path_count=%s, disease_course_available_count=%s, disease_course_missing_count=%s, elapsed_seconds=%s",
            "30010096",
            1,
            1,
            1,
            1,
            0,
            ANY,
        )

    def test_build_similar_user_candidates_reads_multiple_saved_scored_patterns(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            scored_paths_dir = Path(temp_dir) / "scored_pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "candidate_ranking:",
                        "  patterns:",
                        "    - patient_game_patient",
                        "    - patient_disease_patient",
                        "  candidate_top_k: 2",
                    ]
                ),
                encoding="utf-8",
            )
            game_row = {
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
            disease_row = {
                "p": {"id": "30010096"},
                "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
                "dis": {"id": "AU_DIS_0013", "name": "遗忘型轻度认知障碍"},
                "s2": {"id": "20113562_20211214", "执行年龄": "64", "执行学历": "大专"},
                "p2": {"id": "20113562"},
            }
            save_scored_pattern_result(
                {
                    "source_id": "30010096",
                    "source_parameter": "patient_id",
                    "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                    "path_count": 1,
                    "scored_path_count": 1,
                    "retrieval_context": {"score_end_date": "2022-05-22"},
                    "scores": [
                        {
                            "path_index": 0,
                            "score": {"total_score": 95.0},
                            "path": {"row": game_row},
                        }
                    ],
                },
                scored_paths_dir,
            )
            save_scored_pattern_result(
                {
                    "source_id": "30010096",
                    "source_parameter": "patient_id",
                    "pattern": "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT",
                    "path_count": 1,
                    "scored_path_count": 1,
                    "retrieval_context": {"score_end_date": "2022-05-22"},
                    "scores": [
                        {
                            "path_index": 0,
                            "score": {"total_score": 91.0},
                            "path": {"row": disease_row},
                        }
                    ],
                },
                scored_paths_dir,
            )
            with patch(
                "scripts.build_similar_user_candidates.Neo4jClient.from_config",
            ) as mock_from_config, patch(
                "scripts.build_similar_user_candidates.UserService",
            ) as mock_user_service_cls:
                mock_client_context = Mock()
                mock_client_context.__enter__ = Mock(return_value=Mock())
                mock_client_context.__exit__ = Mock(return_value=None)
                mock_from_config.return_value = mock_client_context
                mock_user_service = Mock()
                mock_user_service.get_patient_game_norm_score_series_comparison_by_end_date.return_value = [
                    {"game": "真假句辨别", "scores_p1": ["90"], "scores_p2": ["90"]}
                ]
                mock_user_service.get_patient_game_set_comparison_by_end_date.return_value = [
                    {"games1": [{"id": "348"}], "games2": [{"id": "348"}]}
                ]
                mock_user_service.get_patient_disease_set_comparison_by_end_date.return_value = [
                    {"diseases1": [], "diseases2": []}
                ]
                mock_user_service.get_patient_symptom_set_comparison_by_end_date.return_value = [
                    {"symptoms1": [], "symptoms2": []}
                ]
                mock_user_service.get_patient_unknown_set_comparison_by_end_date.return_value = [
                    {"unknowns1": [], "unknowns2": []}
                ]
                mock_user_service_cls.return_value = mock_user_service

                candidates = build_similar_user_candidates(
                    "30010096",
                    config_path=config_path,
                    scored_paths_dir=scored_paths_dir,
                )

        self.assertEqual(
            candidates["patterns"],
            [
                "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT",
            ],
        )
        self.assertEqual(candidates["candidate_count"], 1)
        candidate = candidates["candidates"][0]
        self.assertEqual(candidate["patient_id"], "20113562")
        self.assertEqual(candidate["match_count"], 2)
        self.assertEqual(
            sorted(candidate["pattern_breakdown"]),
            [
                "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT",
                "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            ],
        )

    @patch("scripts.build_similar_user_candidates.LOGGER")
    def test_load_saved_scored_pattern_result_warns_when_missing(
        self,
        mock_logger: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = load_saved_scored_pattern_result(
                "30010096",
                pattern="patient_game_patient",
                scored_paths_dir=Path(temp_dir) / "scored_pattern_paths",
                scored_key="missing_scored_key",
            )

        self.assertIsNone(result)
        mock_logger.warning.assert_called_once()

    def test_load_saved_scored_pattern_result_uses_scored_cache_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            scored_paths_dir = Path(temp_dir) / "scored_pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "score_pattern_paths:",
                        "  top_k: 150",
                    ]
                ),
                encoding="utf-8",
            )
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )
            scored_key = build_scored_key(path_key, 150)
            saved_result = {
                "source_id": "30010096",
                "source_parameter": "patient_id",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "path_count": 1,
                "scored_path_count": 1,
                "retrieval_context": {"score_end_date": "2024-01-31"},
                "scores": [],
                "cache_context": {
                    "cache_type": "scored_pattern_paths",
                    "path_key": path_key,
                    "scored_key": scored_key,
                    "score_top_k": 150,
                },
            }
            save_scored_pattern_result(saved_result, scored_paths_dir)

            loaded_result = load_saved_scored_pattern_result(
                "30010096",
                pattern="patient_game_patient",
                scored_paths_dir=scored_paths_dir,
                scored_key=scored_key,
            )

        self.assertEqual(loaded_result, saved_result)

    def test_save_similar_user_candidates_result_writes_detail_and_summary_files(
        self,
    ) -> None:
        result = {
            "source_id": "30010096",
            "source_parameter": "patient_id",
            "patterns": [
                "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT",
            ],
            "candidate_top_k": 2,
            "path_count": 10,
            "scored_path_count": 5,
            "retrieval_context": {"score_end_date": "2022-05-22"},
            "candidate_count": 1,
            "cache_context": {
                "cache_type": "similar_user_candidates",
                "scored_key": "test_scored_key",
                "candidate_key": "test_scored_key_candcfg_12345678",
                "candidate_config_hash": "12345678",
                "candidate_config": {
                    "patterns": ["patient_game_patient"],
                    "candidate_top_k": 2,
                    "total_score_match_top_k": 1,
                    "disease_course_window_days": 14,
                    "scoring": {},
                },
            },
            "candidates": [
                {
                    "patient_id": "20113562",
                    "candidate_score": 2.232,
                    "match_count": 3,
                    "best_score": 95.0,
                    "avg_score": 90.0,
                    "pattern_breakdown": {
                        "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT": {
                            "match_count": 2,
                        },
                        "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT": {
                            "match_count": 1,
                        },
                    },
                    "score_details": {
                        "common_game_score_similarity": {
                            "similarity": 0.982,
                            "common_games": ["专注猎手", "冰块求和"],
                        },
                        "game_similarity_with_diversity_score": {
                            "score": 0.25,
                            "source_game_count": 3,
                            "candidate_game_count": 4,
                        },
                        "disease_course_secondary_ability": {
                            "score": 0.667,
                            "distance": 0.5,
                            "used_count": 31,
                        },
                        "set_same_scores": {
                            "disease": {"score": 0.5, "same_items": ["D1"]},
                            "symptom": {"score": 0.25, "same_items": ["S1"]},
                            "unknown": {"score": 0.0, "same_items": []},
                            "score": 0.75,
                        },
                    },
                }
            ],
        }

        with tempfile.TemporaryDirectory() as temp_dir:
            output_paths = save_similar_user_candidates_result(
                result,
                Path(temp_dir),
            )
            detail = json.loads(output_paths["detail"].read_text(encoding="utf-8"))
            summary = json.loads(output_paths["summary"].read_text(encoding="utf-8"))

        self.assertEqual(
            output_paths["detail"].name,
            "30010096.detail.json",
        )
        self.assertIn("test_scored_key_candcfg_12345678", str(output_paths["detail"]))
        expected_score_summary = build_similar_user_candidate_summary(result)
        self.assertEqual(
            detail["candidates"][0]["score_details"],
            result["candidates"][0]["score_details"],
        )
        self.assertNotIn("match_count", detail["candidates"][0])
        self.assertNotIn("best_score", detail["candidates"][0])
        self.assertNotIn("avg_score", detail["candidates"][0])
        self.assertNotIn("pattern_breakdown", detail["candidates"][0])
        self.assertEqual(
            summary,
            expected_score_summary,
        )
        self.assertEqual(
            summary["candidates"][0]["score_summary"],
            {
                "common_game_score_similarity": 0.982,
                "game_similarity_with_diversity_score": 0.25,
                "disease_course_secondary_ability": {
                    "score": 0.667,
                    "distance": 0.5,
                },
                "set_same_score": {
                    "total": 0.75,
                    "disease": 0.5,
                    "symptom": 0.25,
                    "unknown": 0.0,
                },
            },
        )
        self.assertNotIn("score_details", summary["candidates"][0])
        self.assertNotIn("common_games", json.dumps(summary, ensure_ascii=False))
        self.assertNotIn("same_items", json.dumps(summary, ensure_ascii=False))
        self.assertNotIn("match_count", summary["candidates"][0])
        self.assertNotIn("best_score", summary["candidates"][0])
        self.assertNotIn("avg_score", summary["candidates"][0])
        self.assertNotIn("pattern_breakdown", summary["candidates"][0])
        self.assertNotIn("patterns", summary)
        self.assertNotIn("path_count", summary)
        self.assertNotIn("scored_path_count", summary)

    def test_save_similar_user_candidates_result_requires_candidate_cache_key(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaisesRegex(ValueError, "cache_context must be present"):
                save_similar_user_candidates_result(
                    {
                        "source_id": "30010096",
                        "source_parameter": "patient_id",
                        "candidate_top_k": 10,
                        "candidate_count": 0,
                        "candidates": [],
                    },
                    Path(temp_dir),
                )

    def test_save_similar_user_candidates_result_uses_candidate_cache_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            output_dir = Path(temp_dir) / "similar_user_candidates"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "score_pattern_paths:",
                        "  top_k: 150",
                        "candidate_ranking:",
                        "  patterns:",
                        "    - patient_game_patient",
                        "  candidate_top_k: 10",
                        "  total_score_match_top_k: 3",
                        "  disease_course_window_days: 14",
                        "  scoring:",
                        "    common_game_score_similarity: false",
                        "    game_similarity_with_diversity_score: false",
                        "    disease_course_secondary_ability: true",
                        "    set_same:",
                        "      disease: false",
                        "      symptom: false",
                        "      unknown: false",
                    ]
                ),
                encoding="utf-8",
            )
            path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )
            scored_key = build_scored_key(path_key, 150)
            cache_context = build_candidate_cache_context(
                config_path,
                scored_key=scored_key,
                disease_course_window_days=14,
            )

            output_paths = save_similar_user_candidates_result(
                {
                    "source_id": "30010096",
                    "source_parameter": "patient_id",
                    "candidate_top_k": 10,
                    "retrieval_context": {"score_end_date": "2024-01-31"},
                    "candidate_count": 0,
                    "candidates": [],
                    "cache_context": cache_context,
                },
                output_dir,
            )

        self.assertEqual(
            output_paths["detail"],
            output_dir
            / cache_context["candidate_key"]
            / "30"
            / "30010096.detail.json",
        )
        self.assertIn(f"{scored_key}_candcfg_", cache_context["candidate_key"])

    def test_topk_user_cache_context_is_disabled_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = root / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                    ]
                ),
                encoding="utf-8",
            )

            context = build_topk_candidate_user_cache_context(
                config_path,
                patient_id="30010096",
                base_date=None,
                query_family=None,
                scored_key="base_2024-01-31_window_14_qf_default_pathcfg_abc_scoretopk_150",
                candidate_cache_context={
                    "candidate_key": "base_2024-01-31_window_14_qf_default_pathcfg_abc_scoretopk_150_candcfg_def",
                    "candidate_config_hash": "def",
                },
            )

        self.assertEqual(context, {"enabled": False, "cache_type": "topk_candidates"})

    def test_save_similar_user_candidates_result_registers_topk_user_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_user_cache_config(
                root,
                refresh_candidate_base_date_on_hit=False,
            )
            output_dir = root / "similar_user_candidates"
            scored_key = build_scored_key(
                build_path_key(
                    config_path,
                    base_date="2024-01-31",
                    query_family="training_order_source_window",
                ),
                150,
            )
            cache_context = build_candidate_cache_context(
                config_path,
                scored_key=scored_key,
                disease_course_window_days=14,
            )
            user_cache_context = build_topk_candidate_user_cache_context(
                config_path,
                patient_id="30010096",
                base_date="2024-01-31",
                query_family="training_order_source_window",
                scored_key=scored_key,
                candidate_cache_context=cache_context,
            )

            output_paths = save_similar_user_candidates_result(
                _candidate_result(
                    cache_context=cache_context,
                    user_cache_context=user_cache_context,
                ),
                output_dir,
            )
            found = UserCacheIndexStore(
                root / "user_cache" / "cache_index.sqlite"
            ).find_latest_valid_source_entry(
                cache_type="topk_candidates",
                source_type="patient",
                source_id="30010096",
                query_family="training_order_source_window",
                window_days=14,
                config_hash=str(user_cache_context["config_hash"]),
                request_base_date="2024-02-03",
            )

        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.cached_base_date, "2024-01-31")
        self.assertEqual(found.data_path, str(output_paths["detail"]))
        self.assertIn(
            str(root / "user_cache" / "files" / "patient" / "30" / "30010096"),
            str(output_paths["detail"]),
        )
        self.assertIn(
            "topk_candidates/training_order_source_window/window_14",
            str(output_paths["detail"]),
        )

    def test_save_direct_entity_candidates_registers_source_topk_user_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_user_cache_config(
                root,
                refresh_candidate_base_date_on_hit=False,
            )
            output_dir = root / "similar_user_candidates"
            scored_result = {
                "source_id": "201231885555",
                "source_parameter": "manual_profile",
                "base_date": "2024-01-31",
                "scoring_input": {
                    "age": 66,
                    "education": "本科",
                    "gender": "男",
                    "disease_ids": ["D1"],
                    "symptom_ids": [],
                    "unknown_ids": [],
                },
                "path_count": 1,
                "scored_path_count": 1,
                "cache_context": {
                    "scored_key": "base_2024-01-31_qf_direct_entity_scoretopk_150",
                    "score_top_k": 150,
                    "pattern_source_keys": {
                        "DISEASE_TASKSET_PATIENT": (
                            "entitybase_2024-01-30_entitywindow_180_pathcfg_abcdef12"
                        )
                    },
                    "source_entries": [
                        {
                            "pattern": "DISEASE_TASKSET_PATIENT",
                            "source_id": "D1",
                            "base_date": "2024-01-30",
                            "window_days": 180,
                            "path_key": "base_2024-01-30_window_180_directcfg_abcdef12",
                        }
                    ],
                },
            }
            cache_context = build_direct_entity_candidate_cache_context(
                config_path,
                scored_result=scored_result,
                disease_course_window_days=21,
            )
            user_cache_context = build_direct_entity_topk_candidate_user_cache_context(
                config_path,
                source_id="201231885555",
                base_date="2024-01-31",
                candidate_cache_context=cache_context,
            )
            candidate_result = {
                "source_id": "201231885555",
                "source_parameter": "manual_profile",
                "candidate_top_k": 10,
                "path_count": 1,
                "scored_path_count": 1,
                "candidate_count": 1,
                "pre_score_candidate_count": 1,
                "ranking": "direct_entity_best_score_avg_score_match_count",
                "cache_context": cache_context,
                "user_cache_context": user_cache_context,
                "user_cache_hit": False,
                "candidates": [
                    {
                        "patient_id": "P1",
                        "candidate_score": 95.0,
                        "match_count": 1,
                        "best_score": 95.0,
                        "avg_score": 95.0,
                    }
                ],
            }

            output_paths = save_similar_user_candidates_result(
                candidate_result,
                output_dir,
            )
            cached = load_cached_topk_candidate_result(
                user_cache_context,
                candidates_dir=output_dir,
                request_base_date="2024-02-03",
            )
            found = UserCacheIndexStore(
                root / "user_cache" / "cache_index.sqlite"
            ).find_latest_valid_source_entry(
                cache_type="topk_candidates",
                source_type="direct_entity_profile",
                source_id="201231885555",
                query_family="direct_entity",
                window_days=14,
                config_hash=str(user_cache_context["config_hash"]),
                request_base_date="2024-02-03",
            )

        self.assertIsNotNone(found)
        assert found is not None
        self.assertEqual(found.data_path, str(output_paths["detail"]))
        self.assertEqual(found.source_type, "direct_entity_profile")
        self.assertEqual(found.window_days, 14)
        self.assertEqual(cache_context["candidate_config"]["disease_course_window_days"], 14)
        self.assertEqual(cache_context["direct_entity_topk_cache_window_days"], 14)
        self.assertEqual(user_cache_context["window_days"], 14)
        self.assertEqual(
            user_cache_context["window_days_source"],
            "direct_entity_topk_cache_window_constant",
        )
        self.assertIn(
            str(root / "user_cache" / "files" / "patient" / "20" / "201231885555"),
            str(output_paths["detail"]),
        )
        self.assertIn("topk_candidates/direct_entity/window_14", str(output_paths["detail"]))
        self.assertIsNotNone(cached)
        assert cached is not None
        self.assertTrue(cached["user_cache_hit"])
        self.assertEqual(cached["source_id"], "201231885555")
        self.assertEqual(cached["candidate_count"], 1)

    def test_build_similar_user_candidates_uses_valid_topk_user_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_user_cache_config(
                root,
                refresh_candidate_base_date_on_hit=False,
            )
            output_dir = root / "similar_user_candidates"
            scored_key = build_scored_key(
                build_path_key(
                    config_path,
                    base_date="2024-01-31",
                    query_family="training_order_source_window",
                ),
                150,
            )
            cache_context = build_candidate_cache_context(
                config_path,
                scored_key=scored_key,
                disease_course_window_days=14,
            )
            user_cache_context = build_topk_candidate_user_cache_context(
                config_path,
                patient_id="30010096",
                base_date="2024-01-31",
                query_family="training_order_source_window",
                scored_key=scored_key,
                candidate_cache_context=cache_context,
            )
            save_similar_user_candidates_result(
                _candidate_result(
                    cache_context=cache_context,
                    user_cache_context=user_cache_context,
                ),
                output_dir,
            )

            with patch(
                "scripts.build_similar_user_candidates.Neo4jClient.from_config",
            ) as mock_from_config:
                result = build_similar_user_candidates(
                    "30010096",
                    config_path=config_path,
                    candidates_dir=output_dir,
                    base_date="2024-02-03",
                    query_family="training_order_source_window",
                )

        mock_from_config.assert_not_called()
        self.assertTrue(result["user_cache_hit"])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["patient_id"], "20113562")

    def test_load_cached_topk_candidate_result_uses_stale_cache_and_enqueues_refresh_job(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_user_cache_config(
                root,
                refresh_candidate_base_date_on_hit=False,
                topk_candidates_stale_valid_days=14,
            )
            output_dir = root / "similar_user_candidates"
            scored_key = build_scored_key(
                build_path_key(
                    config_path,
                    base_date="2024-01-31",
                    query_family="training_order_source_window",
                ),
                150,
            )
            cache_context = build_candidate_cache_context(
                config_path,
                scored_key=scored_key,
                disease_course_window_days=14,
            )
            user_cache_context = build_topk_candidate_user_cache_context(
                config_path,
                patient_id="30010096",
                base_date="2024-01-31",
                query_family="training_order_source_window",
                scored_key=scored_key,
                candidate_cache_context=cache_context,
            )
            save_similar_user_candidates_result(
                _candidate_result(
                    cache_context=cache_context,
                    user_cache_context=user_cache_context,
                ),
                output_dir,
            )

            cached = load_cached_topk_candidate_result(
                user_cache_context,
                candidates_dir=output_dir,
                request_base_date="2024-02-10",
                config_path=config_path,
            )
            cached_again = load_cached_topk_candidate_result(
                user_cache_context,
                candidates_dir=output_dir,
                request_base_date="2024-02-10",
                config_path=config_path,
            )
            store = UserCacheIndexStore(root / "user_cache" / "cache_index.sqlite")
            jobs = store.claim_pending_refresh_jobs(limit=10)

        self.assertIsNotNone(cached)
        assert cached is not None
        self.assertTrue(cached["user_cache_hit"])
        self.assertTrue(cached["user_cache_stale_hit"])
        self.assertEqual(cached["user_cache_lookup_state"], "stale")
        self.assertEqual(cached["user_cache_context"]["cached_base_date"], "2024-01-31")
        self.assertEqual(cached["user_cache_context"]["stale_valid_days"], 14)
        self.assertIsNotNone(cached.get("user_cache_refresh_job_id"))
        self.assertEqual(
            cached.get("user_cache_refresh_job_key"),
            cached_again.get("user_cache_refresh_job_key") if cached_again else None,
        )
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0].status, "running")
        self.assertEqual(jobs[0].cache_type, "topk_candidates")
        self.assertEqual(jobs[0].source_type, "patient")
        self.assertEqual(jobs[0].source_id, "30010096")
        self.assertEqual(jobs[0].request_base_date, "2024-02-10")

    def test_topk_user_cache_hit_refreshes_candidate_base_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_user_cache_config(root)
            output_dir = root / "similar_user_candidates"
            scored_key = build_scored_key(
                build_path_key(
                    config_path,
                    base_date="2024-01-31",
                    query_family="training_order_source_window",
                ),
                150,
            )
            cache_context = build_candidate_cache_context(
                config_path,
                scored_key=scored_key,
                disease_course_window_days=14,
            )
            user_cache_context = build_topk_candidate_user_cache_context(
                config_path,
                patient_id="30010096",
                base_date="2024-01-31",
                query_family="training_order_source_window",
                scored_key=scored_key,
                candidate_cache_context=cache_context,
            )
            save_similar_user_candidates_result(
                _candidate_result(
                    cache_context=cache_context,
                    user_cache_context=user_cache_context,
                ),
                output_dir,
            )

            with patch(
                "scripts.build_similar_user_candidates.Neo4jClient.from_config",
            ) as mock_from_config, patch(
                "scripts.build_similar_user_candidates.UserService",
            ) as mock_user_service_cls:
                mock_client_context = Mock()
                mock_client_context.__enter__ = Mock(return_value=Mock())
                mock_client_context.__exit__ = Mock(return_value=None)
                mock_from_config.return_value = mock_client_context
                mock_user_service = Mock()
                mock_user_service.find_patient_total_score_timepoint_matches.return_value = [
                    {
                        "matched": {
                            "patient_id": "20113562",
                            "recommended_date": "2024-02-01",
                        }
                    }
                ]
                mock_user_service_cls.return_value = mock_user_service
                result = build_similar_user_candidates(
                    "30010096",
                    config_path=config_path,
                    candidates_dir=output_dir,
                    base_date="2024-02-03",
                    query_family="training_order_source_window",
                )

        self.assertTrue(result["user_cache_hit"])
        disease_course = result["candidates"][0]["score_details"][
            "disease_course_secondary_ability"
        ]
        self.assertEqual(disease_course["candidate_base_date"], "2024-02-01")
        self.assertEqual(
            result["candidate_base_date_refresh"]["request_base_date"],
            "2024-02-03",
        )
        self.assertEqual(result["candidate_base_date_refresh"]["refreshed_count"], 1)
        mock_user_service.find_patient_total_score_timepoint_matches.assert_called_once_with(
            source_patient_id="30010096",
            source_training_date="2024-02-03",
            comparison_patient_ids=["20113562"],
        )

    def test_build_similar_user_candidates_uses_valid_scored_path_user_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_user_cache_config(root)
            scored_paths_dir = root / "scored_pattern_paths"
            old_path_key = build_path_key(
                config_path,
                base_date="2024-01-31",
                query_family="training_order_source_window",
            )
            old_scored_key = build_scored_key(old_path_key, 150)
            scored_cache_context = {
                "cache_type": "scored_pattern_paths",
                "path_key": old_path_key,
                "scored_key": old_scored_key,
                "score_top_k": 150,
            }
            scored_output_paths = save_scored_pattern_result(
                {
                    "source_id": "30010096",
                    "source_parameter": "patient_id",
                    "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                    "path_count": 1,
                    "scored_path_count": 1,
                    "retrieval_context": {
                        "base_date": "2024-01-31",
                        "path_window": {
                            "start_date": "2024-01-17",
                            "end_date": "2024-01-31",
                        },
                        "score_end_date": "2024-01-31",
                    },
                    "scores": [
                        {
                            "path_index": 0,
                            "score": {"total_score": 95.0},
                            "path": {
                                "row": {
                                    "p": {"id": "30010096"},
                                    "s1": {
                                        "id": "30010096_20240131",
                                        "执行年龄": "66",
                                        "执行学历": "本科",
                                    },
                                    "i1": {
                                        "id": "30010096_20240131_348",
                                        "任务类型": "专属",
                                        "结果": "完成",
                                    },
                                    "g": {"id": "348", "name": "真假句辨别"},
                                    "i2": {
                                        "id": "20113562_20240130_348",
                                        "任务类型": "专属",
                                        "结果": "完成",
                                        "活跃": "是",
                                    },
                                    "s2": {
                                        "id": "20113562_20240130",
                                        "执行年龄": "65",
                                        "执行学历": "本科",
                                    },
                                    "p2": {"id": "20113562"},
                                }
                            },
                        }
                    ],
                    "cache_context": scored_cache_context,
                    "user_cache_context": build_scored_path_user_cache_context(
                        config_path,
                        source_id="30010096",
                        base_date="2024-01-31",
                        query_family="training_order_source_window",
                        scored_cache_context=scored_cache_context,
                    ),
                },
                scored_paths_dir,
            )

            with patch(
                "scripts.build_similar_user_candidates.Neo4jClient.from_config",
            ) as mock_from_config, patch(
                "scripts.build_similar_user_candidates.UserService",
            ) as mock_user_service_cls:
                mock_client_context = Mock()
                mock_client_context.__enter__ = Mock(return_value=Mock())
                mock_client_context.__exit__ = Mock(return_value=None)
                mock_from_config.return_value = mock_client_context
                mock_user_service = Mock()
                mock_user_service.get_patient_game_norm_score_series_comparison_by_end_date.return_value = []
                mock_user_service.get_patient_distinct_games_by_end_date.return_value = []
                mock_user_service.get_patient_disease_names_by_end_date.return_value = []
                mock_user_service.get_patient_symptom_names_by_end_date.return_value = []
                mock_user_service.get_patient_unknown_names_by_end_date.return_value = []
                mock_user_service_cls.return_value = mock_user_service
                result = build_similar_user_candidates(
                    "30010096",
                    config_path=config_path,
                    scored_paths_dir=scored_paths_dir,
                    base_date="2024-02-03",
                    query_family="training_order_source_window",
                )

        self.assertFalse(result["user_cache_hit"])
        self.assertEqual(result["candidate_count"], 1)
        self.assertEqual(result["candidates"][0]["patient_id"], "20113562")
        self.assertEqual(result["cache_context"]["scored_key"], old_scored_key)
        self.assertIn(
            str(root / "user_cache" / "files" / "patient" / "30" / "30010096"),
            str(scored_output_paths["detail"]),
        )
        self.assertIn(
            "scored_paths/training_order_source_window/window_14",
            str(scored_output_paths["detail"]),
        )

    def test_build_similar_user_candidates_rejects_expired_scored_path_user_cache(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_user_cache_config(root)
            scored_paths_dir = root / "scored_pattern_paths"
            old_path_key = build_path_key(
                config_path,
                base_date="2024-01-01",
                query_family="training_order_source_window",
            )
            old_scored_key = build_scored_key(old_path_key, 150)
            scored_cache_context = {
                "cache_type": "scored_pattern_paths",
                "path_key": old_path_key,
                "scored_key": old_scored_key,
                "score_top_k": 150,
            }
            save_scored_pattern_result(
                {
                    "source_id": "30010096",
                    "source_parameter": "patient_id",
                    "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                    "path_count": 1,
                    "scored_path_count": 1,
                    "retrieval_context": {
                        "base_date": "2024-01-01",
                        "path_window": {
                            "start_date": "2023-12-18",
                            "end_date": "2024-01-01",
                        },
                        "score_end_date": "2024-01-01",
                    },
                    "scores": [
                        {
                            "path_index": 0,
                            "score": {"total_score": 95.0},
                            "path": {
                                "row": {
                                    "p": {"id": "30010096"},
                                    "i1": {"任务类型": "专属", "结果": "完成"},
                                    "g": {"id": "348", "name": "真假句辨别"},
                                    "i2": {"任务类型": "专属", "结果": "完成", "活跃": "是"},
                                    "p2": {"id": "20113562"},
                                }
                            },
                        }
                    ],
                    "cache_context": scored_cache_context,
                    "user_cache_context": build_scored_path_user_cache_context(
                        config_path,
                        source_id="30010096",
                        base_date="2024-01-01",
                        query_family="training_order_source_window",
                        scored_cache_context=scored_cache_context,
                    ),
                },
                scored_paths_dir,
            )

            with self.assertRaisesRegex(FileNotFoundError, "Patient scored paths missing or expired"):
                build_similar_user_candidates(
                    "30010096",
                    config_path=config_path,
                    scored_paths_dir=scored_paths_dir,
                    base_date="2024-02-03",
                    query_family="training_order_source_window",
                )

    @patch("scripts.build_similar_user_candidates.LOGGER")
    @patch("scripts.build_similar_user_candidates.parse_args")
    @patch("scripts.build_similar_user_candidates.save_similar_user_candidates_result")
    @patch("scripts.build_similar_user_candidates.build_similar_user_candidates")
    def test_main_builds_candidate_result(
        self,
        mock_build_candidates: Mock,
        mock_save_candidates: Mock,
        mock_parse_args: Mock,
        mock_logger: Mock,
    ) -> None:
        expected = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "candidate_top_k": 2,
            "path_count": 10,
            "scored_path_count": 5,
            "retrieval_context": {
                "split_training_date": "2022-01-13",
                "candidate_scope": "候选相似用户来自训练日期 < 2022-01-13 的已保存评分 path 去重结果，最终返回 top-2 候选用户",
            },
            "candidate_count": 2,
            "candidates": [{"patient_id": "20113562"}],
        }
        mock_parse_args.return_value = Mock(
            patient_id="30010096",
            config="config/settings.yaml",
            scored_paths_dir="data/scored_pattern_paths",
            candidates_dir="data/similar_user_candidates",
        )
        mock_build_candidates.return_value = expected
        mock_save_candidates.return_value = {
            "detail": Path("data/similar_user_candidates/30/30010096.detail.json"),
            "summary": Path("data/similar_user_candidates/30/30010096.summary.json"),
        }

        exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_build_candidates.assert_called_once_with(
            "30010096",
            config_path="config/settings.yaml",
            scored_paths_dir="data/scored_pattern_paths",
            candidates_dir="data/similar_user_candidates",
        )
        mock_save_candidates.assert_called_once_with(
            expected,
            output_dir="data/similar_user_candidates",
        )
        mock_logger.info.assert_called_once_with(
            "Saved similar-user candidates: detail_path=%s, summary_path=%s",
            Path("data/similar_user_candidates/30/30010096.detail.json"),
            Path("data/similar_user_candidates/30/30010096.summary.json"),
        )

    @patch("scripts.run_similar_user_pipeline.time.perf_counter")
    @patch("scripts.run_similar_user_pipeline.save_similar_user_candidates_result")
    @patch("scripts.run_similar_user_pipeline.build_similar_user_candidates")
    @patch("scripts.run_similar_user_pipeline.score_and_save_configured_pattern_paths")
    @patch("scripts.run_similar_user_pipeline.run_configured_pattern_path_flows")
    def test_run_similar_user_pipeline_builds_paths_then_candidates(
        self,
        mock_run_path_flows: Mock,
        mock_score_and_save: Mock,
        mock_build_candidates: Mock,
        mock_save_candidates: Mock,
        mock_perf_counter: Mock,
    ) -> None:
        mock_perf_counter.side_effect = [10.0, 12.345]
        path_result = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "retrieval_context": {
                "path_window": {
                    "base_date": "2022-01-17",
                    "start_date": "2022-01-03",
                    "end_date": "2022-01-17",
                    "window_days": 14,
                    "range_semantics": "[start_date, end_date)",
                },
                "paths": [{"row": {}}],
            },
        }
        candidate_result = {
            "patient_id": "30010096",
            "candidate_count": 1,
            "candidates": [{"patient_id": "20113562"}],
        }
        scored_result = {
            "source_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "scores": [],
        }
        mock_run_path_flows.return_value = [path_result]
        mock_score_and_save.return_value = [scored_result]
        mock_build_candidates.return_value = candidate_result
        mock_save_candidates.return_value = {
            "detail": Path("data/similar_user_candidates/30/30010096.detail.json"),
            "summary": Path("data/similar_user_candidates/30/30010096.summary.json"),
        }

        result = run_similar_user_pipeline(
            "30010096",
            base_date="2022-01-17",
            config_path="config/settings.yaml",
            query_family="date_window",
        )

        self.assertIsNone(result["path_generation"])
        self.assertEqual(result["candidate_result"], candidate_result)
        self.assertEqual(
            result["candidate_output_paths"],
            {
                "detail": "data/similar_user_candidates/30/30010096.detail.json",
                "summary": "data/similar_user_candidates/30/30010096.summary.json",
            },
        )
        self.assertFalse(result["skip_path_build"])
        self.assertFalse(result["skip_path_scoring"])
        self.assertEqual(result["elapsed_seconds"], 2.345)
        mock_run_path_flows.assert_not_called()
        mock_build_candidates.assert_called_once_with(
            "30010096",
            config_path="config/settings.yaml",
            base_date="2022-01-17",
            query_family="date_window",
        )
        mock_score_and_save.assert_not_called()
        mock_save_candidates.assert_called_once_with(candidate_result)

    @patch("scripts.run_similar_user_pipeline.save_similar_user_candidates_result")
    @patch("scripts.run_similar_user_pipeline.build_similar_user_candidates")
    @patch("scripts.run_similar_user_pipeline.score_and_save_configured_pattern_paths")
    @patch("scripts.run_similar_user_pipeline.run_configured_pattern_path_flows")
    def test_run_similar_user_pipeline_returns_empty_candidates_for_empty_path_result(
        self,
        mock_run_path_flows: Mock,
        mock_score_and_save: Mock,
        mock_build_candidates: Mock,
        mock_save_candidates: Mock,
    ) -> None:
        mock_run_path_flows.return_value = [
            {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "retrieval_context": {
                    "path_window": {
                        "base_date": "2022-01-17",
                        "start_date": "2022-01-03",
                        "end_date": "2022-01-17",
                        "window_days": 14,
                        "range_semantics": "[start_date, end_date)",
                    },
                    "paths": [],
                },
            },
        ]
        mock_build_candidates.side_effect = FileNotFoundError("missing scored paths")
        mock_score_and_save.side_effect = FileNotFoundError("missing raw paths")
        mock_save_candidates.return_value = {
            "detail": Path("data/similar_user_candidates/30/30010096.detail.json"),
            "summary": Path("data/similar_user_candidates/30/30010096.summary.json"),
        }

        result = run_similar_user_pipeline(
            "30010096",
            base_date="2022-01-17",
            config_path="config/settings.yaml",
        )

        mock_build_candidates.assert_called_once()
        mock_score_and_save.assert_called_once()
        self.assertEqual(result["candidate_result"]["candidate_count"], 0)
        self.assertEqual(result["candidate_result"]["candidates"], [])
        self.assertEqual(result["candidate_result"]["patient_id"], "30010096")
        self.assertEqual(result["candidate_result"]["source_id"], "30010096")
        self.assertEqual(result["candidate_result"]["source_parameter"], "patient_id")
        self.assertIn("candidate_key", result["candidate_result"]["cache_context"])
        self.assertEqual(
            result["candidate_result"]["user_cache_context"]["patient_id"],
            "30010096",
        )
        self.assertFalse(result["candidate_result"]["user_cache_hit"])
        mock_save_candidates.assert_called_once_with(result["candidate_result"])

    @patch("scripts.run_similar_user_pipeline.save_similar_user_candidates_result")
    @patch("scripts.run_similar_user_pipeline.build_similar_user_candidates")
    @patch("scripts.run_similar_user_pipeline.score_and_save_configured_pattern_paths")
    @patch("scripts.run_similar_user_pipeline.run_configured_pattern_path_flows")
    def test_run_similar_user_pipeline_can_skip_path_build(
        self,
        mock_run_path_flows: Mock,
        mock_score_and_save: Mock,
        mock_build_candidates: Mock,
        mock_save_candidates: Mock,
    ) -> None:
        candidate_result = {
            "patient_id": "30010096",
            "candidate_count": 1,
            "candidates": [{"patient_id": "20113562"}],
        }
        scored_result = {
            "source_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "scores": [],
        }
        mock_score_and_save.return_value = [scored_result]
        mock_build_candidates.return_value = candidate_result
        mock_save_candidates.return_value = {
            "detail": Path("data/similar_user_candidates/30/30010096.detail.json"),
            "summary": Path("data/similar_user_candidates/30/30010096.summary.json"),
        }

        result = run_similar_user_pipeline(
            "30010096",
            base_date="2022-01-17",
            config_path="config/settings.yaml",
            skip_path_build=True,
        )

        self.assertIsNone(result["path_generation"])
        self.assertEqual(result["candidate_result"], candidate_result)
        self.assertEqual(
            result["candidate_output_paths"],
            {
                "detail": "data/similar_user_candidates/30/30010096.detail.json",
                "summary": "data/similar_user_candidates/30/30010096.summary.json",
            },
        )
        self.assertTrue(result["skip_path_build"])
        self.assertFalse(result["skip_path_scoring"])
        mock_run_path_flows.assert_not_called()
        mock_score_and_save.assert_not_called()
        mock_build_candidates.assert_called_once_with(
            "30010096",
            config_path="config/settings.yaml",
            base_date="2022-01-17",
            query_family="training_order_source_window",
        )
        mock_save_candidates.assert_called_once_with(candidate_result)

    @patch("scripts.run_similar_user_pipeline.save_similar_user_candidates_result")
    @patch("scripts.run_similar_user_pipeline.build_similar_user_candidates")
    @patch("scripts.run_similar_user_pipeline.score_and_save_configured_pattern_paths")
    @patch("scripts.run_similar_user_pipeline.run_configured_pattern_path_flows")
    def test_run_similar_user_pipeline_can_skip_path_scoring(
        self,
        mock_run_path_flows: Mock,
        mock_score_and_save: Mock,
        mock_build_candidates: Mock,
        mock_save_candidates: Mock,
    ) -> None:
        path_result = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "retrieval_context": {"paths": [{"row": {}}]},
        }
        candidate_result = {
            "patient_id": "30010096",
            "candidate_count": 1,
            "candidates": [{"patient_id": "20113562"}],
        }
        mock_run_path_flows.return_value = [path_result]
        mock_build_candidates.return_value = candidate_result
        mock_save_candidates.return_value = {
            "detail": Path("data/similar_user_candidates/30/30010096.detail.json"),
            "summary": Path("data/similar_user_candidates/30/30010096.summary.json"),
        }

        result = run_similar_user_pipeline(
            "30010096",
            base_date="2022-01-17",
            config_path="config/settings.yaml",
            skip_path_scoring=True,
        )

        self.assertTrue(result["skip_path_scoring"])
        mock_score_and_save.assert_not_called()
        mock_run_path_flows.assert_not_called()
        mock_build_candidates.assert_called_once_with(
            "30010096",
            config_path="config/settings.yaml",
            base_date="2022-01-17",
            query_family="training_order_source_window",
        )
        mock_save_candidates.assert_called_once_with(candidate_result)

    @patch("scripts.run_similar_user_pipeline.score_and_save_configured_pattern_paths")
    @patch("scripts.run_similar_user_pipeline.build_similar_user_candidates")
    def test_patient_candidate_auto_refreshes_missing_scored_paths(
        self,
        mock_build_candidates: Mock,
        mock_score_and_save: Mock,
    ) -> None:
        refreshed_result = {
            "patient_id": "30010096",
            "candidate_count": 1,
            "candidates": [{"patient_id": "20113562"}],
        }
        mock_build_candidates.side_effect = [
            FileNotFoundError("missing scored paths"),
            refreshed_result,
        ]

        result = _build_patient_candidates_with_auto_refresh(
            "30010096",
            config_path="config/settings.yaml",
            base_date="2022-01-17",
            query_family="training_order_source_window",
        )

        self.assertEqual(result, (refreshed_result, None))
        mock_score_and_save.assert_called_once_with(
            "30010096",
            config_path="config/settings.yaml",
            base_date="2022-01-17",
            query_family="training_order_source_window",
        )
        self.assertEqual(mock_build_candidates.call_count, 2)

    @patch("scripts.run_similar_user_pipeline.time.sleep")
    @patch("scripts.run_similar_user_pipeline.run_configured_pattern_path_flows")
    def test_raw_path_build_limiter_retries_transient_failures(
        self,
        mock_run_path_flows: Mock,
        mock_sleep: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "user_cache:",
                        "  raw_path_build_workers: 1",
                        "  raw_path_build_max_retries: 1",
                        "  raw_path_build_retry_sleep_seconds: 0",
                    ]
                ),
                encoding="utf-8",
            )
            mock_run_path_flows.side_effect = [
                RuntimeError("neo4j busy"),
                [
                    {
                        "patient_id": "30010096",
                        "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                        "retrieval_context": {"paths": [{"row": {}}]},
                    }
                ],
            ]

            result = _build_patient_raw_paths_with_limit(
                "30010096",
                config_path=config_path,
                base_date="2022-01-17",
                query_family="training_order_source_window",
            )

        self.assertEqual(result[0]["path_count"], 1)
        self.assertEqual(mock_run_path_flows.call_count, 2)
        mock_sleep.assert_called_once_with(0.0)

    @patch("scripts.run_similar_user_pipeline.LOGGER")
    @patch("scripts.run_similar_user_pipeline.parse_args")
    @patch("scripts.run_similar_user_pipeline.run_similar_user_pipeline")
    def test_pipeline_main_logs_result(
        self,
        mock_run_pipeline: Mock,
        mock_parse_args: Mock,
        mock_logger: Mock,
    ) -> None:
        expected = {
            "patient_id": "30010096",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "config_path": "config/settings.yaml",
            "skip_path_build": False,
            "elapsed_seconds": 2.345,
            "path_generation": None,
            "candidate_result": {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "candidate_top_k": 10,
                "path_count": 230,
                "scored_path_count": 50,
                "retrieval_context": {"split_training_date": "2022-05-22"},
                "candidate_count": 1,
                "candidates": [
                    {
                        "patient_id": "20113562",
                        "candidate_score": 2.232,
                        "match_count": 3,
                        "best_score": 95.0,
                        "avg_score": 90.0,
                        "score_details": {"large": "payload"},
                    }
                ],
            },
        }
        mock_parse_args.return_value = Mock(
            patient_id="30010096",
            pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            config="config/settings.yaml",
            skip_path_build=False,
            skip_path_scoring=False,
            query_family="date_window",
            base_date="2022-05-22",
            output_level="ids",
        )
        mock_run_pipeline.return_value = expected

        exit_code = pipeline_main()

        self.assertEqual(exit_code, 0)
        mock_run_pipeline.assert_called_once_with(
            "30010096",
            pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            config_path="config/settings.yaml",
            skip_path_build=False,
            skip_path_scoring=False,
            query_family="date_window",
            base_date="2022-05-22",
        )
        mock_logger.info.assert_called_once_with(
            json.dumps(
                summarize_pipeline_result(expected),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

    @patch("scripts.run_similar_user_pipeline.LOGGER")
    @patch("scripts.run_similar_user_pipeline.parse_args")
    @patch("scripts.run_similar_user_pipeline.run_similar_user_pipeline")
    def test_pipeline_main_logs_full_result_when_requested(
        self,
        mock_run_pipeline: Mock,
        mock_parse_args: Mock,
        mock_logger: Mock,
    ) -> None:
        expected = {
            "patient_id": "30010096",
            "candidate_result": {"candidate_count": 1},
        }
        mock_parse_args.return_value = Mock(
            patient_id="30010096",
            pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            config="config/settings.yaml",
            skip_path_build=False,
            skip_path_scoring=False,
            query_family=None,
            base_date="2022-05-22",
            output_level="full",
        )
        mock_run_pipeline.return_value = expected

        exit_code = pipeline_main()

        self.assertEqual(exit_code, 0)
        mock_logger.info.assert_called_once_with(
            json.dumps(expected, ensure_ascii=False, indent=2, default=str)
        )

    @patch("scripts.run_similar_user_pipeline.LOGGER")
    @patch("scripts.run_similar_user_pipeline.parse_args")
    @patch("scripts.run_similar_user_pipeline.run_similar_user_pipeline")
    def test_pipeline_main_logs_score_summary_when_requested(
        self,
        mock_run_pipeline: Mock,
        mock_parse_args: Mock,
        mock_logger: Mock,
    ) -> None:
        expected = {
            "patient_id": "30010096",
            "candidate_result": {
                "candidate_count": 1,
                "candidates": [
                    {"patient_id": "20113562", "candidate_score": 2.232}
                ],
            },
        }
        mock_parse_args.return_value = Mock(
            patient_id="30010096",
            pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            config="config/settings.yaml",
            skip_path_build=False,
            skip_path_scoring=False,
            query_family=None,
            base_date="2022-05-22",
            output_level="scores",
        )
        mock_run_pipeline.return_value = expected

        exit_code = pipeline_main()

        self.assertEqual(exit_code, 0)
        mock_logger.info.assert_called_once_with(
            json.dumps(
                summarize_pipeline_result(expected, output_level="scores"),
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )

    def test_summarize_pipeline_result_keeps_only_candidate_summary(self) -> None:
        result = {
            "patient_id": "40",
            "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            "config_path": "config/settings.yaml",
            "skip_path_build": False,
            "skip_path_scoring": True,
            "base_date": "2022-05-22",
            "window_days": 14,
            "elapsed_seconds": 2.345,
            "path_generation": {
                "path_window": {
                    "base_date": "2022-05-22",
                    "start_date": "2022-05-08",
                    "end_date": "2022-05-22",
                    "window_days": 14,
                    "range_semantics": "[start_date, end_date)",
                },
                "path_count": 230,
            },
            "candidate_result": {
                "patient_id": "40",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "candidate_top_k": 10,
                "path_count": 230,
                "scored_path_count": 50,
                "retrieval_context": {
                    "path_window": {
                        "base_date": "2022-05-22",
                        "start_date": "2022-05-08",
                        "end_date": "2022-05-22",
                        "window_days": 14,
                        "range_semantics": "[start_date, end_date)",
                    },
                    "candidate_scope": "long text",
                },
                "candidate_count": 1,
                "candidates": [
                    {
                        "patient_id": "20113562",
                        "candidate_score": 2.232,
                        "match_count": 3,
                        "best_score": 95.0,
                        "avg_score": 90.0,
                        "score_details": {"large": "payload"},
                    }
                ],
            },
        }

        summary = summarize_pipeline_result(result)

        self.assertNotIn("candidate_result", summary)
        self.assertEqual(
            summary["candidate_summary"],
            {
                "patient_id": "40",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "candidate_top_k": 10,
                "path_count": 230,
                "scored_path_count": 50,
                "path_window": {
                    "base_date": "2022-05-22",
                    "start_date": "2022-05-08",
                    "end_date": "2022-05-22",
                    "window_days": 14,
                    "range_semantics": "[start_date, end_date)",
                },
                "candidate_count": 1,
                "candidate_ids": ["20113562"],
            },
        )
        self.assertEqual(summary["elapsed_seconds"], 2.345)
        self.assertTrue(summary["skip_path_scoring"])

    def test_summarize_pipeline_result_includes_all_candidate_ids(self) -> None:
        result = {
            "patient_id": "40",
            "candidate_result": {
                "candidate_count": 3,
                "candidates": [
                    {"patient_id": "20113562", "candidate_score": 2.2},
                    {"patient_id": "20113563", "candidate_score": 2.1},
                    {"patient_id": "20113564", "candidate_score": 2.0},
                ],
            },
        }

        summary = summarize_pipeline_result(result)

        self.assertEqual(
            summary["candidate_summary"]["candidate_ids"],
            ["20113562", "20113563", "20113564"],
        )

    def test_summarize_pipeline_result_can_include_candidate_scores(self) -> None:
        result = {
            "patient_id": "40",
            "candidate_result": {
                "candidate_count": 2,
                "candidates": [
                    {
                        "patient_id": "20113562",
                        "candidate_score": 2.2,
                        "score_details": {"large": "payload"},
                    },
                    {"patient_id": "20113563", "candidate_score": 2.1},
                ],
            },
        }

        summary = summarize_pipeline_result(result, output_level="scores")

        self.assertEqual(
            summary["candidate_summary"]["candidates"],
            [
                {"patient_id": "20113562", "candidate_score": 2.2},
                {"patient_id": "20113563", "candidate_score": 2.1},
            ],
        )
        self.assertNotIn("candidate_ids", summary["candidate_summary"])


def _write_user_cache_config(
    root: Path,
    *,
    refresh_candidate_base_date_on_hit: bool = True,
    patient_scored_paths_valid_days: int | None = None,
    direct_scored_paths_valid_days: int | None = None,
    topk_candidates_stale_valid_days: int | None = None,
) -> Path:
    config_path = root / "settings.yaml"
    config_path.write_text(
        "\n".join(
            [
                "graph_path_limit:",
                "  bands:",
                "    - per_g: 1",
                "patient_path:",
                "  window_days: 14",
                "score_pattern_paths:",
                "  top_k: 150",
                "candidate_ranking:",
                "  patterns:",
                "    - patient_game_patient",
                "  candidate_top_k: 10",
                "  total_score_match_top_k: 3",
                "  disease_course_window_days: 14",
                "  scoring:",
                "    common_game_score_similarity: false",
                "    game_similarity_with_diversity_score: false",
                "    disease_course_secondary_ability: true",
                "    set_same:",
                "      disease: false",
                "      symptom: false",
                "      unknown: false",
                "user_cache:",
                "  enabled: true",
                f'  sqlite_path: "{root / "user_cache" / "cache_index.sqlite"}"',
                *(
                    [f"  patient_scored_paths_valid_days: {patient_scored_paths_valid_days}"]
                    if patient_scored_paths_valid_days is not None
                    else []
                ),
                *(
                    [f"  direct_scored_paths_valid_days: {direct_scored_paths_valid_days}"]
                    if direct_scored_paths_valid_days is not None
                    else []
                ),
                "  topk_candidates_valid_days: 7",
                *(
                    [
                        "  topk_candidates_stale_valid_days: "
                        f"{topk_candidates_stale_valid_days}"
                    ]
                    if topk_candidates_stale_valid_days is not None
                    else []
                ),
                "  refresh_candidate_base_date_on_hit: "
                f"{str(refresh_candidate_base_date_on_hit).lower()}",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _candidate_result(
    *,
    cache_context: dict[str, object],
    user_cache_context: dict[str, object],
) -> dict[str, object]:
    return {
        "source_id": "30010096",
        "source_parameter": "patient_id",
        "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
        "patterns": ["PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"],
        "candidate_top_k": 10,
        "path_count": 3,
        "scored_path_count": 3,
        "retrieval_context": {"score_end_date": "2024-01-31"},
        "cache_context": cache_context,
        "user_cache_context": user_cache_context,
        "user_cache_hit": False,
        "candidate_count": 1,
        "pre_score_candidate_count": 1,
        "disease_course_available_count": 1,
        "disease_course_missing_count": 0,
        "candidates": [
            {
                "patient_id": "20113562",
                "candidate_score": 2.5,
                "score_details": {
                    "disease_course_secondary_ability": {
                        "score": 2.5,
                        "candidate_base_date": "2024-01-30",
                    }
                },
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
