"""Tests for unified patient/direct-entity prediction routing."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from scripts.predict_training_tasks_unified import (
    predict_training_tasks_unified,
    summarize_unified_prediction_result,
)


class PredictTrainingTasksUnifiedTest(unittest.TestCase):
    @patch("scripts.predict_training_tasks_unified.run_end_to_end_training_task_prediction")
    @patch("scripts.predict_training_tasks_unified._patient_exists")
    def test_routes_existing_patient_to_patient_path(
        self,
        mock_patient_exists: Mock,
        mock_patient_prediction: Mock,
    ) -> None:
        mock_patient_exists.return_value = True
        mock_patient_prediction.return_value = {
            "patient_id": "P1",
            "training_task_prediction": {"predicted_training_tasks": []},
        }

        result = predict_training_tasks_unified(
            patient_id="P1",
            base_date="2026-05-25",
            config_path="config/settings.yaml",
            use_llm=False,
        )

        self.assertEqual(result["route"], "patient_path")
        self.assertEqual(result["patient_exists"], True)
        mock_patient_prediction.assert_called_once()

    @patch("scripts.predict_training_tasks_unified.predict_training_tasks_from_direct_entity")
    @patch("scripts.predict_training_tasks_unified._patient_exists")
    def test_routes_missing_patient_to_direct_entity_path(
        self,
        mock_patient_exists: Mock,
        mock_direct_prediction: Mock,
    ) -> None:
        mock_patient_exists.return_value = False
        mock_direct_prediction.return_value = {
            "patient_id": "non_patient_1",
            "training_task_prediction": {"predicted_training_tasks": []},
        }

        result = predict_training_tasks_unified(
            patient_id="non_patient_1",
            base_date="2026-05-25",
            age=66,
            education="本科",
            gender="男",
            disease_ids=["AU_DIS_0029"],
            config_path="config/settings.yaml",
            use_llm=False,
        )

        self.assertEqual(result["route"], "direct_entity_path")
        self.assertEqual(result["patient_exists"], False)
        mock_direct_prediction.assert_called_once()

    @patch("scripts.predict_training_tasks_unified.predict_training_tasks_from_direct_entity")
    @patch("scripts.predict_training_tasks_unified._patient_exists")
    def test_missing_patient_allows_incomplete_profile_fallback(
        self,
        mock_patient_exists: Mock,
        mock_direct_prediction: Mock,
    ) -> None:
        mock_patient_exists.return_value = False
        mock_direct_prediction.return_value = {
            "patient_id": "non_patient_1",
            "training_task_prediction": {
                "fallback_used": True,
                "fallback_reason": "missing_age",
                "predicted_training_tasks": [{"game_id": "312"}],
            },
        }

        result = predict_training_tasks_unified(
            patient_id="non_patient_1",
            base_date="2026-05-25",
            education="本科",
            gender="男",
            disease_ids=["AU_DIS_0029"],
            config_path="config/settings.yaml",
            use_llm=False,
        )

        self.assertEqual(result["route"], "direct_entity_path")
        self.assertEqual(result["patient_exists"], False)
        mock_direct_prediction.assert_called_once()
        call_kwargs = mock_direct_prediction.call_args.kwargs
        self.assertIsNone(call_kwargs["age"])
        self.assertEqual(call_kwargs["education"], "本科")

    @patch("scripts.predict_training_tasks_unified.predict_training_tasks_from_direct_entity")
    @patch("scripts.predict_training_tasks_unified._patient_exists")
    def test_missing_patient_allows_profile_only_fallback(
        self,
        mock_patient_exists: Mock,
        mock_direct_prediction: Mock,
    ) -> None:
        mock_patient_exists.return_value = False
        mock_direct_prediction.return_value = {
            "patient_id": "non_patient_1",
            "training_task_prediction": {
                "fallback_used": True,
                "fallback_reason": "missing_entity_input",
                "predicted_training_tasks": [{"game_id": "312"}],
            },
        }

        result = predict_training_tasks_unified(
            patient_id="non_patient_1",
            base_date="2026-05-25",
            age=66,
            education="本科",
            gender="男",
            config_path="config/settings.yaml",
            use_llm=False,
        )

        self.assertEqual(result["route"], "direct_entity_path")
        self.assertEqual(result["patient_exists"], False)
        mock_direct_prediction.assert_called_once()
        call_kwargs = mock_direct_prediction.call_args.kwargs
        self.assertEqual(call_kwargs["disease_ids"], [])
        self.assertEqual(call_kwargs["disease_names"], [])
        self.assertEqual(call_kwargs["symptom_ids"], [])
        self.assertEqual(call_kwargs["unknown_ids"], [])

    @patch("scripts.predict_training_tasks_unified.predict_training_tasks_from_direct_entity")
    @patch("scripts.predict_training_tasks_unified._patient_exists")
    def test_missing_patient_preserves_missing_education_for_fallback(
        self,
        mock_patient_exists: Mock,
        mock_direct_prediction: Mock,
    ) -> None:
        mock_patient_exists.return_value = False
        mock_direct_prediction.return_value = {
            "patient_id": "non_patient_1",
            "training_task_prediction": {
                "fallback_used": True,
                "fallback_reason": "missing_education",
                "predicted_training_tasks": [{"game_id": "312"}],
            },
        }

        result = predict_training_tasks_unified(
            patient_id="non_patient_1",
            base_date="2026-05-25",
            age=18,
            gender="男",
            disease_names=["认知-其他"],
            config_path="config/settings.yaml",
            use_llm=False,
        )

        self.assertEqual(result["route"], "direct_entity_path")
        self.assertEqual(result["patient_exists"], False)
        call_kwargs = mock_direct_prediction.call_args.kwargs
        self.assertIsNone(call_kwargs["education"])
        self.assertEqual(call_kwargs["disease_names"], ["认知-其他"])

    def test_patient_path_ids_summary_includes_route(self) -> None:
        summary = summarize_unified_prediction_result(
            {
                "route": "patient_path",
                "patient_exists": True,
                "result": {
                    "patient_id": "P1",
                    "training_task_prediction": {
                        "patient_id": "P1",
                        "predicted_training_tasks": [{"game_id": "433"}],
                    },
                },
            },
            output_level="ids",
        )

        self.assertEqual(
            summary,
            {
                "patient_id": "P1",
                "predicted_training_task_ids": ["433"],
                "route": "patient_path",
                "patient_exists": True,
            },
        )

    def test_direct_entity_ids_summary_includes_route(self) -> None:
        summary = summarize_unified_prediction_result(
            {
                "route": "direct_entity_path",
                "patient_exists": False,
                "result": {
                    "patient_id": "non_patient_1",
                    "training_task_prediction": {
                        "predicted_training_tasks": [{"game_id": "312"}],
                    },
                },
            },
            output_level="ids",
        )

        self.assertEqual(
            summary,
            {
                "patient_id": "non_patient_1",
                "predicted_training_task_ids": ["312"],
                "route": "direct_entity_path",
                "patient_exists": False,
            },
        )


if __name__ == "__main__":
    unittest.main()
