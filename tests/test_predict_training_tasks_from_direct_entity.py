"""Tests for direct-entity-only task prediction helpers."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from scripts.predict_training_tasks_from_direct_entity import (
    _score_direct_entity_paths_with_auto_refresh,
    normalize_direct_entity_education,
    normalize_direct_entity_gender,
    predict_training_tasks_from_direct_entity,
    resolve_direct_entity_names,
)
from src.similar_user.services.similarity import SimilarUserCandidateService


class PredictTrainingTasksFromDirectEntityTest(unittest.TestCase):
    def test_normalizes_direct_entity_demographic_codes(self) -> None:
        self.assertEqual(normalize_direct_entity_gender(1), "男")
        self.assertEqual(normalize_direct_entity_gender("2"), "女")
        self.assertEqual(normalize_direct_entity_education(15), "高中")
        self.assertEqual(normalize_direct_entity_education("22"), "大专")
        self.assertEqual(normalize_direct_entity_education("硕士"), "研究生")

    def test_aggregate_direct_entity_candidates_ranks_by_direct_scores(self) -> None:
        result = SimilarUserCandidateService().aggregate_candidates_from_direct_entity_scored_result(
            {
                "source_id": "201231885555",
                "source_parameter": "manual_profile",
                "path_count": 3,
                "scored_path_count": 3,
                "scores": [
                    {
                        "pattern": "DISEASE_TASKSET_PATIENT",
                        "patient_id": "P1",
                        "path_index": 0,
                        "score": {"total_score": 80.0},
                    },
                    {
                        "pattern": "SYMPTOM_TASKSET_PATIENT",
                        "patient_id": "P2",
                        "path_index": 1,
                        "score": {"total_score": 95.0},
                    },
                    {
                        "pattern": "UNKNOWN_TASKSET_PATIENT",
                        "patient_id": "P1",
                        "path_index": 2,
                        "score": {"total_score": 90.0},
                    },
                ],
            },
            candidate_top_k=10,
        )

        self.assertEqual(result["source_id"], "201231885555")
        self.assertEqual(result["candidate_count"], 2)
        self.assertEqual(
            [candidate["patient_id"] for candidate in result["candidates"]],
            ["P2", "P1"],
        )
        self.assertEqual(result["candidates"][1]["match_count"], 2)
        self.assertEqual(result["candidates"][1]["best_score"], 90.0)
        self.assertEqual(result["candidates"][1]["avg_score"], 85.0)

    def test_resolve_direct_entity_names_groups_matches_and_unresolved(self) -> None:
        resolver = Mock()
        resolver.resolve_names.return_value = {
            "resolved": [
                {
                    "input_name": "注意缺陷多动障碍",
                    "entity_type": "disease",
                    "entity_id": "AU_DIS_0002",
                    "entity_name": "注意缺陷多动障碍",
                },
                {
                    "input_name": "注意缺陷多动障碍",
                    "entity_type": "symptom",
                    "entity_id": "AU_SYM_0007",
                    "entity_name": "注意缺陷多动障碍",
                },
            ],
            "unresolved": [
                {
                    "input_name": "未知疾病",
                    "reason": "not_found_in_kg",
                }
            ],
        }

        result = resolve_direct_entity_names(
            resolver,
            [" 注意缺陷多动障碍 ", "未知疾病", "注意缺陷多动障碍"],
        )

        self.assertEqual(
            result["resolved"],
            [
                {
                    "input_name": "注意缺陷多动障碍",
                    "entity_type": "disease",
                    "entity_id": "AU_DIS_0002",
                    "entity_name": "注意缺陷多动障碍",
                },
                {
                    "input_name": "注意缺陷多动障碍",
                    "entity_type": "symptom",
                    "entity_id": "AU_SYM_0007",
                    "entity_name": "注意缺陷多动障碍",
                },
            ],
        )
        self.assertEqual(
            result["unresolved"],
            [
                {
                    "input_name": "未知疾病",
                    "reason": "not_found_in_kg",
                }
            ],
        )
        resolver.resolve_names.assert_called_once_with(
            [" 注意缺陷多动障碍 ", "未知疾病", "注意缺陷多动障碍"]
        )

    @patch("scripts.predict_training_tasks_from_direct_entity.DirectEntityFallbackPredictionService")
    @patch("scripts.predict_training_tasks_from_direct_entity.UserService")
    @patch("scripts.predict_training_tasks_from_direct_entity.KgRepository")
    @patch("scripts.predict_training_tasks_from_direct_entity.Neo4jClient")
    @patch("scripts.predict_training_tasks_from_direct_entity.resolve_direct_entity_names")
    @patch("scripts.predict_training_tasks_from_direct_entity._score_direct_entity_paths_with_auto_refresh")
    def test_predict_falls_back_when_profile_field_is_missing(
        self,
        mock_score_paths: Mock,
        mock_resolve_names: Mock,
        mock_neo4j_client: Mock,
        mock_repository: Mock,
        mock_user_service: Mock,
        mock_fallback_service_class: Mock,
    ) -> None:
        mock_client_context = Mock()
        mock_client_context.__enter__ = Mock(return_value=Mock())
        mock_client_context.__exit__ = Mock(return_value=False)
        mock_neo4j_client.from_config.return_value = mock_client_context
        mock_fallback_service = Mock()
        mock_fallback_service.predict.return_value = {
            "prediction_status": "success",
            "fallback_used": True,
            "fallback_reason": "missing_education",
            "fallback_source": "profile_matched_tasks",
            "prediction_failure_stage": "input",
            "prediction_failure_reason": "missing_education",
            "candidate_source": {"fallback_level": "profile_matched_tasks"},
            "predicted_training_tasks": [{"game_id": "433"}],
        }
        mock_fallback_service_class.return_value = mock_fallback_service

        result = predict_training_tasks_from_direct_entity(
            patient_id="non_patient_1",
            base_date="2026-05-25",
            age=66,
            education="None",
            gender="男",
            disease_names=["认知-其他"],
            config_path="config/settings.yaml",
            use_llm=False,
        )

        self.assertEqual(
            result["training_task_prediction"]["fallback_reason"],
            "missing_education",
        )
        self.assertEqual(result["direct_entity_scoring"]["reason"], "missing_education")
        self.assertFalse(result["direct_entity_scoring"]["should_score"])
        mock_resolve_names.assert_not_called()
        mock_score_paths.assert_not_called()
        mock_repository.assert_called_once()
        mock_user_service.assert_called_once()
        mock_fallback_service.predict.assert_called_once()
        self.assertIsNone(mock_fallback_service.predict.call_args.kwargs["education"])

    @patch("scripts.predict_training_tasks_from_direct_entity.TrainingTaskPredictionService")
    @patch("scripts.predict_training_tasks_from_direct_entity.UserService")
    @patch("scripts.predict_training_tasks_from_direct_entity.KgRepository")
    @patch("scripts.predict_training_tasks_from_direct_entity.Neo4jClient")
    @patch("scripts.predict_training_tasks_from_direct_entity._score_direct_entity_paths_with_auto_refresh")
    @patch("scripts.predict_training_tasks_from_direct_entity.load_cached_topk_candidate_result")
    @patch("scripts.predict_training_tasks_from_direct_entity.load_direct_path_source_entries_for_cache")
    def test_predict_uses_topk_cache_before_loading_raw_paths(
        self,
        mock_source_entries: Mock,
        mock_load_topk: Mock,
        mock_score_paths: Mock,
        mock_neo4j_client: Mock,
        mock_repository: Mock,
        mock_user_service: Mock,
        mock_prediction_service_class: Mock,
    ) -> None:
        mock_source_entries.return_value = (
            [
                {
                    "pattern": "DISEASE_TASKSET_PATIENT",
                    "source_id": "D1",
                    "base_date": "2026-05-25",
                    "window_days": 180,
                    "path_key": "base_2026-05-25_window_180_directcfg_abcdef12",
                    "direct_path_limit": 1000,
                }
            ],
            [],
            "user_cache",
        )
        mock_load_topk.return_value = {
            "source_id": "non_patient_1",
            "source_parameter": "manual_profile",
            "candidate_count": 1,
            "candidates": [{"patient_id": "P1"}],
            "user_cache_hit": True,
            "user_cache_data_path": "cached.detail.json",
        }
        mock_client_context = Mock()
        mock_client_context.__enter__ = Mock(return_value=Mock())
        mock_client_context.__exit__ = Mock(return_value=False)
        mock_neo4j_client.from_config.return_value = mock_client_context
        mock_prediction_service = Mock()
        mock_prediction_service.predict_from_direct_entity_candidates.return_value = {
            "predicted_training_tasks": [{"game_id": "433"}],
            "candidate_training_tasks": [{"game_id": "433"}],
        }
        mock_prediction_service_class.return_value = mock_prediction_service

        result = predict_training_tasks_from_direct_entity(
            patient_id="non_patient_1",
            base_date="2026-05-25",
            age=66,
            education="本科",
            gender="男",
            disease_ids=["D1"],
            config_path="config/settings.yaml",
            use_llm=False,
        )

        self.assertEqual(result["direct_entity_candidate_result"]["user_cache_hit"], True)
        mock_load_topk.assert_called_once()
        mock_score_paths.assert_not_called()
        mock_repository.assert_called_once()
        mock_user_service.assert_called_once()
        service_kwargs = mock_prediction_service_class.call_args.kwargs
        self.assertIn("unlock_train_candidate_tasks_enabled", service_kwargs)
        self.assertIn("algorithm_request_results_csv", service_kwargs)
        mock_prediction_service.predict_from_direct_entity_candidates.assert_called_once()

    @patch("scripts.predict_training_tasks_from_direct_entity.build_direct_entity_paths")
    @patch("scripts.predict_training_tasks_from_direct_entity.score_direct_entity_paths")
    def test_score_direct_entity_paths_auto_refreshes_missing_raw_paths(
        self,
        mock_score: Mock,
        mock_build_paths: Mock,
    ) -> None:
        mock_score.side_effect = [
            {
                "should_score": True,
                "missing_sources": [
                    {"pattern": "DISEASE_TASKSET_PATIENT", "source_id": "D1"},
                    {"pattern": "SYMPTOM_TASKSET_PATIENT", "source_id": "S1"},
                ],
                "scores": [],
            },
            {
                "should_score": True,
                "missing_sources": [],
                "scores": [{"patient_id": "P1", "score": {"total_score": 95.0}}],
            },
        ]

        result = _score_direct_entity_paths_with_auto_refresh(
            config_path="config/settings.yaml",
            patient_id="201231885555",
            base_date="2026-05-25",
            age=66,
            education="本科",
            gender="男",
            disease_ids=["D1"],
            symptom_ids=["S1"],
            unknown_ids=[],
            top_k=150,
        )

        self.assertEqual(result["missing_sources"], [])
        self.assertEqual(mock_score.call_count, 2)
        mock_build_paths.assert_called_once_with(
            config_path="config/settings.yaml",
            disease_ids=["D1"],
            symptom_ids=["S1"],
            unknown_ids=[],
        )


if __name__ == "__main__":
    unittest.main()
