"""Tests for direct-entity-only task prediction helpers."""

from __future__ import annotations

import unittest

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


if __name__ == "__main__":
    unittest.main()
