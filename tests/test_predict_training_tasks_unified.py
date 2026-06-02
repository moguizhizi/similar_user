"""Tests for unified patient/direct-entity prediction routing."""

from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from scripts.predict_training_tasks_unified import predict_training_tasks_unified


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

    @patch("scripts.predict_training_tasks_unified._patient_exists")
    def test_missing_patient_requires_direct_entity_profile(
        self,
        mock_patient_exists: Mock,
    ) -> None:
        mock_patient_exists.return_value = False

        with self.assertRaisesRegex(ValueError, "requires: age"):
            predict_training_tasks_unified(
                patient_id="non_patient_1",
                base_date="2026-05-25",
                education="本科",
                gender="男",
                disease_ids=["AU_DIS_0029"],
                config_path="config/settings.yaml",
                use_llm=False,
            )


if __name__ == "__main__":
    unittest.main()
