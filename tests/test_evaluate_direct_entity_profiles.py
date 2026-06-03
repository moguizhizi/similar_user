"""Tests for direct-entity profile evaluation helpers."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from scripts.evaluate_direct_entity_profiles import evaluate_profile


class EvaluateDirectEntityProfilesTest(unittest.TestCase):
    @patch("scripts.evaluate_direct_entity_profiles.validate_training_task_recommendation")
    @patch("scripts.evaluate_direct_entity_profiles.predict_training_tasks_unified")
    def test_evaluate_profile_unified_mode_records_route(
        self,
        mock_predict_unified: Mock,
        mock_validate: Mock,
    ) -> None:
        mock_predict_unified.return_value = {
            "route": "direct_entity_path",
            "patient_exists": False,
            "result": {
                "patient_id": "non_patient_1",
                "training_task_prediction": {
                    "predicted_training_tasks": [{"game_id": "433"}],
                    "candidate_training_tasks": [{"game_id": "433"}],
                },
            },
        }
        mock_validate.return_value = {
            "status": "success",
            "validation_mode": "score_api",
            "actual_task_count": 0,
            "matched_task_count": 0,
            "matched_game_ids": [],
        }

        detail = evaluate_profile(
            {
                "patient_id": "non_patient_1",
                "base_date": "2026-05-25",
                "age": 66,
                "education": "本科",
                "gender": "男",
                "disease_ids": ["AU_DIS_0029"],
            },
            config_path="config/settings.yaml",
            scored_paths_dir="data/scored_pattern_paths",
            task_top_k=7,
            use_llm=False,
            prediction_mode="unified",
            validation_mode="score_api",
            score_url="http://localhost",
            csv_path="data/algorithm_request_results.csv",
            timeout_seconds=1.0,
        )

        self.assertEqual(detail["route"], "direct_entity_path")
        self.assertEqual(detail["patient_exists"], False)
        self.assertEqual(detail["predicted_game_ids"], ["433"])
        mock_predict_unified.assert_called_once()


if __name__ == "__main__":
    unittest.main()
