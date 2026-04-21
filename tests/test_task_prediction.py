"""Tests for training-task prediction helpers."""

from __future__ import annotations

import json
import unittest
from unittest.mock import Mock

from src.similar_user.services.task_prediction import (
    SimilarUserCandidate,
    TrainingTaskPredictionService,
    build_candidate_task_window,
    build_candidate_training_tasks,
    build_rule_based_predictions,
    build_similar_user_game_counts,
    build_target_task_window,
    extract_similar_user_candidates,
    filter_recent_target_repeated_games,
    parse_json_object_from_text,
    parse_date_value,
    summarize_training_history,
)


class TaskPredictionTest(unittest.TestCase):
    def test_parse_json_object_from_text_accepts_logger_prefixed_json(self) -> None:
        payload = {"patient_id": "40", "candidate_ids": ["201"]}
        text = "2026-04-20 | INFO | module | file.py:1 | " + json.dumps(payload)

        result = parse_json_object_from_text(text)

        self.assertEqual(result, payload)

    def test_parse_json_object_from_text_skips_non_json_braces(self) -> None:
        payload = {"patient_id": "40", "candidate_ids": ["201"]}
        text = (
            "2026-04-20 | INFO | module | stats={'totalPaths': 20}\n"
            f"2026-04-20 | INFO | module | {json.dumps(payload)}"
        )

        result = parse_json_object_from_text(text)

        self.assertEqual(result, payload)

    def test_extract_similar_user_candidates_reads_scores_summary(self) -> None:
        result = extract_similar_user_candidates(
            {
                "candidate_summary": {
                    "candidates": [
                        {"patient_id": "201", "candidate_score": 2.5},
                        {"patient_id": "202", "candidate_score": 1.5},
                    ]
                }
            }
        )

        self.assertEqual(
            result,
            [
                SimilarUserCandidate(patient_id="201", candidate_score=2.5),
                SimilarUserCandidate(patient_id="202", candidate_score=1.5),
            ],
        )

    def test_extract_similar_user_candidates_reads_ids_summary(self) -> None:
        result = extract_similar_user_candidates(
            {"candidate_summary": {"candidate_ids": ["201", "202"]}},
        )

        self.assertEqual(
            result,
            [
                SimilarUserCandidate(patient_id="201"),
                SimilarUserCandidate(patient_id="202"),
            ],
        )

    def test_extract_similar_user_candidates_keeps_all_pipeline_candidates(self) -> None:
        candidate_ids = [str(200 + index) for index in range(12)]

        result = extract_similar_user_candidates(
            {"candidate_summary": {"candidate_ids": candidate_ids}},
        )

        self.assertEqual(
            result,
            [
                SimilarUserCandidate(patient_id=candidate_id)
                for candidate_id in candidate_ids
            ],
        )

    def test_summarize_training_history_builds_compact_history(self) -> None:
        result = summarize_training_history(
            "40",
            [
                {
                    "trainingDate": "2022-01-01",
                    "g": {"id": "1", "name": "任务A", "任务类型": "类型A"},
                },
                {
                    "trainingDate": "2022-01-03",
                    "g": {"id": "1", "name": "任务A", "任务类型": "类型A"},
                },
                {
                    "trainingDate": "2022-01-05",
                    "g": {"id": "2", "name": "任务B", "任务类型": "类型B"},
                },
            ],
        )

        self.assertEqual(result["patient_id"], "40")
        self.assertEqual(result["row_count"], 3)
        self.assertEqual(result["training_date_count"], 3)
        self.assertEqual(result["first_training_date"], "2022-01-01")
        self.assertEqual(result["last_training_date"], "2022-01-05")
        self.assertEqual(result["frequent_games"][0]["game_id"], "1")
        self.assertEqual(result["frequent_games"][0]["count"], 2)

    def test_build_target_task_window_uses_two_days_before_base_date(self) -> None:
        result = build_target_task_window("2022-5-22")

        self.assertEqual(
            result,
            {
                "base_date": "2022-05-22",
                "start_date": "2022-05-20",
                "end_date": "2022-05-22",
                "includes_base_date": False,
                "range_semantics": "[start_date, end_date)",
            },
        )

    def test_build_candidate_task_window_uses_requested_days_before_base_date(
        self,
    ) -> None:
        result = build_candidate_task_window("2022-5-22", 14)

        self.assertEqual(
            result,
            {
                "base_date": "2022-05-22",
                "start_date": "2022-05-08",
                "end_date": "2022-05-22",
                "window_days": 14,
                "includes_base_date": False,
                "range_semantics": "[start_date, end_date)",
            },
        )

    def test_build_candidate_task_window_rejects_non_positive_window_days(
        self,
    ) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "window_days must be a positive integer, got 0.",
        ):
            build_candidate_task_window("2022-05-22", 0)

    def test_parse_date_value_rejects_invalid_dates(self) -> None:
        with self.assertRaisesRegex(ValueError, "base_date must be a valid date."):
            parse_date_value("2022-02-31", "base_date")

    def test_build_candidate_training_tasks_uses_candidate_score_as_weight(self) -> None:
        tasks = build_candidate_training_tasks(
            [
                SimilarUserCandidate("201", 2.0),
                SimilarUserCandidate("202", 1.0),
            ],
            {
                "201": [
                    {"g": {"id": "1", "name": "任务A"}},
                    {"g": {"id": "1", "name": "任务A"}},
                ],
                "202": [{"g": {"id": "2", "name": "任务B"}}],
            },
            top_k=5,
        )

        self.assertEqual(tasks[0]["game_id"], "1")
        self.assertEqual(tasks[0]["appearance_count"], 2)
        self.assertEqual(tasks[0]["weighted_score"], 4.0)
        self.assertEqual(tasks[0]["supporting_candidate_ids"], ["201"])

    def test_build_similar_user_game_counts_returns_simple_task_counts(self) -> None:
        game_counts = build_similar_user_game_counts(
            [
                SimilarUserCandidate("201", 2.0),
                SimilarUserCandidate("202", 1.0),
            ],
            {
                "201": [
                    {"g": {"id": "1", "name": "任务A", "任务类型": "类型A"}},
                    {"g": {"id": "1", "name": "任务A", "任务类型": "类型A"}},
                ],
                "202": [
                    {"g": {"id": "1", "name": "任务A", "任务类型": "类型A"}},
                    {"g": {"id": "2", "name": "任务B", "任务类型": "类型B"}},
                ],
            },
        )

        self.assertEqual(game_counts[0]["game_id"], "1")
        self.assertEqual(game_counts[0]["game_name"], "任务A")
        self.assertEqual(game_counts[0]["count"], 3)
        self.assertEqual(game_counts[1]["game_id"], "2")
        self.assertEqual(game_counts[1]["count"], 1)

    def test_filter_recent_target_repeated_games_removes_consecutive_target_tasks(
        self,
    ) -> None:
        game_counts = [
            {"game_id": "1", "game_name": "任务A", "count": 3},
            {"game_id": "2", "game_name": "任务B", "count": 1},
        ]
        filtered_counts = filter_recent_target_repeated_games(
            game_counts,
            [
                {"trainingDate": "2022-05-20", "g": {"id": "1", "name": "任务A"}},
                {"trainingDate": "2022-05-21", "g": {"id": "1", "name": "任务A"}},
                {"trainingDate": "2022-05-21", "g": {"id": "2", "name": "任务B"}},
            ],
        )

        self.assertEqual(
            filtered_counts,
            [{"game_id": "2", "game_name": "任务B", "count": 1}],
        )

    def test_build_rule_based_predictions_returns_ranked_tasks(self) -> None:
        predictions = build_rule_based_predictions(
            [
                {"game_id": "1", "game_name": "任务A", "weighted_score": 4.0},
                {"game_id": "2", "game_name": "任务B", "weighted_score": 2.0},
            ],
            top_k=2,
        )

        self.assertEqual(predictions[0]["rank"], 1)
        self.assertEqual(predictions[0]["game_id"], "1")
        self.assertEqual(predictions[0]["confidence"], 1.0)
        self.assertEqual(predictions[1]["confidence"], 0.5)

    def test_predict_from_pipeline_result_uses_pipeline_candidates_without_llm(self) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.side_effect = [
            [{"trainingDate": "2022-01-01", "g": {"id": "9", "name": "目标任务"}}],
            [{"trainingDate": "2022-01-02", "g": {"id": "1", "name": "任务A"}}],
            [{"trainingDate": "2022-01-03", "g": {"id": "2", "name": "任务B"}}],
        ]
        service = TrainingTaskPredictionService(user_service=user_service)

        result = service.predict_from_pipeline_result(
            {
                "patient_id": "40",
                "candidate_summary": {
                    "candidates": [
                        {"patient_id": "201", "candidate_score": 2.0},
                        {"patient_id": "202", "candidate_score": 1.0},
                    ]
                },
            },
            base_date="2022-5-22",
            window_days=14,
            use_llm=False,
            task_top_k=2,
        )

        self.assertEqual(result["patient_id"], "40")
        self.assertEqual(result["candidate_source"]["candidate_ids"], ["201", "202"])
        self.assertEqual(
            result["similar_user_game_counts"],
            [
                {
                    "game_id": "1",
                    "game_name": "任务A",
                    "count": 1,
                },
                {
                    "game_id": "2",
                    "game_name": "任务B",
                    "count": 1,
                },
            ],
        )
        self.assertEqual(
            result["candidate_source"]["candidate_task_window"],
            {
                "base_date": "2022-05-22",
                "start_date": "2022-05-08",
                "end_date": "2022-05-22",
                "window_days": 14,
                "includes_base_date": False,
                "range_semantics": "[start_date, end_date)",
            },
        )
        self.assertEqual(
            result["target_history_summary"]["task_window"],
            {
                "base_date": "2022-05-22",
                "start_date": "2022-05-20",
                "end_date": "2022-05-22",
                "includes_base_date": False,
                "range_semantics": "[start_date, end_date)",
            },
        )
        self.assertEqual(result["predicted_training_tasks"][0]["game_id"], "1")
        user_service.get_patient_training_task_history_by_date_window.assert_any_call(
            "40",
            "2022-05-20",
            "2022-05-22",
        )
        user_service.get_patient_training_task_history_by_date_window.assert_any_call(
            "201",
            "2022-05-08",
            "2022-05-22",
        )
        user_service.get_patient_training_task_history_by_date_window.assert_any_call(
            "202",
            "2022-05-08",
            "2022-05-22",
        )

    def test_predict_from_pipeline_result_filters_counts_seen_in_target_two_days(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.side_effect = [
            [
                {"trainingDate": "2022-05-20", "g": {"id": "1", "name": "任务A"}},
                {"trainingDate": "2022-05-21", "g": {"id": "1", "name": "任务A"}},
            ],
            [
                {"trainingDate": "2022-05-09", "g": {"id": "1", "name": "任务A"}},
                {"trainingDate": "2022-05-10", "g": {"id": "2", "name": "任务B"}},
            ],
        ]
        service = TrainingTaskPredictionService(user_service=user_service)

        result = service.predict_from_pipeline_result(
            {
                "patient_id": "40",
                "candidate_summary": {"candidate_ids": ["201"]},
            },
            base_date="2022-05-22",
            window_days=14,
            use_llm=False,
            task_top_k=2,
        )

        self.assertEqual(
            result["similar_user_game_counts"],
            [{"game_id": "2", "game_name": "任务B", "count": 1}],
        )

    def test_predict_from_pipeline_result_reads_patient_id_from_candidate_summary(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.side_effect = [
            [{"trainingDate": "2022-01-01", "g": {"id": "9", "name": "目标任务"}}],
            [{"trainingDate": "2022-01-02", "g": {"id": "1", "name": "任务A"}}],
        ]
        service = TrainingTaskPredictionService(user_service=user_service)

        result = service.predict_from_pipeline_result(
            {
                "candidate_summary": {
                    "patient_id": "40",
                    "candidate_ids": ["201"],
                },
            },
            base_date="2022-05-22",
            window_days=14,
            use_llm=False,
            task_top_k=1,
        )

        self.assertEqual(result["patient_id"], "40")
        user_service.get_patient_training_task_history_by_date_window.assert_any_call(
            "40",
            "2022-05-20",
            "2022-05-22",
        )

    def test_predict_from_pipeline_result_requires_patient_id_from_pipeline_output(
        self,
    ) -> None:
        service = TrainingTaskPredictionService(user_service=Mock())

        with self.assertRaisesRegex(
            ValueError,
            "patient_id is required in run_similar_user_pipeline.py output.",
        ):
            service.predict_from_pipeline_result(
                {"candidate_summary": {"candidate_ids": ["201"]}},
                base_date="2022-05-22",
                window_days=14,
                use_llm=False,
            )

    def test_predict_from_pipeline_result_requires_valid_base_date(self) -> None:
        service = TrainingTaskPredictionService(user_service=Mock())

        with self.assertRaisesRegex(ValueError, "base_date must be a valid date."):
            service.predict_from_pipeline_result(
                {
                    "patient_id": "40",
                    "candidate_summary": {"candidate_ids": ["201"]},
                },
                base_date="2022-02-31",
                window_days=14,
                use_llm=False,
            )


if __name__ == "__main__":
    unittest.main()
