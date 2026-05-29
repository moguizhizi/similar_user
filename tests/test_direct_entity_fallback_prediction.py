"""Tests for direct-entity task prediction fallback."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.similar_user.services.direct_entity_fallback_prediction import (
    DirectEntityFallbackPredictionService,
)


class DirectEntityFallbackPredictionTest(unittest.TestCase):
    def test_predict_fills_from_profile_global_and_random(self) -> None:
        user_service = Mock()
        user_service.get_profile_matched_exclusive_tasks.side_effect = [
            [
                {
                    "g": {"id": "G1", "name": "画像任务1", "任务类型": "专属"},
                    "support_count": 10,
                    "patient_count": 3,
                    "latest_training_date": "2026-05-20",
                }
            ],
            [],
            [],
            [],
        ]
        user_service.get_global_popular_exclusive_tasks.return_value = [
            {
                "g": {"id": "G2", "name": "热门任务2", "任务类型": "专属"},
                "support_count": 8,
                "patient_count": 2,
                "latest_training_date": "2026-05-21",
            },
            {
                "g": {"id": "G1", "name": "重复任务", "任务类型": "专属"},
                "support_count": 6,
                "patient_count": 1,
                "latest_training_date": "2026-05-22",
            },
        ]
        user_service.get_distinct_training_games.return_value = [
            {"g": {"id": "G3", "name": "随机任务3"}},
            {"g": {"id": "G2", "name": "重复任务"}},
        ]

        result = DirectEntityFallbackPredictionService(user_service).predict(
            patient_id="P_NOT_IN_KG",
            base_date="2026-05-25",
            age="66",
            education="本科",
            gender="男",
            task_top_k=3,
            reason="missing_entity_input",
        )

        self.assertEqual(
            [task["game_id"] for task in result["predicted_training_tasks"]],
            ["G1", "G2", "G3"],
        )
        self.assertEqual(
            result["candidate_source"]["levels_used"],
            [
                "profile_matched_tasks",
                "global_popular_tasks",
                "deterministic_random_tasks",
            ],
        )
        self.assertEqual(
            result["predicted_training_tasks"][0]["fallback_level"],
            "profile_matched_tasks",
        )
        self.assertEqual(result["target_profile"]["age"], 66)

    def test_predict_uses_global_when_profile_has_no_match(self) -> None:
        user_service = Mock()
        user_service.get_profile_matched_exclusive_tasks.return_value = []
        user_service.get_global_popular_exclusive_tasks.return_value = [
            {
                "g": {"id": "G2", "name": "热门任务2"},
                "support_count": 8,
                "patient_count": 2,
            }
        ]
        user_service.get_distinct_training_games.return_value = []

        result = DirectEntityFallbackPredictionService(user_service).predict(
            patient_id="P1",
            base_date="2026-05-25",
            age=None,
            education=None,
            gender=None,
            task_top_k=1,
        )

        self.assertEqual(
            result["candidate_source"]["fallback_level"],
            "global_popular_tasks",
        )
        self.assertEqual(result["predicted_training_tasks"][0]["game_id"], "G2")


if __name__ == "__main__":
    unittest.main()
