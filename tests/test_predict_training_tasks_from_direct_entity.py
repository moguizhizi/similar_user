"""Tests for direct-entity-only task prediction helpers."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from scripts.predict_training_tasks_from_direct_entity import (
    resolve_direct_entity_names,
)
from src.similar_user.services.similarity import SimilarUserCandidateService


class PredictTrainingTasksFromDirectEntityTest(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
