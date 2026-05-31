"""Tests for direct-entity-only task prediction helpers."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from scripts.predict_training_tasks_from_direct_entity import (
    _score_direct_entity_paths_with_auto_refresh,
    normalize_direct_entity_education,
    normalize_direct_entity_gender,
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
