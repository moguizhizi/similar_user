"""Tests for the training-task prediction CLI workflow."""

from __future__ import annotations

import json
import unittest
from unittest.mock import Mock, patch

from scripts import predict_training_tasks


class PredictTrainingTasksScriptTest(unittest.TestCase):
    @patch("scripts.predict_training_tasks.run_training_task_prediction")
    @patch("scripts.predict_training_tasks.run_similar_user_pipeline")
    def test_run_end_to_end_prediction_builds_candidates_then_predicts_tasks(
        self,
        mock_run_pipeline: Mock,
        mock_run_prediction: Mock,
    ) -> None:
        pipeline_result = {
            "patient_id": "40",
            "candidate_result": {"candidates": [{"patient_id": "201"}]},
        }
        prediction_result = {
            "patient_id": "40",
            "predicted_training_tasks": [{"game_id": "1"}],
        }
        mock_run_pipeline.return_value = pipeline_result
        mock_run_prediction.return_value = prediction_result

        result = predict_training_tasks.run_end_to_end_training_task_prediction(
            "40",
            base_date="2022-05-22",
            window_days=14,
            pattern="PATTERN",
            config_path="config/custom.yaml",
            skip_path_build=True,
            task_top_k=3,
            use_llm=False,
            include_prompt=True,
        )

        self.assertEqual(
            result,
            {
                "patient_id": "40",
                "similar_user_pipeline": pipeline_result,
                "training_task_prediction": prediction_result,
            },
        )
        mock_run_pipeline.assert_called_once_with(
            "40",
            pattern="PATTERN",
            config_path="config/custom.yaml",
            skip_path_build=True,
            base_date="2022-05-22",
            window_days=14,
        )
        mock_run_prediction.assert_called_once_with(
            pipeline_result,
            base_date="2022-05-22",
            window_days=14,
            config_path="config/custom.yaml",
            task_top_k=3,
            use_llm=False,
            include_prompt=True,
        )

    def test_summarize_prediction_result_reads_nested_prediction_for_ids(self) -> None:
        result = predict_training_tasks.summarize_prediction_result(
            {
                "patient_id": "40",
                "similar_user_pipeline": {"patient_id": "40"},
                "training_task_prediction": {
                    "patient_id": "40",
                    "predicted_training_tasks": [
                        {"game_id": "1"},
                        {"game_id": "2"},
                    ],
                },
            },
            output_level="ids",
        )

        self.assertEqual(
            result,
            {
                "patient_id": "40",
                "predicted_training_task_ids": ["1", "2"],
            },
        )

    def test_summarize_prediction_result_keeps_full_end_to_end_payload(self) -> None:
        payload = {
            "patient_id": "40",
            "similar_user_pipeline": {"patient_id": "40"},
            "training_task_prediction": {"patient_id": "40"},
        }

        result = predict_training_tasks.summarize_prediction_result(
            payload,
            output_level="full",
        )

        self.assertIs(result, payload)

    @patch("scripts.predict_training_tasks.LOGGER")
    @patch("scripts.predict_training_tasks.parse_args")
    @patch("scripts.predict_training_tasks.run_end_to_end_training_task_prediction")
    def test_main_runs_end_to_end_prediction_from_patient_id(
        self,
        mock_run_end_to_end: Mock,
        mock_parse_args: Mock,
        mock_logger: Mock,
    ) -> None:
        end_to_end_result = {
            "patient_id": "40",
            "similar_user_pipeline": {"patient_id": "40"},
            "training_task_prediction": {
                "patient_id": "40",
                "predicted_training_tasks": [
                    {
                        "game_id": "1",
                        "game_name": "任务A",
                        "confidence": 0.9,
                    }
                ],
            },
        }
        mock_parse_args.return_value = Mock(
            patient_id="40",
            base_date="2022-05-22",
            window_days=14,
            pattern="PATTERN",
            config="config/settings.yaml",
            skip_path_build=True,
            task_top_k=5,
            dry_run=True,
            include_prompt=False,
            output_level="scores",
        )
        mock_run_end_to_end.return_value = end_to_end_result

        exit_code = predict_training_tasks.main()

        self.assertEqual(exit_code, 0)
        mock_run_end_to_end.assert_called_once_with(
            "40",
            base_date="2022-05-22",
            window_days=14,
            pattern="PATTERN",
            config_path="config/settings.yaml",
            skip_path_build=True,
            task_top_k=5,
            use_llm=False,
            include_prompt=False,
        )
        mock_logger.info.assert_called_once_with(
            json.dumps(
                {
                    "patient_id": "40",
                    "predicted_training_tasks": [
                        {
                            "game_id": "1",
                            "game_name": "任务A",
                            "confidence": 0.9,
                        }
                    ],
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )


if __name__ == "__main__":
    unittest.main()
