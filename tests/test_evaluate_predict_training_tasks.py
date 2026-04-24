"""Tests for same-day training-task prediction evaluation."""

from __future__ import annotations

import sys
import unittest
from unittest.mock import Mock, patch

from scripts import evaluate_predict_training_tasks


class EvaluatePredictTrainingTasksTest(unittest.TestCase):
    def test_parse_args_accepts_single_patient_id(self) -> None:
        with patch.object(
            sys,
            "argv",
            [
                "evaluate_predict_training_tasks.py",
                "--patient-id",
                "40",
                "--base-date",
                "2022-05-22",
                "--window-days",
                "14",
            ],
        ):
            args = evaluate_predict_training_tasks.parse_args()

        self.assertEqual(args.patient_id, "40")
        self.assertIsNone(args.patient_ids_file)
        self.assertEqual(args.base_date, "2022-05-22")
        self.assertEqual(args.window_days, 14)

    def test_evaluate_prediction_sets_ignores_ranking_and_dedupes_ids(self) -> None:
        result = evaluate_predict_training_tasks.evaluate_prediction_sets(
            ["A", "B", "A", "C"],
            ["C", "D", "B"],
        )

        self.assertEqual(result["matched_game_ids"], ["B", "C"])
        self.assertTrue(result["task_hit"])
        self.assertEqual(result["precision"], 0.6667)
        self.assertEqual(result["recall"], 0.6667)
        self.assertEqual(result["f1"], 0.6667)

    def test_summarize_evaluation_details_calculates_set_metrics(self) -> None:
        summary = evaluate_predict_training_tasks.summarize_evaluation_details(
            [
                {
                    "status": "success_evaluated",
                    "task_hit": True,
                    "precision": 0.5,
                    "recall": 1.0,
                    "f1": 0.6667,
                    "predicted_task_count": 3,
                    "actual_task_count": 2,
                    "matched_task_count": 2,
                    "elapsed_seconds": 1.0,
                },
                {
                    "status": "success_evaluated",
                    "task_hit": False,
                    "precision": 0.0,
                    "recall": 0.0,
                    "f1": 0.0,
                    "predicted_task_count": 1,
                    "actual_task_count": 2,
                    "matched_task_count": 0,
                    "elapsed_seconds": 3.0,
                },
                {
                    "status": "success_not_evaluable",
                    "elapsed_seconds": 2.0,
                },
                {
                    "status": "failed",
                    "elapsed_seconds": 4.0,
                },
            ]
        )

        self.assertEqual(summary["total_count"], 4)
        self.assertEqual(summary["success_count"], 3)
        self.assertEqual(summary["failed_count"], 1)
        self.assertEqual(summary["not_evaluable_count"], 1)
        self.assertEqual(summary["evaluated_count"], 2)
        self.assertEqual(summary["coverage_rate"], 0.75)
        self.assertEqual(summary["evaluable_rate"], 0.5)
        self.assertEqual(summary["task_hit_rate"], 0.5)
        self.assertEqual(summary["micro_precision"], 0.5)
        self.assertEqual(summary["micro_recall"], 0.5)
        self.assertEqual(summary["micro_f1"], 0.5)
        self.assertEqual(summary["macro_precision"], 0.25)
        self.assertEqual(summary["macro_recall"], 0.5)
        self.assertEqual(summary["macro_f1"], 0.3333)
        self.assertEqual(summary["avg_predicted_task_count"], 2.0)
        self.assertEqual(summary["avg_actual_task_count"], 2.0)
        self.assertEqual(summary["avg_elapsed_seconds"], 2.5)
        self.assertEqual(summary["p95_elapsed_seconds"], 4.0)

    @patch("scripts.evaluate_predict_training_tasks.run_end_to_end_training_task_prediction")
    def test_evaluate_patient_uses_base_date_as_actual_label_window(
        self,
        mock_predict: Mock,
    ) -> None:
        mock_predict.return_value = {
            "training_task_prediction": {
                "predicted_training_tasks": [
                    {"game_id": "1"},
                    {"game_id": "2"},
                ]
            }
        }
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-05-22", "g": {"id": "2", "name": "任务B"}},
            {"trainingDate": "2022-05-22", "g": {"id": "3", "name": "任务C"}},
        ]

        detail = evaluate_predict_training_tasks.evaluate_patient(
            "40",
            base_date="2022-05-22",
            window_days=14,
            user_service=user_service,
            pattern="PATTERN",
            config_path="config/settings.yaml",
            skip_path_build=True,
            task_top_k=5,
            use_llm=False,
        )

        self.assertEqual(detail["status"], "success_evaluated")
        self.assertEqual(detail["predicted_game_ids"], ["1", "2"])
        self.assertEqual(detail["actual_game_ids"], ["2", "3"])
        self.assertEqual(detail["matched_game_ids"], ["2"])
        self.assertTrue(detail["task_hit"])
        self.assertEqual(detail["precision"], 0.5)
        self.assertEqual(detail["recall"], 0.5)
        mock_predict.assert_called_once_with(
            "40",
            base_date="2022-05-22",
            window_days=14,
            pattern="PATTERN",
            config_path="config/settings.yaml",
            skip_path_build=True,
            task_top_k=5,
            use_llm=False,
        )
        user_service.get_patient_training_task_history_by_date_window.assert_called_once_with(
            "40",
            "2022-05-22",
            "2022-05-23",
        )

    @patch("scripts.evaluate_predict_training_tasks.run_end_to_end_training_task_prediction")
    def test_evaluate_patient_skips_prediction_without_actual_tasks(
        self,
        mock_predict: Mock,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.return_value = []

        detail = evaluate_predict_training_tasks.evaluate_patient(
            "40",
            base_date="2022-05-22",
            window_days=14,
            user_service=user_service,
            use_llm=False,
        )

        self.assertEqual(detail["status"], "success_not_evaluable")
        self.assertEqual(detail["reason"], "no_actual_tasks_on_base_date")
        self.assertEqual(detail["predicted_game_ids"], [])
        self.assertEqual(detail["actual_game_ids"], [])
        self.assertIsNone(detail["task_hit"])
        self.assertEqual(detail["predicted_task_count"], 0)
        mock_predict.assert_not_called()
        user_service.get_patient_training_task_history_by_date_window.assert_called_once_with(
            "40",
            "2022-05-22",
            "2022-05-23",
        )

    @patch("scripts.evaluate_predict_training_tasks.Neo4jClient")
    @patch("scripts.evaluate_predict_training_tasks.KgRepository")
    @patch("scripts.evaluate_predict_training_tasks.UserService")
    @patch("scripts.evaluate_predict_training_tasks.evaluate_patient")
    def test_run_batch_evaluation_applies_limit_after_loading_patient_ids(
        self,
        mock_evaluate_patient: Mock,
        mock_user_service_class: Mock,
        mock_repository_class: Mock,
        mock_client_class: Mock,
    ) -> None:
        mock_client = Mock()
        mock_client_class.from_config.return_value.__enter__.return_value = mock_client
        mock_user_service = Mock()
        mock_user_service.get_patient_ids.return_value = ["40", "41", "42"]
        mock_user_service_class.return_value = mock_user_service
        mock_evaluate_patient.side_effect = [
            {"patient_id": "40", "status": "success_evaluated"},
            {"patient_id": "41", "status": "success_evaluated"},
        ]

        details = evaluate_predict_training_tasks.run_batch_evaluation(
            None,
            base_date="2022-05-22",
            window_days=14,
            config_path="config/settings.yaml",
            use_llm=False,
            limit=2,
        )

        self.assertEqual(
            details,
            [
                {"patient_id": "40", "status": "success_evaluated"},
                {"patient_id": "41", "status": "success_evaluated"},
            ],
        )
        mock_repository_class.assert_called_once_with(
            client=mock_client,
            config_path=evaluate_predict_training_tasks.Path("config/settings.yaml"),
        )
        mock_user_service.get_patient_ids.assert_called_once_with()
        self.assertEqual(mock_evaluate_patient.call_count, 2)
        self.assertEqual(
            [
                call_args.args[0]
                for call_args in mock_evaluate_patient.call_args_list
            ],
            ["40", "41"],
        )

    @patch("scripts.evaluate_predict_training_tasks.Neo4jClient")
    @patch("scripts.evaluate_predict_training_tasks.KgRepository")
    @patch("scripts.evaluate_predict_training_tasks.UserService")
    @patch("scripts.evaluate_predict_training_tasks.evaluate_patient")
    def test_run_batch_evaluation_can_load_only_base_date_active_patients(
        self,
        mock_evaluate_patient: Mock,
        mock_user_service_class: Mock,
        mock_repository_class: Mock,
        mock_client_class: Mock,
    ) -> None:
        mock_client = Mock()
        mock_client_class.from_config.return_value.__enter__.return_value = mock_client
        mock_user_service = Mock()
        mock_user_service.get_patient_ids_with_training_on_date.return_value = [
            "40",
            "41",
        ]
        mock_user_service_class.return_value = mock_user_service
        mock_evaluate_patient.side_effect = [
            {"patient_id": "40", "status": "success_evaluated"},
            {"patient_id": "41", "status": "success_evaluated"},
        ]

        details = evaluate_predict_training_tasks.run_batch_evaluation(
            None,
            base_date="2022-05-22",
            window_days=14,
            config_path="config/settings.yaml",
            use_llm=False,
            active_on_base_date=True,
        )

        self.assertEqual(
            details,
            [
                {"patient_id": "40", "status": "success_evaluated"},
                {"patient_id": "41", "status": "success_evaluated"},
            ],
        )
        mock_repository_class.assert_called_once_with(
            client=mock_client,
            config_path=evaluate_predict_training_tasks.Path("config/settings.yaml"),
        )
        mock_user_service.get_patient_ids_with_training_on_date.assert_called_once_with(
            "2022-05-22",
        )
        mock_user_service.get_patient_ids.assert_not_called()

    def test_resolve_patient_ids_prefers_explicit_patient_ids(self) -> None:
        user_service = Mock()

        result = evaluate_predict_training_tasks.resolve_patient_ids_for_evaluation(
            user_service,
            patient_ids=["40"],
            base_date="2022-05-22",
            active_on_base_date=True,
        )

        self.assertEqual(result, ["40"])
        user_service.get_patient_ids.assert_not_called()
        user_service.get_patient_ids_with_training_on_date.assert_not_called()

    def test_run_batch_evaluation_rejects_non_positive_limit(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "limit must be a positive integer, got 0.",
        ):
            evaluate_predict_training_tasks.run_batch_evaluation(
                ["40"],
                base_date="2022-05-22",
                window_days=14,
                limit=0,
            )

    @patch("scripts.evaluate_predict_training_tasks.run_batch_evaluation")
    def test_main_rejects_patient_id_and_file_together(
        self,
        mock_run_batch_evaluation: Mock,
    ) -> None:
        with patch.object(
            sys,
            "argv",
            [
                "evaluate_predict_training_tasks.py",
                "patients.txt",
                "--patient-id",
                "40",
                "--base-date",
                "2022-05-22",
                "--window-days",
                "14",
            ],
        ):
            exit_code = evaluate_predict_training_tasks.main()

        self.assertEqual(exit_code, 1)
        mock_run_batch_evaluation.assert_not_called()


if __name__ == "__main__":
    unittest.main()
