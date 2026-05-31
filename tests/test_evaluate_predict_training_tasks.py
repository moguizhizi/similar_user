"""Tests for same-day training-task prediction evaluation."""

from __future__ import annotations

import sys
import tempfile
import unittest
import json
from unittest.mock import Mock, patch

from scripts import evaluate_predict_training_tasks
from scripts.run_similar_user_pipeline import EmptyPathResultsError


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
                "--query-family",
                "date_window",
            ],
        ):
            args = evaluate_predict_training_tasks.parse_args()

        self.assertEqual(args.patient_id, "40")
        self.assertEqual(args.base_date, "2022-05-22")
        self.assertEqual(args.query_family, "date_window")
        self.assertEqual(
            args.analysis_file,
            "predict_training_tasks_analysis.json",
        )
        self.assertEqual(args.patient_list_dir, "data/patient_ids")

    def test_build_patient_ids_file_from_base_date_uses_export_path_rule(self) -> None:
        patient_ids_file = (
            evaluate_predict_training_tasks.build_patient_ids_file_from_base_date(
                base_date="2023-10-15",
                patient_list_dir="data/patient_ids",
            )
        )

        self.assertEqual(
            patient_ids_file,
            evaluate_predict_training_tasks.Path(
                "data/patient_ids/base_2023-10-15/patients_active_2023-10-15.txt"
            ),
        )

    def test_write_analysis_output_writes_json_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            analysis_path = evaluate_predict_training_tasks.write_analysis_output(
                {"evaluated_count": 2},
                output_dir=temp_dir,
                analysis_file="analysis.json",
            )

            self.assertEqual(
                json.loads(analysis_path.read_text(encoding="utf-8")),
                {"evaluated_count": 2},
            )

    def test_write_score_curl_commands_writes_kg_and_csv_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            curl_path = evaluate_predict_training_tasks.write_score_curl_commands(
                [
                    {
                        "patient_id": "40",
                        "base_date": "2022-05-22",
                        "training_task_score_validation": {
                            "kg_score_exchange": {"request_curl": "curl kg"},
                            "csv_score_exchange": {"request_curl": "curl csv"},
                        },
                    }
                ],
                output_dir=temp_dir,
            )

            self.assertEqual(
                curl_path,
                evaluate_predict_training_tasks.Path(temp_dir)
                / "training_task_score_requests.sh",
            )
            content = curl_path.read_text(encoding="utf-8")
            self.assertIn("source=kg", content)
            self.assertIn("curl kg", content)
            self.assertIn("source=csv", content)
            self.assertIn("curl csv", content)

    def test_build_coverage_diagnostics_uses_raw_similar_user_counts_for_overlap(
        self,
    ) -> None:
        diagnostics = evaluate_predict_training_tasks.build_coverage_diagnostics(
            predicted_game_ids=["A"],
            actual_game_ids=["D"],
            result={
                "training_task_prediction": {
                    "raw_similar_user_game_counts": [
                        {"game_id": "A"},
                        {"game_id": "B"},
                        {"game_id": "C"},
                        {"game_id": "D"},
                    ],
                    "similar_user_game_counts": [
                        {"game_id": "A"},
                        {"game_id": "B"},
                    ],
                    "candidate_training_tasks": [
                        {"game_id": "A"},
                        {"game_id": "B"},
                        {"game_id": "E"},
                    ],
                }
            },
        )

        self.assertEqual(
            diagnostics["similar_user_candidate_task_overlap"],
            {
                "similar_user_task_count": 4,
                "candidate_task_count": 3,
                "intersection_task_count": 2,
                "coverage": 0.5,
                "candidate_supported_rate": 0.6667,
            },
        )
        self.assertEqual(
            diagnostics["similar_user_game_counts"]["actual_missing_count"],
            1,
        )

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
                    "similar_user_game_counts_task_count": 10,
                    "candidate_training_tasks_count": 4,
                    "coverage_diagnostics": {
                        "similar_user_game_counts": {
                            "predicted_missing_count": 1,
                            "predicted_total_count": 3,
                            "actual_missing_count": 0,
                            "actual_total_count": 2,
                        },
                        "candidate_training_tasks": {
                            "predicted_missing_count": 0,
                            "predicted_total_count": 3,
                            "actual_missing_count": 1,
                            "actual_total_count": 2,
                        },
                        "similar_user_candidate_task_overlap": {
                            "similar_user_task_count": 10,
                            "candidate_task_count": 4,
                            "intersection_task_count": 3,
                            "coverage": 0.3,
                            "candidate_supported_rate": 0.75,
                        },
                    },
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
                    "similar_user_game_counts_task_count": 20,
                    "candidate_training_tasks_count": 6,
                    "coverage_diagnostics": {
                        "similar_user_game_counts": {
                            "predicted_missing_count": 1,
                            "predicted_total_count": 1,
                            "actual_missing_count": 2,
                            "actual_total_count": 2,
                        },
                        "candidate_training_tasks": {
                            "predicted_missing_count": 0,
                            "predicted_total_count": 1,
                            "actual_missing_count": 1,
                            "actual_total_count": 2,
                        },
                        "similar_user_candidate_task_overlap": {
                            "similar_user_task_count": 20,
                            "candidate_task_count": 6,
                            "intersection_task_count": 6,
                            "coverage": 0.3,
                            "candidate_supported_rate": 1.0,
                        },
                    },
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
        self.assertEqual(summary["avg_similar_user_game_counts_task_count"], 15.0)
        self.assertEqual(summary["min_similar_user_game_counts_task_count"], 10)
        self.assertEqual(summary["max_similar_user_game_counts_task_count"], 20)
        self.assertEqual(summary["avg_candidate_training_tasks_count"], 5.0)
        self.assertEqual(summary["min_candidate_training_tasks_count"], 4)
        self.assertEqual(summary["max_candidate_training_tasks_count"], 6)
        self.assertEqual(summary["similar_user_game_counts_predicted_missing_rate"], 0.5)
        self.assertEqual(summary["similar_user_game_counts_actual_missing_rate"], 0.5)
        self.assertEqual(summary["candidate_training_tasks_predicted_missing_rate"], 0.0)
        self.assertEqual(summary["candidate_training_tasks_actual_missing_rate"], 0.5)
        self.assertEqual(summary["similar_user_candidate_task_coverage"], 0.3)
        self.assertEqual(summary["candidate_task_supported_rate"], 0.875)
        self.assertEqual(
            summary["avg_similar_user_candidate_task_intersection_count"],
            4.5,
        )
        self.assertEqual(summary["avg_elapsed_seconds"], 2.5)
        self.assertEqual(summary["p95_elapsed_seconds"], 4.0)

    def test_summarize_evaluation_details_calculates_score_metrics(self) -> None:
        summary = evaluate_predict_training_tasks.summarize_evaluation_details(
            [
                {
                    "status": "success_evaluated",
                    "validation_mode": "score",
                    "kg_avg_score": 65.0,
                    "csv_avg_score": 60.0,
                    "score_delta": 5.0,
                    "predicted_task_count": 2,
                    "actual_task_count": 0,
                    "matched_task_count": 0,
                    "similar_user_game_counts_task_count": 3,
                    "candidate_training_tasks_count": 2,
                    "coverage_diagnostics": {
                        "similar_user_game_counts": {
                            "predicted_missing_count": 0,
                            "predicted_total_count": 2,
                            "actual_missing_count": 0,
                            "actual_total_count": 0,
                        },
                        "candidate_training_tasks": {
                            "predicted_missing_count": 1,
                            "predicted_total_count": 2,
                            "actual_missing_count": 0,
                            "actual_total_count": 0,
                        },
                        "similar_user_candidate_task_overlap": {
                            "similar_user_task_count": 3,
                            "candidate_task_count": 2,
                            "intersection_task_count": 1,
                            "coverage": 0.3333,
                            "candidate_supported_rate": 0.5,
                        },
                    },
                    "elapsed_seconds": 1.0,
                },
                {
                    "status": "success_evaluated",
                    "validation_mode": "score",
                    "kg_avg_score": 70.0,
                    "csv_avg_score": 55.0,
                    "score_delta": 15.0,
                    "predicted_task_count": 2,
                    "actual_task_count": 0,
                    "matched_task_count": 0,
                    "similar_user_game_counts_task_count": 3,
                    "candidate_training_tasks_count": 2,
                    "coverage_diagnostics": {
                        "similar_user_game_counts": {
                            "predicted_missing_count": 0,
                            "predicted_total_count": 2,
                            "actual_missing_count": 0,
                            "actual_total_count": 0,
                        },
                        "candidate_training_tasks": {
                            "predicted_missing_count": 0,
                            "predicted_total_count": 2,
                            "actual_missing_count": 0,
                            "actual_total_count": 0,
                        },
                        "similar_user_candidate_task_overlap": {
                            "similar_user_task_count": 3,
                            "candidate_task_count": 2,
                            "intersection_task_count": 2,
                            "coverage": 0.6667,
                            "candidate_supported_rate": 1.0,
                        },
                    },
                    "elapsed_seconds": 1.0,
                },
            ]
        )

        self.assertEqual(summary["score_evaluated_count"], 2)
        self.assertEqual(summary["avg_kg_score"], 67.5)
        self.assertEqual(summary["avg_csv_score"], 57.5)
        self.assertEqual(summary["avg_score_delta"], 10.0)

    def test_analyze_evaluation_details_summarizes_rank_evidence(self) -> None:
        analysis = evaluate_predict_training_tasks.analyze_evaluation_details(
            [
                {
                    "patient_id": "40",
                    "status": "success_evaluated",
                    "task_hit": True,
                    "precision": 0.5,
                    "recall": 0.5,
                    "predicted_task_count": 2,
                    "actual_task_count": 2,
                    "matched_task_count": 1,
                    "matched_game_ids": ["B"],
                    "predicted_game_similar_user_counts": [
                        {
                            "game_id": "A",
                            "game_name": "任务A",
                            "similar_user_count_rank": 1,
                        },
                        {
                            "game_id": "B",
                            "game_name": "任务B",
                            "similar_user_count_rank": 3,
                        },
                    ],
                    "actual_game_similar_user_counts": [
                        {
                            "game_id": "B",
                            "game_name": "任务B",
                            "similar_user_count_rank": 3,
                        },
                        {
                            "game_id": "C",
                            "game_name": "任务C",
                            "similar_user_count_rank": 12,
                        },
                    ],
                    "similar_user_game_counts_task_count": 10,
                    "candidate_training_tasks_count": 4,
                    "coverage_diagnostics": {
                        "similar_user_game_counts": {
                            "predicted_missing_count": 0,
                            "predicted_total_count": 2,
                            "actual_missing_count": 0,
                            "actual_total_count": 2,
                        },
                        "candidate_training_tasks": {
                            "predicted_missing_count": 0,
                            "predicted_total_count": 2,
                            "actual_missing_count": 1,
                            "actual_total_count": 2,
                        },
                    },
                    "elapsed_seconds": 1.0,
                },
                {
                    "patient_id": "41",
                    "status": "success_evaluated",
                    "task_hit": False,
                    "precision": 0.0,
                    "recall": 0.0,
                    "predicted_task_count": 1,
                    "actual_task_count": 1,
                    "matched_task_count": 0,
                    "matched_game_ids": [],
                    "predicted_game_similar_user_counts": [
                        {
                            "game_id": "D",
                            "game_name": "任务D",
                            "similar_user_count_rank": 9,
                        },
                    ],
                    "actual_game_similar_user_counts": [
                        {
                            "game_id": "E",
                            "game_name": "任务E",
                            "similar_user_count_rank": None,
                        },
                    ],
                    "similar_user_game_counts_task_count": 20,
                    "candidate_training_tasks_count": 6,
                    "coverage_diagnostics": {
                        "similar_user_game_counts": {
                            "predicted_missing_count": 0,
                            "predicted_total_count": 1,
                            "actual_missing_count": 1,
                            "actual_total_count": 1,
                        },
                        "candidate_training_tasks": {
                            "predicted_missing_count": 0,
                            "predicted_total_count": 1,
                            "actual_missing_count": 1,
                            "actual_total_count": 1,
                        },
                    },
                    "elapsed_seconds": 2.0,
                },
                {"patient_id": "42", "status": "failed"},
            ]
        )

        self.assertEqual(analysis["evaluated_count"], 2)
        self.assertEqual(
            analysis["rank_stats"]["predicted"],
            {
                "count": 3,
                "min": 1,
                "p25": 1,
                "median": 3,
                "mean": 4.3333,
                "p75": 9,
                "max": 9,
            },
        )
        self.assertEqual(
            analysis["rank_buckets"]["predicted"],
            {"1-7": 2, "8-10": 1, "11-20": 0, "21-50": 0, "51+": 0},
        )
        self.assertEqual(
            analysis["rank_buckets"]["missed_actual"],
            {"1-7": 0, "8-10": 0, "11-20": 1, "21-50": 0, "51+": 0},
        )
        self.assertEqual(
            analysis["missing_from_similar_user_game_counts"],
            {"predicted_task_count": 0, "actual_task_count": 1},
        )
        self.assertEqual(
            analysis["coverage_diagnostics"]["similar_user_game_counts"],
            {
                "predicted_missing_count": 0,
                "predicted_total_count": 3,
                "predicted_missing_rate": 0.0,
                "actual_missing_count": 1,
                "actual_total_count": 3,
                "actual_missing_rate": 0.3333,
            },
        )
        self.assertEqual(
            analysis["coverage_diagnostics"]["candidate_training_tasks"],
            {
                "predicted_missing_count": 0,
                "predicted_total_count": 3,
                "predicted_missing_rate": 0.0,
                "actual_missing_count": 2,
                "actual_total_count": 3,
                "actual_missing_rate": 0.6667,
            },
        )
        self.assertEqual(
            analysis["similar_user_game_counts_task_count_stats"]["mean"],
            15.0,
        )
        self.assertEqual(
            analysis["candidate_training_tasks_count_stats"]["mean"],
            5.0,
        )
        self.assertEqual(
            analysis["per_patient"][0]["candidate_training_tasks_count"],
            4,
        )
        self.assertEqual(
            analysis["top_matched_games"],
            [{"game_id": "B", "game_name": "任务B", "count": 1}],
        )
        self.assertEqual(analysis["per_patient"][0]["actual_rank_max"], 12)

    @patch("scripts.evaluate_predict_training_tasks.load_query_settings")
    def test_build_experiment_config_records_window_settings(
        self,
        mock_load_query_settings: Mock,
    ) -> None:
        mock_load_query_settings.return_value = Mock(
            candidate_ranking=Mock(disease_course_window_days=180),
            score_pattern_paths=Mock(top_k=50),
            training_task_prediction=Mock(
                prompt_candidate_compression_enabled=True,
                prompt_template_name="TASK_PREDICTION_PROMPT_TEMPLATE_V1",
                similar_user_game_counts_weighting_enabled=True,
                similar_user_game_counts_weighted_sort_enabled=False,
            ),
            training_task_evaluation=Mock(
                validation_mode="set",
                workers=3,
                score_validation_url="http://score.test/training_task_score",
                algorithm_request_results_csv="/tmp/request_results.csv",
                score_validation_timeout=3.0,
            ),
        )

        config = evaluate_predict_training_tasks.build_experiment_config(
            base_date="2022-05-22",
            pattern="PATTERN",
            config_path="config/settings.yaml",
            skip_path_build=True,
            skip_path_scoring=True,
            query_family="date_window",
            task_top_k=7,
            use_llm=False,
            workers=3,
        )

        self.assertEqual(config["disease_course_window_days"], 180)
        self.assertEqual(config["scored_path_top_k"], 50)
        self.assertNotIn("fallback_candidate_task_window_days", config)
        self.assertNotIn("effective_candidate_task_window_days", config)
        self.assertEqual(config["base_date"], "2022-05-22")
        self.assertEqual(config["task_top_k"], 7)
        self.assertEqual(config["workers"], 3)
        self.assertTrue(config["skip_path_scoring"])
        self.assertFalse(config["use_llm"])
        self.assertEqual(
            config["prompt_template"],
            "TASK_PREDICTION_PROMPT_TEMPLATE_V1",
        )
        self.assertTrue(config["similar_user_game_counts_weighting_enabled"])
        self.assertFalse(config["similar_user_game_counts_weighted_sort_enabled"])
        mock_load_query_settings.assert_called_once_with("config/settings.yaml")

    def test_build_experiment_output_dir_uses_parameterized_subdir(self) -> None:
        output_dir = evaluate_predict_training_tasks.build_experiment_output_dir(
            "data/evaluation",
            {
                "base_date": "2022-05-22",
                "window_days": 14,
                "disease_course_window_days": 180,
                "task_top_k": 7,
                "query_family": "date_window",
                "use_llm": False,
            },
        )

        self.assertEqual(
            output_dir,
            evaluate_predict_training_tasks.Path(
                "data/evaluation/"
                "base_2022-05-22_window_14_dcw_180_topk_7_qf_date-window_dry_run"
            ),
        )

    @patch("scripts.evaluate_predict_training_tasks.load_query_settings")
    @patch("scripts.evaluate_predict_training_tasks.run_end_to_end_training_task_prediction")
    @patch("scripts.evaluate_predict_training_tasks.write_prompt_to_file")
    def test_evaluate_patient_uses_base_date_as_actual_label_window(
        self,
        mock_write_prompt: Mock,
        mock_predict: Mock,
        mock_load_query_settings: Mock,
    ) -> None:
        mock_load_query_settings.return_value = Mock(
            training_task_evaluation=Mock(validation_mode="set")
        )
        mock_predict.return_value = {
            "training_task_prediction": {
                "similar_user_game_counts": [
                    {"game_id": "2", "game_name": "任务B", "count": 4},
                    {"game_id": "4", "game_name": "任务D", "count": 1},
                ],
                "predicted_training_tasks": [
                    {"game_id": "1"},
                    {"game_id": "2"},
                ],
                "candidate_training_tasks": [
                    {"game_id": "1"},
                    {"game_id": "4"},
                ],
            }
        }
        mock_write_prompt.return_value = evaluate_predict_training_tasks.Path(
            "data/prompts/training_task_prompt_patient_40_base_date_2022-05-22.txt"
        )
        user_service = Mock()
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-05-22", "g": {"id": "2", "name": "任务B"}},
            {"trainingDate": "2022-05-22", "g": {"id": "3", "name": "任务C"}},
        ]

        detail = evaluate_predict_training_tasks.evaluate_patient(
            "40",
            base_date="2022-05-22",
            user_service=user_service,
            pattern="PATTERN",
            config_path="config/settings.yaml",
            skip_path_build=True,
            skip_path_scoring=True,
            query_family="date_window",
            task_top_k=5,
            use_llm=False,
        )

        self.assertEqual(detail["status"], "success_evaluated")
        self.assertEqual(detail["predicted_game_ids"], ["1", "2"])
        self.assertEqual(detail["candidate_training_tasks_count"], 2)
        self.assertEqual(
            detail["predicted_game_similar_user_counts"],
            [
                {
                    "game_id": "1",
                    "game_name": None,
                    "similar_user_count": 0,
                    "similar_user_count_rank": None,
                    "appears_in_similar_user_game_counts": False,
                },
                {
                    "game_id": "2",
                    "game_name": "任务B",
                    "similar_user_count": 4,
                    "similar_user_count_rank": 1,
                    "appears_in_similar_user_game_counts": True,
                },
            ],
        )
        self.assertEqual(detail["actual_game_ids"], ["2", "3"])
        self.assertEqual(detail["similar_user_game_counts_task_count"], 2)
        self.assertEqual(
            detail["coverage_diagnostics"],
            {
                "similar_user_game_counts": {
                    "predicted_missing_count": 1,
                    "predicted_total_count": 2,
                    "predicted_missing_rate": 0.5,
                    "actual_missing_count": 1,
                    "actual_total_count": 2,
                    "actual_missing_rate": 0.5,
                },
                "candidate_training_tasks": {
                    "predicted_missing_count": 1,
                    "predicted_total_count": 2,
                    "predicted_missing_rate": 0.5,
                    "actual_missing_count": 2,
                    "actual_total_count": 2,
                    "actual_missing_rate": 1.0,
                },
                "similar_user_candidate_task_overlap": {
                    "similar_user_task_count": 2,
                    "candidate_task_count": 2,
                    "intersection_task_count": 1,
                    "coverage": 0.5,
                    "candidate_supported_rate": 0.5,
                },
            },
        )
        self.assertEqual(
            detail["actual_game_similar_user_counts"],
            [
                {
                    "game_id": "2",
                    "game_name": "任务B",
                    "similar_user_count": 4,
                    "similar_user_count_rank": 1,
                    "appears_in_similar_user_game_counts": True,
                },
                {
                    "game_id": "3",
                    "game_name": None,
                    "similar_user_count": 0,
                    "similar_user_count_rank": None,
                    "appears_in_similar_user_game_counts": False,
                },
            ],
        )
        self.assertEqual(detail["matched_game_ids"], ["2"])
        self.assertTrue(detail["task_hit"])
        self.assertEqual(detail["precision"], 0.5)
        self.assertEqual(detail["recall"], 0.5)
        self.assertEqual(
            detail["prompt_path"],
            "data/prompts/training_task_prompt_patient_40_base_date_2022-05-22.txt",
        )
        mock_predict.assert_called_once_with(
            "40",
            base_date="2022-05-22",
            pattern="PATTERN",
            config_path="config/settings.yaml",
            skip_path_build=True,
            skip_path_scoring=True,
            query_family="date_window",
            task_top_k=5,
            use_llm=False,
            include_prompt=True,
        )
        mock_write_prompt.assert_called_once_with(
            mock_predict.return_value,
            output_dir=evaluate_predict_training_tasks.DEFAULT_PROMPT_OUTPUT_DIR,
            base_date="2022-05-22",
        )
        user_service.get_patient_exclusive_training_task_history_by_date_window.assert_called_once_with(
            "40",
            "2022-05-22",
            "2022-05-23",
        )

    @patch("scripts.evaluate_predict_training_tasks.load_query_settings")
    @patch("scripts.evaluate_predict_training_tasks.run_end_to_end_training_task_prediction")
    @patch("scripts.evaluate_predict_training_tasks.write_prompt_to_file")
    def test_evaluate_patient_skips_prediction_without_actual_tasks(
        self,
        mock_write_prompt: Mock,
        mock_predict: Mock,
        mock_load_query_settings: Mock,
    ) -> None:
        mock_load_query_settings.return_value = Mock(
            training_task_evaluation=Mock(validation_mode="set")
        )
        user_service = Mock()
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = []

        detail = evaluate_predict_training_tasks.evaluate_patient(
            "40",
            base_date="2022-05-22",
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
        mock_write_prompt.assert_not_called()
        user_service.get_patient_exclusive_training_task_history_by_date_window.assert_called_once_with(
            "40",
            "2022-05-22",
            "2022-05-23",
        )

    @patch("scripts.evaluate_predict_training_tasks.load_query_settings")
    @patch("scripts.evaluate_predict_training_tasks.validate_training_task_recommendation")
    @patch("scripts.evaluate_predict_training_tasks.run_end_to_end_training_task_prediction")
    @patch("scripts.evaluate_predict_training_tasks.write_prompt_to_file")
    def test_evaluate_patient_score_mode_uses_score_validation(
        self,
        mock_write_prompt: Mock,
        mock_predict: Mock,
        mock_validation: Mock,
        mock_load_query_settings: Mock,
    ) -> None:
        mock_load_query_settings.return_value = Mock(
            training_task_evaluation=Mock(
                validation_mode="score",
                score_validation_url="http://score.test/training_task_score",
                algorithm_request_results_csv="/tmp/request_results.csv",
                score_validation_timeout=3.0,
            )
        )
        mock_predict.return_value = {
            "patient_id": "40",
            "training_task_prediction": {
                "patient_id": "40",
                "predicted_training_tasks": [{"game_id": "1"}, {"game_id": "2"}],
                "similar_user_game_counts": [{"game_id": "1", "count": 3}],
                "candidate_training_tasks": [{"game_id": "1"}],
            },
        }
        mock_validation.return_value = {
            "status": "success_evaluated",
            "validation_mode": "score",
            "actual_task_count": 0,
            "matched_task_count": 0,
            "kg_avg_score": 65.0,
            "csv_avg_score": 60.0,
            "score_delta": 5.0,
        }
        user_service = Mock()

        detail = evaluate_predict_training_tasks.evaluate_patient(
            "40",
            base_date="2022-05-22",
            user_service=user_service,
            use_llm=False,
            save_prompt=False,
            config_path="config/settings.yaml",
        )

        self.assertEqual(detail["status"], "success_evaluated")
        self.assertEqual(detail["validation_mode"], "score")
        self.assertEqual(detail["kg_avg_score"], 65.0)
        self.assertEqual(detail["csv_avg_score"], 60.0)
        self.assertEqual(detail["score_delta"], 5.0)
        self.assertEqual(detail["predicted_game_ids"], ["1", "2"])
        user_service.get_patient_exclusive_training_task_history_by_date_window.assert_not_called()
        mock_validation.assert_called_once_with(
            validation_mode="score",
            prediction_result=mock_predict.return_value,
            patient_id="40",
            predicted_game_ids=["1", "2"],
            actual_game_ids=[],
            score_url="http://score.test/training_task_score",
            csv_path="/tmp/request_results.csv",
            timeout_seconds=3.0,
        )
        mock_load_query_settings.assert_called_once_with("config/settings.yaml")
        mock_write_prompt.assert_not_called()

    @patch("scripts.evaluate_predict_training_tasks.run_end_to_end_training_task_prediction")
    @patch("scripts.evaluate_predict_training_tasks.write_prompt_to_file")
    def test_evaluate_patient_marks_empty_paths_as_not_evaluable(
        self,
        mock_write_prompt: Mock,
        mock_predict: Mock,
    ) -> None:
        mock_predict.side_effect = EmptyPathResultsError("no paths")
        user_service = Mock()
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-05-22", "g": {"id": "2", "name": "任务B"}},
        ]

        detail = evaluate_predict_training_tasks.evaluate_patient(
            "40",
            base_date="2022-05-22",
            user_service=user_service,
            use_llm=False,
        )

        self.assertEqual(detail["status"], "success_not_evaluable")
        self.assertEqual(detail["reason"], "no_pattern_paths")
        self.assertEqual(detail["error_message"], "no paths")
        self.assertIsNone(detail["task_hit"])
        self.assertEqual(detail["predicted_task_count"], 0)
        mock_write_prompt.assert_not_called()

    @patch("scripts.evaluate_predict_training_tasks.run_end_to_end_training_task_prediction")
    @patch("scripts.evaluate_predict_training_tasks.write_prompt_to_file")
    def test_evaluate_patient_saves_prompt_from_prediction_failure(
        self,
        mock_write_prompt: Mock,
        mock_predict: Mock,
    ) -> None:
        error = RuntimeError("llm failed")
        error.llm_prompt = "prompt body"
        mock_predict.side_effect = error
        mock_write_prompt.return_value = evaluate_predict_training_tasks.Path(
            "data/prompts/training_task_prompt_patient_40_base_date_2022-05-22.txt"
        )
        user_service = Mock()
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-05-22", "g": {"id": "2", "name": "任务B"}},
        ]

        detail = evaluate_predict_training_tasks.evaluate_patient(
            "40",
            base_date="2022-05-22",
            user_service=user_service,
            use_llm=True,
        )

        self.assertEqual(detail["status"], "failed")
        self.assertEqual(detail["error_message"], "llm failed")
        self.assertEqual(
            detail["prompt_path"],
            "data/prompts/training_task_prompt_patient_40_base_date_2022-05-22.txt",
        )
        mock_write_prompt.assert_called_once_with(
            {
                "training_task_prediction": {
                    "patient_id": "40",
                    "llm_prompt": "prompt body",
                }
            },
            output_dir=evaluate_predict_training_tasks.DEFAULT_PROMPT_OUTPUT_DIR,
            base_date="2022-05-22",
        )

    @patch("scripts.evaluate_predict_training_tasks.Neo4jClient")
    @patch("scripts.evaluate_predict_training_tasks.KgRepository")
    @patch("scripts.evaluate_predict_training_tasks.UserService")
    @patch("scripts.evaluate_predict_training_tasks.evaluate_patient")
    def test_run_batch_evaluation_applies_limit_to_explicit_patient_ids(
        self,
        mock_evaluate_patient: Mock,
        mock_user_service_class: Mock,
        mock_repository_class: Mock,
        mock_client_class: Mock,
    ) -> None:
        mock_client = Mock()
        mock_client_class.from_config.return_value.__enter__.return_value = mock_client
        mock_user_service = Mock()
        mock_user_service_class.return_value = mock_user_service
        mock_evaluate_patient.side_effect = [
            {"patient_id": "40", "status": "success_evaluated"},
            {"patient_id": "41", "status": "success_evaluated"},
        ]

        details = evaluate_predict_training_tasks.run_batch_evaluation(
            ["40", "41", "42"],
            base_date="2022-05-22",
            config_path="config/settings.yaml",
            use_llm=False,
            query_family="date_window",
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
        mock_user_service.get_patient_ids.assert_not_called()
        self.assertEqual(mock_evaluate_patient.call_count, 2)
        self.assertEqual(
            [
                call_args.args[0]
                for call_args in mock_evaluate_patient.call_args_list
            ],
            ["40", "41"],
        )
        self.assertEqual(
            [
                call_args.kwargs["query_family"]
                for call_args in mock_evaluate_patient.call_args_list
            ],
            ["date_window", "date_window"],
        )

    def test_resolve_patient_ids_prefers_explicit_patient_ids(self) -> None:
        user_service = Mock()

        result = evaluate_predict_training_tasks.resolve_patient_ids_for_evaluation(
            user_service,
            patient_ids=["40"],
            base_date="2022-05-22",
        )

        self.assertEqual(result, ["40"])
        user_service.get_patient_ids.assert_not_called()

    def test_run_batch_evaluation_rejects_non_positive_limit(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "limit must be a positive integer, got 0.",
        ):
            evaluate_predict_training_tasks.run_batch_evaluation(
                ["40"],
                base_date="2022-05-22",
                limit=0,
            )

    def test_run_batch_evaluation_rejects_non_positive_workers(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "workers must be a positive integer, got 0.",
        ):
            evaluate_predict_training_tasks.run_batch_evaluation(
                ["40"],
                base_date="2022-05-22",
                workers=0,
            )

    def test_run_batch_evaluation_rejects_missing_patient_ids(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "patient_ids must contain at least one patient ID.",
        ):
            evaluate_predict_training_tasks.run_batch_evaluation(
                [],
                base_date="2022-05-22",
            )

    @patch("scripts.evaluate_predict_training_tasks.Neo4jClient")
    @patch("scripts.evaluate_predict_training_tasks.KgRepository")
    @patch("scripts.evaluate_predict_training_tasks.UserService")
    @patch("scripts.evaluate_predict_training_tasks.evaluate_patient")
    def test_run_batch_evaluation_with_workers_preserves_patient_order(
        self,
        mock_evaluate_patient: Mock,
        mock_user_service_class: Mock,
        mock_repository_class: Mock,
        mock_client_class: Mock,
    ) -> None:
        mock_client = Mock()
        mock_client_class.from_config.return_value.__enter__.return_value = mock_client
        mock_user_service = Mock()
        mock_user_service_class.return_value = mock_user_service

        def evaluate_side_effect(patient_id: str, **_: object) -> dict[str, object]:
            return {"patient_id": patient_id, "status": "success_evaluated"}

        mock_evaluate_patient.side_effect = evaluate_side_effect

        details = evaluate_predict_training_tasks.run_batch_evaluation(
            ["40", "41", "42"],
            base_date="2022-05-22",
            config_path="config/settings.yaml",
            use_llm=False,
            workers=2,
        )

        self.assertEqual(
            [detail["patient_id"] for detail in details],
            ["40", "41", "42"],
        )
        self.assertEqual(mock_evaluate_patient.call_count, 3)
        mock_repository_class.assert_called_once_with(
            client=mock_client,
            config_path=evaluate_predict_training_tasks.Path("config/settings.yaml"),
        )

    @patch("scripts.evaluate_predict_training_tasks.write_analysis_output")
    @patch("scripts.evaluate_predict_training_tasks.write_outputs")
    @patch("scripts.evaluate_predict_training_tasks.build_experiment_config")
    @patch("scripts.evaluate_predict_training_tasks.export_patient_ids_with_training_on_date")
    @patch("scripts.evaluate_predict_training_tasks.run_batch_evaluation")
    def test_main_reads_patient_ids_from_base_date_file(
        self,
        mock_run_batch_evaluation: Mock,
        mock_export_patient_ids: Mock,
        mock_build_experiment_config: Mock,
        mock_write_outputs: Mock,
        mock_write_analysis_output: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            patient_ids_file = (
                evaluate_predict_training_tasks.Path(temp_dir)
                / "base_2023-10-15"
                / "patients_active_2023-10-15.txt"
            )
            patient_ids_file.parent.mkdir(parents=True)
            patient_ids_file.write_text("40\n41\n", encoding="utf-8")
            mock_run_batch_evaluation.return_value = [
                {
                    "status": "success_evaluated",
                    "task_hit": True,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1": 1.0,
                    "predicted_task_count": 1,
                    "actual_task_count": 1,
                    "matched_task_count": 1,
                    "elapsed_seconds": 1.0,
                }
            ]
            mock_build_experiment_config.return_value = {
                "base_date": "2023-10-15",
                "window_days": 14,
                "disease_course_window_days": 14,
                "task_top_k": 7,
                "query_family": None,
                "use_llm": False,
            }
            mock_write_outputs.return_value = (
                evaluate_predict_training_tasks.Path("summary.json"),
                evaluate_predict_training_tasks.Path("details.jsonl"),
            )
            mock_write_analysis_output.return_value = (
                evaluate_predict_training_tasks.Path("analysis.json")
            )

            with patch.object(
                sys,
                "argv",
                [
                    "evaluate_predict_training_tasks.py",
                    "--patient-list-dir",
                    temp_dir,
                    "--base-date",
                    "2023-10-15",
                    "--dry-run",
                ],
            ):
                exit_code = evaluate_predict_training_tasks.main()

        self.assertEqual(exit_code, 0)
        mock_export_patient_ids.assert_not_called()
        mock_run_batch_evaluation.assert_called_once()
        self.assertEqual(mock_run_batch_evaluation.call_args.args[0], ["40", "41"])

    @patch("scripts.evaluate_predict_training_tasks.write_analysis_output")
    @patch("scripts.evaluate_predict_training_tasks.write_outputs")
    @patch("scripts.evaluate_predict_training_tasks.build_experiment_config")
    @patch("scripts.evaluate_predict_training_tasks.export_patient_ids_with_training_on_date")
    @patch("scripts.evaluate_predict_training_tasks.run_batch_evaluation")
    def test_main_exports_base_date_file_when_missing(
        self,
        mock_run_batch_evaluation: Mock,
        mock_export_patient_ids: Mock,
        mock_build_experiment_config: Mock,
        mock_write_outputs: Mock,
        mock_write_analysis_output: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            patient_ids_file = (
                evaluate_predict_training_tasks.Path(temp_dir)
                / "base_2023-10-15"
                / "patients_active_2023-10-15.txt"
            )

            def export_side_effect(**_: object) -> None:
                patient_ids_file.parent.mkdir(parents=True)
                patient_ids_file.write_text("40\n41\n", encoding="utf-8")

            mock_export_patient_ids.side_effect = export_side_effect
            mock_run_batch_evaluation.return_value = [
                {
                    "status": "success_evaluated",
                    "task_hit": True,
                    "precision": 1.0,
                    "recall": 1.0,
                    "f1": 1.0,
                    "predicted_task_count": 1,
                    "actual_task_count": 1,
                    "matched_task_count": 1,
                    "elapsed_seconds": 1.0,
                }
            ]
            mock_build_experiment_config.return_value = {
                "base_date": "2023-10-15",
                "window_days": 14,
                "disease_course_window_days": 14,
                "task_top_k": 7,
                "query_family": None,
                "use_llm": False,
            }
            mock_write_outputs.return_value = (
                evaluate_predict_training_tasks.Path("summary.json"),
                evaluate_predict_training_tasks.Path("details.jsonl"),
            )
            mock_write_analysis_output.return_value = (
                evaluate_predict_training_tasks.Path("analysis.json")
            )

            with patch.object(
                sys,
                "argv",
                [
                    "evaluate_predict_training_tasks.py",
                    "--patient-list-dir",
                    temp_dir,
                    "--base-date",
                    "2023-10-15",
                    "--config",
                    "config/settings.yaml",
                    "--dry-run",
                ],
            ):
                exit_code = evaluate_predict_training_tasks.main()

        self.assertEqual(exit_code, 0)
        mock_export_patient_ids.assert_called_once_with(
            base_date="2023-10-15",
            config_path="config/settings.yaml",
            output_dir=temp_dir,
        )
        mock_run_batch_evaluation.assert_called_once()
        self.assertEqual(mock_run_batch_evaluation.call_args.args[0], ["40", "41"])


if __name__ == "__main__":
    unittest.main()
