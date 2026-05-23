"""Tests for the training-task prediction CLI workflow."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import predict_training_tasks


class PredictTrainingTasksScriptTest(unittest.TestCase):
    def test_write_prompt_to_file_uses_patient_and_date_in_filename(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            prompt_path = predict_training_tasks.write_prompt_to_file(
                {
                    "training_task_prediction": {
                        "patient_id": "40",
                        "llm_prompt": "prompt body",
                    }
                },
                output_dir=temp_dir,
                base_date="2022-05-22",
            )

            self.assertEqual(
                prompt_path,
                Path(temp_dir)
                / "training_task_prompt_patient_40_base_date_2022-05-22.txt",
            )
            self.assertEqual(prompt_path.read_text(encoding="utf-8"), "prompt body\n")

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
            query_family="date_window",
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
            query_family="date_window",
            base_date="2022-05-22",
            window_days=14,
        )
        mock_run_prediction.assert_called_once_with(
            pipeline_result,
            base_date="2022-05-22",
            config_path="config/custom.yaml",
            task_top_k=3,
            use_llm=False,
            include_prompt=True,
        )

    @patch("scripts.predict_training_tasks.TrainingTaskPredictionService")
    @patch("scripts.predict_training_tasks.UserService")
    @patch("scripts.predict_training_tasks.Neo4jClient.from_config")
    @patch("scripts.predict_training_tasks.load_query_settings")
    def test_run_training_task_prediction_reads_disease_course_window_from_config(
        self,
        mock_load_query_settings: Mock,
        mock_from_config: Mock,
        mock_user_service_cls: Mock,
        mock_service_cls: Mock,
    ) -> None:
        mock_load_query_settings.return_value = Mock(
            candidate_ranking=Mock(disease_course_window_days=365),
            training_task_prediction=Mock(prompt_candidate_compression_enabled=True),
        )
        mock_client_context = Mock()
        mock_client_context.__enter__ = Mock(return_value=Mock())
        mock_client_context.__exit__ = Mock(return_value=None)
        mock_from_config.return_value = mock_client_context
        mock_service = Mock()
        mock_service.predict_from_pipeline_result.return_value = {"patient_id": "40"}
        mock_service_cls.return_value = mock_service

        result = predict_training_tasks.run_training_task_prediction(
            {"patient_id": "40", "candidate_result": {"candidates": []}},
            base_date="2022-05-22",
            config_path="config/custom.yaml",
            task_top_k=3,
            use_llm=False,
            include_prompt=True,
        )

        self.assertEqual(result, {"patient_id": "40"})
        mock_load_query_settings.assert_called_once_with("config/custom.yaml")
        mock_service.predict_from_pipeline_result.assert_called_once_with(
            {"patient_id": "40", "candidate_result": {"candidates": []}},
            base_date="2022-05-22",
            window_days=365,
            task_top_k=3,
            use_llm=False,
            include_prompt=True,
        )
        mock_user_service_cls.assert_called_once()

    @patch("scripts.predict_training_tasks.Neo4jClient.from_config")
    @patch("scripts.predict_training_tasks.load_query_settings")
    def test_run_training_task_prediction_requires_disease_course_window(
        self,
        mock_load_query_settings: Mock,
        mock_from_config: Mock,
    ) -> None:
        mock_load_query_settings.return_value = Mock(
            candidate_ranking=Mock(disease_course_window_days=None),
            training_task_prediction=Mock(prompt_candidate_compression_enabled=True),
        )

        with self.assertRaisesRegex(
            ValueError,
            "candidate_ranking disease_course_window_days is required",
        ):
            predict_training_tasks.run_training_task_prediction(
                {"patient_id": "40", "candidate_result": {"candidates": []}},
                base_date="2022-05-22",
                config_path="config/custom.yaml",
                use_llm=False,
            )

        mock_from_config.assert_not_called()

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
    @patch("scripts.predict_training_tasks.write_prompt_to_file")
    def test_main_runs_end_to_end_prediction_from_patient_id(
        self,
        mock_write_prompt_to_file: Mock,
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
            query_family="date_window",
            task_top_k=5,
            dry_run=True,
            include_prompt=False,
            no_save_prompt=True,
            prompt_output_dir="data/prompts",
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
            query_family="date_window",
            task_top_k=5,
            use_llm=False,
            include_prompt=False,
        )
        mock_write_prompt_to_file.assert_not_called()
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

    @patch("scripts.predict_training_tasks.LOGGER")
    @patch("scripts.predict_training_tasks.parse_args")
    @patch("scripts.predict_training_tasks.run_end_to_end_training_task_prediction")
    @patch("scripts.predict_training_tasks.write_prompt_to_file")
    def test_main_saves_prompt_by_default(
        self,
        mock_write_prompt_to_file: Mock,
        mock_run_end_to_end: Mock,
        mock_parse_args: Mock,
        mock_logger: Mock,
    ) -> None:
        mock_parse_args.return_value = Mock(
            patient_id="40",
            base_date="2022-05-22",
            window_days=14,
            pattern="PATTERN",
            config="config/settings.yaml",
            skip_path_build=True,
            query_family=None,
            task_top_k=5,
            dry_run=True,
            include_prompt=False,
            no_save_prompt=False,
            prompt_output_dir="data/custom-prompts",
            output_level="full",
        )
        mock_run_end_to_end.return_value = {
            "patient_id": "40",
            "training_task_prediction": {
                "patient_id": "40",
                "llm_prompt": "prompt body",
            },
        }
        mock_write_prompt_to_file.return_value = Path(
            "data/custom-prompts/training_task_prompt_patient_40_base_date_2022-05-22.txt"
        )

        exit_code = predict_training_tasks.main()

        self.assertEqual(exit_code, 0)
        mock_run_end_to_end.assert_called_once_with(
            "40",
            base_date="2022-05-22",
            window_days=14,
            pattern="PATTERN",
            config_path="config/settings.yaml",
            skip_path_build=True,
            query_family=None,
            task_top_k=5,
            use_llm=False,
            include_prompt=True,
        )
        mock_write_prompt_to_file.assert_called_once_with(
            mock_run_end_to_end.return_value,
            output_dir="data/custom-prompts",
            base_date="2022-05-22",
        )
        self.assertEqual(mock_logger.info.call_count, 2)


if __name__ == "__main__":
    unittest.main()
