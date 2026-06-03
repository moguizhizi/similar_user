"""Tests for training-task prediction helpers."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock

from src.similar_user.services.task_prediction import (
    CURRENT_TASK_PREDICTION_PROMPT_TEMPLATE_NAME,
    SimilarUserCandidate,
    TASK_PREDICTION_PROMPT_TEMPLATE_DIRECT_ENTITY_V1,
    TASK_PREDICTION_PROMPT_TEMPLATE_V1,
    TASK_PREDICTION_PROMPT_TEMPLATE_V2,
    TASK_PREDICTION_PROMPT_TEMPLATE_V3,
    TASK_PREDICTION_PROMPT_TEMPLATE_V4,
    TrainingTaskPredictionService,
    build_candidate_task_window,
    build_candidate_training_tasks,
    build_candidate_training_tasks_from_distinct_games,
    build_task_prediction_prompt,
    build_prompt_similar_user_candidates,
    build_rule_based_predictions,
    build_similar_user_game_counts,
    build_similar_user_task_evidence,
    build_target_task_window,
    extract_similar_user_candidates,
    filter_game_counts_to_ids,
    filter_candidate_tasks_to_ids,
    filter_recent_target_repeated_games,
    filter_task_evidence_to_ids,
    load_unlock_train_candidate_tasks,
    parse_json_object_from_text,
    parse_date_value,
    select_prompt_candidate_game_ids,
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

    def test_build_task_prediction_prompt_uses_named_template(self) -> None:
        prompt = build_task_prediction_prompt(
            patient_id="40",
            similar_user_game_counts=[],
            candidate_training_tasks=[],
            task_top_k=7,
            prompt_template_name="TASK_PREDICTION_PROMPT_TEMPLATE_V1",
        )

        self.assertTrue(prompt.startswith(TASK_PREDICTION_PROMPT_TEMPLATE_V1))
        self.assertFalse(prompt.startswith(TASK_PREDICTION_PROMPT_TEMPLATE_V2))

    def test_build_task_prediction_prompt_uses_weighted_template_v3(self) -> None:
        prompt = build_task_prediction_prompt(
            patient_id="40",
            similar_user_game_counts=[
                {
                    "game_id": "1",
                    "game_name": "任务A",
                    "count": 3,
                    "weighted_count": 2.5,
                    "supporting_user_count": 2,
                    "avg_support_score": 0.75,
                    "max_support_score": 1.0,
                }
            ],
            candidate_training_tasks=[],
            task_top_k=7,
            prompt_template_name="TASK_PREDICTION_PROMPT_TEMPLATE_V3",
        )

        self.assertTrue(prompt.startswith(TASK_PREDICTION_PROMPT_TEMPLATE_V3))
        self.assertIn("supporting_user_count 是做过该任务的不同相似用户人数", prompt)
        self.assertIn('"weighted_count": 2.5', prompt)

    def test_build_task_prediction_prompt_includes_candidate_scores(self) -> None:
        prompt = build_task_prediction_prompt(
            patient_id="40",
            similar_user_candidates=[
                {"patient_id": "201", "candidate_score": 2.5},
                {"patient_id": "202", "candidate_score": 1.5},
            ],
            similar_user_game_counts=[],
            candidate_training_tasks=[],
            task_top_k=7,
            prompt_template_name="TASK_PREDICTION_PROMPT_TEMPLATE_V2",
        )

        self.assertIn('"similar_user_candidates"', prompt)
        self.assertIn('"patient_id": "201"', prompt)
        self.assertIn('"candidate_score": 2.5', prompt)

    def test_build_task_prediction_prompt_uses_compact_v4_template(self) -> None:
        prompt = build_task_prediction_prompt(
            patient_id="40",
            similar_user_candidates=[
                {"patient_id": "201", "candidate_score": 2.5},
            ],
            similar_user_task_evidence=[
                {"patient_id": "201", "tasks": [{"game_id": "1", "count": 3}]},
            ],
            similar_user_game_counts=[],
            candidate_training_tasks=[],
            task_top_k=7,
            prompt_template_name="TASK_PREDICTION_PROMPT_TEMPLATE_V4",
        )

        self.assertTrue(prompt.startswith(TASK_PREDICTION_PROMPT_TEMPLATE_V4))
        self.assertIn('"similar_user_candidates"', prompt)
        self.assertIn('"similar_user_task_evidence"', prompt)
        self.assertNotIn('"rank"', prompt)
        self.assertNotIn("confidence", prompt)
        self.assertNotIn("reason", prompt)
        self.assertNotIn("supporting_candidate_ids", prompt)

    def test_load_unlock_train_candidate_tasks_uses_unlock_train_keys(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            csv_path = Path(tmp_dir) / "request.csv"
            csv_path.write_text(
                "\n".join(
                    [
                        "ai_params,recommen_train",
                        "\"\"\"{'user_id': '40_old', 'unlock_train': {'300': 60, '301': 0}}\"\"\",{}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            tasks = load_unlock_train_candidate_tasks(csv_path, "40")

        self.assertEqual(
            tasks,
            [
                {"game_id": "300", "game_name": None},
                {"game_id": "301", "game_name": None},
            ],
        )

    def test_build_task_prediction_prompt_v2_includes_task_evidence(self) -> None:
        prompt = build_task_prediction_prompt(
            patient_id="40",
            similar_user_game_counts=[],
            candidate_training_tasks=[],
            task_top_k=7,
            similar_user_task_evidence=[
                {
                    "patient_id": "201",
                    "candidate_score": 2.0,
                    "tasks": [{"game_id": "1", "game_name": "任务A", "count": 2}],
                }
            ],
            prompt_template_name="TASK_PREDICTION_PROMPT_TEMPLATE_V2",
        )

        self.assertIn('"similar_user_task_evidence"', prompt)
        self.assertIn('"candidate_score": 2.0', prompt)
        self.assertIn('"game_id": "1"', prompt)

    def test_build_direct_entity_prompt_includes_profile_and_entities(self) -> None:
        prompt = build_task_prediction_prompt(
            patient_id="new-user",
            target_profile={"age": 66, "education": "本科", "gender": "男"},
            target_entities={
                "disease_ids": ["AU_DIS_0029"],
                "symptom_ids": ["AU_SYM_0001"],
                "unknown_ids": [],
            },
            candidate_source="direct_entity_paths",
            similar_user_candidates=[
                {"patient_id": "201", "candidate_score": 2.5},
            ],
            similar_user_task_evidence=[
                {
                    "patient_id": "201",
                    "candidate_score": 2.5,
                    "tasks": [{"game_id": "1", "game_name": "任务A", "count": 1}],
                }
            ],
            similar_user_game_counts=[],
            candidate_training_tasks=[],
            task_top_k=7,
            prompt_template_name="TASK_PREDICTION_PROMPT_TEMPLATE_DIRECT_ENTITY_V1",
        )

        self.assertTrue(
            prompt.startswith(TASK_PREDICTION_PROMPT_TEMPLATE_DIRECT_ENTITY_V1)
        )
        self.assertIn('"target_profile"', prompt)
        self.assertIn('"age": 66', prompt)
        self.assertIn('"target_entities"', prompt)
        self.assertIn('"AU_DIS_0029"', prompt)
        self.assertIn('"candidate_source": "direct_entity_paths"', prompt)

    def test_basic_prompt_templates_do_not_describe_weighted_count(self) -> None:
        self.assertNotIn("weighted_count", TASK_PREDICTION_PROMPT_TEMPLATE_V1)
        self.assertNotIn("weighted_count", TASK_PREDICTION_PROMPT_TEMPLATE_V2)
        self.assertNotIn("weighted_count", TASK_PREDICTION_PROMPT_TEMPLATE_V4)

    def test_v2_and_v4_prompt_templates_describe_task_evidence_payload(self) -> None:
        self.assertNotIn(
            "similar_user_task_evidence",
            TASK_PREDICTION_PROMPT_TEMPLATE_V1,
        )
        self.assertIn(
            "similar_user_task_evidence",
            TASK_PREDICTION_PROMPT_TEMPLATE_V2,
        )
        self.assertIn(
            "similar_user_task_evidence",
            TASK_PREDICTION_PROMPT_TEMPLATE_V4,
        )
        self.assertNotIn(
            "similar_user_task_evidence",
            TASK_PREDICTION_PROMPT_TEMPLATE_V3,
        )

    def test_weighted_template_requires_weighting_enabled(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "TASK_PREDICTION_PROMPT_TEMPLATE_V3 requires",
        ):
            TrainingTaskPredictionService(
                user_service=Mock(),
                prompt_template_name="TASK_PREDICTION_PROMPT_TEMPLATE_V3",
                similar_user_game_counts_weighting_enabled=False,
            )

        service = TrainingTaskPredictionService(
            user_service=Mock(),
            prompt_template_name="TASK_PREDICTION_PROMPT_TEMPLATE_V3",
            similar_user_game_counts_weighting_enabled=True,
        )

        self.assertEqual(
            service.prompt_template_name,
            "TASK_PREDICTION_PROMPT_TEMPLATE_V3",
        )

    def test_build_task_prediction_prompt_v2_includes_empty_task_evidence(self) -> None:
        prompt = build_task_prediction_prompt(
            patient_id="40",
            similar_user_game_counts=[],
            candidate_training_tasks=[],
            task_top_k=7,
        )

        self.assertIn('"similar_user_task_evidence": []', prompt)
        self.assertNotIn("input_options", prompt)

    def test_build_task_prediction_prompt_rejects_unknown_template(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown prompt_template_name"):
            build_task_prediction_prompt(
                patient_id="40",
                similar_user_game_counts=[],
                candidate_training_tasks=[],
                task_top_k=7,
                prompt_template_name="UNKNOWN_TEMPLATE",
            )

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

    def test_build_candidate_training_tasks_from_distinct_games_keeps_all_tasks(
        self,
    ) -> None:
        tasks = build_candidate_training_tasks_from_distinct_games(
            [
                {"g": {"id": "2", "name": "任务B", "任务类型": "类型B"}},
                {"g": {"id": "1", "name": "任务A", "任务类型": "类型A"}},
                {"g": {"id": "1", "name": "任务A重复"}},
            ]
        )

        self.assertEqual(
            tasks,
            [
                {"game_id": "1", "game_name": "任务A"},
                {"game_id": "2", "game_name": "任务B"},
            ],
        )

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

    def test_build_similar_user_game_counts_can_add_weighted_metrics(self) -> None:
        game_counts = build_similar_user_game_counts(
            [
                SimilarUserCandidate("201", 2.0),
                SimilarUserCandidate("202", 1.0),
            ],
            {
                "201": [
                    {"g": {"id": "1", "name": "任务A"}},
                    {"g": {"id": "1", "name": "任务A"}},
                ],
                "202": [
                    {"g": {"id": "1", "name": "任务A"}},
                    {"g": {"id": "2", "name": "任务B"}},
                ],
            },
            weighting_enabled=True,
        )

        self.assertEqual(game_counts[0]["game_id"], "1")
        self.assertEqual(game_counts[0]["count"], 3)
        self.assertEqual(game_counts[0]["weighted_count"], 2.5)
        self.assertEqual(game_counts[0]["supporting_user_count"], 2)
        self.assertEqual(game_counts[0]["avg_support_score"], 0.75)
        self.assertEqual(game_counts[0]["max_support_score"], 1.0)
        self.assertEqual(
            game_counts[0]["supporting_candidate_ids"],
            ["201", "202"],
        )

    def test_build_similar_user_game_counts_can_sort_by_weighted_metrics(self) -> None:
        game_counts = build_similar_user_game_counts(
            [
                SimilarUserCandidate("201", 10.0),
                SimilarUserCandidate("202", 1.0),
            ],
            {
                "201": [
                    {"g": {"id": "2", "name": "任务B"}},
                ],
                "202": [
                    {"g": {"id": "1", "name": "任务A"}},
                    {"g": {"id": "1", "name": "任务A"}},
                    {"g": {"id": "1", "name": "任务A"}},
                ],
            },
            weighting_enabled=True,
            weighted_sort_enabled=True,
        )

        self.assertEqual([item["game_id"] for item in game_counts], ["2", "1"])
        self.assertEqual(game_counts[0]["weighted_count"], 1.0)
        self.assertEqual(game_counts[1]["weighted_count"], 0.3)

    def test_build_similar_user_task_evidence_returns_scores_and_user_tasks(
        self,
    ) -> None:
        evidence = build_similar_user_task_evidence(
            [
                SimilarUserCandidate("201", 2.0),
                SimilarUserCandidate("202", 1.0),
            ],
            {
                "201": [
                    {"g": {"id": "1", "name": "任务A"}},
                    {"g": {"id": "1", "name": "任务A"}},
                    {"g": {"id": "3", "name": "任务C"}},
                ],
                "202": [
                    {"g": {"id": "2", "name": "任务B"}},
                    {"g": {"id": "3", "name": "任务C"}},
                ],
            },
            excluded_game_ids={"3"},
        )

        self.assertEqual(
            evidence,
            [
                {
                    "patient_id": "201",
                    "candidate_score": 2.0,
                    "tasks": [{"game_id": "1", "game_name": "任务A", "count": 2}],
                },
                {
                    "patient_id": "202",
                    "candidate_score": 1.0,
                    "tasks": [{"game_id": "2", "game_name": "任务B", "count": 1}],
                },
            ],
        )

    def test_build_prompt_similar_user_candidates_returns_compact_scores(self) -> None:
        prompt_candidates = build_prompt_similar_user_candidates(
            [
                SimilarUserCandidate("201", 2.0, "2022-05-22"),
                SimilarUserCandidate("202", None),
            ]
        )

        self.assertEqual(
            prompt_candidates,
            [
                {
                    "patient_id": "201",
                    "candidate_score": 2.0,
                    "candidate_base_date": "2022-05-22",
                },
                {"patient_id": "202", "candidate_score": None},
            ],
        )

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

    def test_filter_game_counts_to_ids_keeps_candidate_task_subset(self) -> None:
        result = filter_game_counts_to_ids(
            [
                {"game_id": "1", "game_name": "任务A", "count": 3},
                {"game_id": "2", "game_name": "任务B", "count": 1},
            ],
            {"2"},
        )

        self.assertEqual(
            result,
            [{"game_id": "2", "game_name": "任务B", "count": 1}],
        )

    def test_filter_task_evidence_to_ids_removes_empty_candidate_evidence(
        self,
    ) -> None:
        result = filter_task_evidence_to_ids(
            [
                {
                    "patient_id": "201",
                    "candidate_score": 1.0,
                    "tasks": [
                        {"game_id": "1", "game_name": "任务A", "count": 3},
                        {"game_id": "2", "game_name": "任务B", "count": 1},
                    ],
                },
                {
                    "patient_id": "202",
                    "candidate_score": 0.5,
                    "tasks": [{"game_id": "3", "game_name": "任务C", "count": 1}],
                },
            ],
            {"2"},
        )

        self.assertEqual(
            result,
            [
                {
                    "patient_id": "201",
                    "candidate_score": 1.0,
                    "tasks": [{"game_id": "2", "game_name": "任务B", "count": 1}],
                }
            ],
        )

    def test_filter_candidate_tasks_to_ids_keeps_selected_prompt_tasks(self) -> None:
        result = filter_candidate_tasks_to_ids(
            [
                {"game_id": "1", "game_name": "任务A"},
                {"game_id": "2", "game_name": "任务B"},
            ],
            {"2"},
        )

        self.assertEqual(result, [{"game_id": "2", "game_name": "任务B"}])

    def test_select_prompt_candidate_game_ids_mixes_global_and_high_score_tasks(
        self,
    ) -> None:
        selected = select_prompt_candidate_game_ids(
            [
                {"game_id": "1", "count": 10},
                {"game_id": "2", "count": 9},
                {"game_id": "3", "count": 8},
            ],
            [
                {
                    "patient_id": "201",
                    "candidate_score": 0.5,
                    "tasks": [{"game_id": "4", "count": 3}],
                },
                {
                    "patient_id": "202",
                    "candidate_score": 2.0,
                    "tasks": [
                        {"game_id": "5", "count": 2},
                        {"game_id": "2", "count": 1},
                    ],
                },
            ],
            overall_top_n=2,
            high_score_user_count=1,
            per_high_score_user_top_k=2,
            max_prompt_candidates=4,
        )

        self.assertEqual(selected, {"1", "2", "5"})

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
        user_service.get_patient_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-01-01", "g": {"id": "9", "name": "目标任务"}}
        ]
        user_service.get_patient_exclusive_training_task_history_by_date_window.side_effect = [
            [{"trainingDate": "2022-01-02", "g": {"id": "1", "name": "任务A"}}],
            [{"trainingDate": "2022-01-03", "g": {"id": "2", "name": "任务B"}}],
        ]
        user_service.get_distinct_training_games.return_value = [
            {"g": {"id": "4", "name": "全局任务D", "任务类型": "类型D"}},
            {"g": {"id": "5", "name": "全局任务E", "任务类型": "类型E"}},
        ]
        user_service.get_patient_profile_candidate_training_games.return_value = [
            {"g": {"id": "1", "name": "任务A", "任务类型": "类型A"}},
            {"g": {"id": "7", "name": "画像任务G", "任务类型": "类型G"}},
        ]
        service = TrainingTaskPredictionService(user_service=user_service)

        result = service.predict_from_pipeline_result(
            {
                "patient_id": "40",
                "candidate_summary": {
                    "candidates": [
                        {
                            "patient_id": "201",
                            "candidate_score": 2.0,
                            "score_details": {
                                "disease_course_secondary_ability": {
                                    "candidate_base_date": "2022-06-14",
                                }
                            },
                        },
                        {
                            "patient_id": "202",
                            "candidate_score": 1.0,
                            "score_details": {
                                "disease_course_secondary_ability": {
                                    "candidate_base_date": "2022-07-14",
                                }
                            },
                        },
                    ]
                },
            },
            base_date="2022-5-22",
            window_days=14,
            use_llm=False,
            task_top_k=2,
        )

        self.assertEqual(result["patient_id"], "40")
        self.assertEqual(result["prediction_status"], "success")
        self.assertFalse(result["fallback_used"])
        self.assertIsNone(result["prediction_failure_stage"])
        self.assertEqual(result["candidate_source"]["candidate_ids"], ["201", "202"])
        self.assertEqual(
            result["raw_similar_user_game_counts"],
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
            result["similar_user_game_counts"],
            [
                {
                    "game_id": "1",
                    "game_name": "任务A",
                    "count": 1,
                },
            ],
        )
        self.assertEqual(
            result["similar_user_task_evidence"],
            [
                {
                    "patient_id": "201",
                    "candidate_score": 2.0,
                    "tasks": [{"game_id": "1", "game_name": "任务A", "count": 1}],
                },
            ],
        )
        self.assertEqual(
            result["candidate_source"]["candidate_task_windows"],
            {
                "201": {
                    "base_date": "2022-06-14",
                    "start_date": "2022-05-31",
                    "end_date": "2022-06-14",
                    "window_days": 14,
                    "includes_base_date": False,
                    "range_semantics": "[start_date, end_date)",
                },
                "202": {
                    "base_date": "2022-07-14",
                    "start_date": "2022-06-30",
                    "end_date": "2022-07-14",
                    "window_days": 14,
                    "includes_base_date": False,
                    "range_semantics": "[start_date, end_date)",
                },
            },
        )
        self.assertNotIn("target_history_summary", result)
        self.assertEqual(
            result["candidate_training_tasks"],
            [{"game_id": "1", "game_name": "任务A"}],
        )
        self.assertEqual(result["prompt_candidate_selection"]["enabled"], True)
        self.assertEqual(
            result["prompt_candidate_selection"]["source_candidate_task_count"],
            2,
        )
        self.assertEqual(
            result["candidate_source"]["candidate_task_source"],
            "patient_profile_entities",
        )
        self.assertEqual(result["predicted_training_tasks"][0]["game_id"], "1")
        user_service.get_patient_profile_candidate_training_games.assert_called_once_with(
            "40",
            "2022-05-22",
            profile_candidate_training_window_days=None,
        )
        user_service.get_distinct_training_games.assert_not_called()
        user_service.get_patient_training_task_history_by_date_window.assert_called_once_with(
            "40",
            "2022-05-20",
            "2022-05-22",
        )
        user_service.get_patient_exclusive_training_task_history_by_date_window.assert_any_call(
            "201",
            "2022-05-31",
            "2022-06-14",
        )
        user_service.get_patient_exclusive_training_task_history_by_date_window.assert_any_call(
            "202",
            "2022-06-30",
            "2022-07-14",
        )

    def test_predict_from_pipeline_result_filters_counts_seen_in_target_two_days(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-05-20", "g": {"id": "1", "name": "任务A"}},
            {"trainingDate": "2022-05-21", "g": {"id": "1", "name": "任务A"}},
        ]
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-05-09", "g": {"id": "1", "name": "任务A"}},
            {"trainingDate": "2022-05-10", "g": {"id": "2", "name": "任务B"}},
        ]
        user_service.get_distinct_training_games.return_value = [
            {"g": {"id": "1", "name": "任务A"}},
            {"g": {"id": "2", "name": "任务B"}},
        ]
        user_service.get_patient_profile_candidate_training_games.return_value = [
            {"g": {"id": "2", "name": "任务B"}},
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
        self.assertEqual(
            result["similar_user_task_evidence"],
            [
                {
                    "patient_id": "201",
                    "candidate_score": None,
                    "tasks": [{"game_id": "2", "game_name": "任务B", "count": 1}],
                }
            ],
        )
        self.assertEqual(result["candidate_training_tasks"], [{"game_id": "2", "game_name": "任务B"}])

    def test_predict_from_direct_entity_candidates_keeps_raw_similar_user_counts(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_exclusive_training_task_history_by_date_window.side_effect = [
            [
                {
                    "trainingDate": "2022-05-10",
                    "g": {"id": f"{index:03d}", "name": f"任务{index:03d}"},
                }
                for index in range(1, 52)
            ]
        ]
        service = TrainingTaskPredictionService(
            user_service=user_service,
            prompt_candidate_compression_enabled=False,
        )

        result = service.predict_from_direct_entity_candidates(
            patient_id="new-user",
            candidate_result={"candidates": [{"patient_id": "201"}]},
            base_date="2022-05-22",
            window_days=14,
            use_llm=False,
            task_top_k=1,
        )

        self.assertEqual(
            len(result["raw_similar_user_game_counts"]),
            51,
        )
        self.assertEqual(
            len(result["similar_user_game_counts"]),
            50,
        )
        self.assertEqual(result["raw_similar_user_game_counts"][-1]["game_id"], "051")
        self.assertNotIn(
            "051",
            [item["game_id"] for item in result["similar_user_game_counts"]],
        )

    def test_predict_from_pipeline_result_can_disable_prompt_candidate_compression(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-01-01", "g": {"id": "9", "name": "目标任务"}}
        ]
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-01-02", "g": {"id": "1", "name": "任务A"}}
        ]
        user_service.get_patient_profile_candidate_training_games.return_value = [
            {"g": {"id": "1", "name": "任务A"}},
            {"g": {"id": "7", "name": "画像任务G"}},
        ]
        service = TrainingTaskPredictionService(
            user_service=user_service,
            prompt_candidate_compression_enabled=False,
        )

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

        self.assertEqual(result["prompt_candidate_selection"]["enabled"], False)
        self.assertEqual(
            result["prompt_template"],
            CURRENT_TASK_PREDICTION_PROMPT_TEMPLATE_NAME,
        )
        self.assertEqual(
            result["candidate_training_tasks"],
            [
                {"game_id": "1", "game_name": "任务A"},
                {"game_id": "7", "game_name": "画像任务G"},
            ],
        )

    def test_predict_from_pipeline_result_passes_profile_candidate_training_window(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.return_value = []
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-01-02", "g": {"id": "1", "name": "任务A"}}
        ]
        user_service.get_patient_profile_candidate_training_games.return_value = [
            {"g": {"id": "1", "name": "任务A"}},
        ]
        service = TrainingTaskPredictionService(
            user_service=user_service,
            profile_candidate_training_window_days=0,
        )

        service.predict_from_pipeline_result(
            {
                "patient_id": "40",
                "candidate_summary": {"candidate_ids": ["201"]},
            },
            base_date="2022-05-22",
            window_days=14,
            use_llm=False,
        )

        user_service.get_patient_profile_candidate_training_games.assert_called_once_with(
            "40",
            "2022-05-22",
            profile_candidate_training_window_days=0,
        )

    def test_predict_from_direct_entity_candidates_uses_candidate_histories(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_exclusive_training_task_history_by_date_window.side_effect = [
            [
                {
                    "trainingDate": "2022-05-10",
                    "g": {"id": "1", "name": "任务A"},
                },
                {
                    "trainingDate": "2022-05-11",
                    "g": {"id": "2", "name": "任务B"},
                },
            ],
            [
                {
                    "trainingDate": "2022-05-12",
                    "g": {"id": "1", "name": "任务A"},
                }
            ],
        ]
        service = TrainingTaskPredictionService(user_service=user_service)

        result = service.predict_from_direct_entity_candidates(
            patient_id="new-user",
            candidate_result={
                "candidates": [
                    {"patient_id": "201", "candidate_score": 90.0},
                    {"patient_id": "202", "candidate_score": 80.0},
                ]
            },
            base_date="2022-05-22",
            window_days=14,
            target_profile={"age": 66, "education": "本科", "gender": "男"},
            target_entities={"disease_ids": ["AU_DIS_0029"]},
            use_llm=False,
            task_top_k=1,
        )

        self.assertEqual(result["candidate_source"]["source"], "direct_entity_paths")
        self.assertEqual(result["target_profile"]["age"], 66)
        self.assertEqual(result["target_entities"]["disease_ids"], ["AU_DIS_0029"])
        self.assertEqual(result["candidate_source"]["candidate_ids"], ["201", "202"])
        self.assertEqual(result["predicted_training_tasks"][0]["game_id"], "1")
        self.assertEqual(result["predicted_training_tasks"][0]["game_name"], "任务A")
        self.assertEqual(
            result["predicted_training_tasks"][0]["supporting_candidate_ids"],
            ["201", "202"],
        )
        self.assertEqual(
            user_service.get_patient_training_task_history_by_date_window.call_count,
            0,
        )
        user_service.get_patient_exclusive_training_task_history_by_date_window.assert_any_call(
            "201",
            "2022-05-08",
            "2022-05-22",
        )

    def test_predict_from_pipeline_result_omits_task_evidence_from_v1_prompt(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-01-01", "g": {"id": "9", "name": "目标任务"}}
        ]
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-01-02", "g": {"id": "1", "name": "任务A"}}
        ]
        user_service.get_patient_profile_candidate_training_games.return_value = [
            {"g": {"id": "1", "name": "任务A"}},
        ]
        service = TrainingTaskPredictionService(
            user_service=user_service,
            prompt_template_name="TASK_PREDICTION_PROMPT_TEMPLATE_V1",
        )

        result = service.predict_from_pipeline_result(
            {
                "patient_id": "40",
                "candidate_summary": {
                    "candidates": [{"patient_id": "201", "candidate_score": 2.0}]
                },
            },
            base_date="2022-05-22",
            window_days=14,
            use_llm=False,
            task_top_k=1,
            include_prompt=True,
        )

        self.assertEqual(
            result["similar_user_task_evidence"],
            [
                {
                    "patient_id": "201",
                    "candidate_score": 2.0,
                    "tasks": [{"game_id": "1", "game_name": "任务A", "count": 1}],
                }
            ],
        )
        self.assertNotIn("prompt_input_options", result)
        self.assertNotIn("similar_user_task_evidence", result["llm_prompt"])

    def test_predict_from_pipeline_result_falls_back_to_distinct_games_without_profile_tasks(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-01-01", "g": {"id": "9", "name": "目标任务"}}
        ]
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-01-02", "g": {"id": "1", "name": "任务A"}}
        ]
        user_service.get_patient_profile_candidate_training_games.return_value = []
        user_service.get_distinct_training_games.return_value = [
            {"g": {"id": "4", "name": "全局任务D"}},
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
            task_top_k=1,
        )

        self.assertEqual(
            result["candidate_training_tasks"],
            [{"game_id": "4", "game_name": "全局任务D"}],
        )
        self.assertEqual(
            result["candidate_source"]["candidate_task_source"],
            "distinct_training_games_fallback",
        )
        user_service.get_distinct_training_games.assert_called_once_with()

    def test_predict_from_pipeline_result_reads_patient_id_from_candidate_summary(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-01-01", "g": {"id": "9", "name": "目标任务"}}
        ]
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-01-02", "g": {"id": "1", "name": "任务A"}}
        ]
        user_service.get_distinct_training_games.return_value = [
            {"g": {"id": "1", "name": "任务A"}},
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

    def test_predict_from_pipeline_result_falls_back_when_candidates_are_empty(
        self,
    ) -> None:
        user_service = Mock()
        user_service.get_patient_direct_entity_scoring_profile.return_value = [
            {
                "age_at_base_date": 66,
                "education": "本科",
                "gender": "男",
            }
        ]
        user_service.get_profile_matched_exclusive_tasks.return_value = [
            {
                "g": {"id": "G1", "name": "画像任务1", "任务类型": "专属"},
                "support_count": 10,
                "patient_count": 3,
                "latest_training_date": "2022-05-20",
            }
        ]
        user_service.get_global_popular_exclusive_tasks.return_value = []
        user_service.get_distinct_training_games.return_value = []
        service = TrainingTaskPredictionService(user_service=user_service)

        result = service.predict_from_pipeline_result(
            {
                "patient_id": "40",
                "candidate_summary": {"candidate_ids": []},
            },
            base_date="2022-05-22",
            window_days=14,
            use_llm=False,
            task_top_k=1,
        )

        self.assertEqual(result["prediction_status"], "success")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["fallback_reason"], "empty_candidates")
        self.assertEqual(result["fallback_source"], "profile_matched_tasks")
        self.assertEqual(result["prediction_failure_stage"], "candidate")
        self.assertEqual(result["predicted_training_tasks"][0]["game_id"], "G1")
        self.assertTrue(result["candidate_source"]["patient_profile_loaded"])

    def test_predict_from_pipeline_result_falls_back_on_llm_errors(self) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-05-21", "g": {"id": "9", "name": "目标任务"}}
        ]
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-05-10", "g": {"id": "1", "name": "任务A"}}
        ]
        user_service.get_patient_profile_candidate_training_games.return_value = [
            {"g": {"id": "1", "name": "任务A"}}
        ]
        llm_client = Mock()
        llm_client.chat.side_effect = RuntimeError("llm failed")
        service = TrainingTaskPredictionService(
            user_service=user_service,
            llm_client=llm_client,
        )

        result = service.predict_from_pipeline_result(
            {
                "patient_id": "40",
                "candidate_summary": {"candidate_ids": ["201"]},
            },
            base_date="2022-05-22",
            window_days=14,
            use_llm=True,
            include_prompt=True,
            task_top_k=1,
        )

        self.assertEqual(result["prediction_status"], "success")
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["fallback_reason"], "llm_failed")
        self.assertEqual(result["fallback_source"], "candidate_training_tasks")
        self.assertEqual(result["prediction_failure_stage"], "llm")
        self.assertEqual(result["prediction_error_type"], "RuntimeError")
        self.assertEqual(result["prediction_error_message"], "llm failed")
        self.assertEqual(result["predicted_training_tasks"][0]["game_id"], "1")
        self.assertIn("candidate_training_tasks", result["llm_prompt"])

    def test_predict_from_pipeline_result_can_disable_llm_fallback(self) -> None:
        user_service = Mock()
        user_service.get_patient_training_task_history_by_date_window.return_value = []
        user_service.get_patient_exclusive_training_task_history_by_date_window.return_value = [
            {"trainingDate": "2022-05-10", "g": {"id": "1", "name": "任务A"}}
        ]
        user_service.get_patient_profile_candidate_training_games.return_value = [
            {"g": {"id": "1", "name": "任务A"}}
        ]
        llm_client = Mock()
        llm_client.chat.side_effect = RuntimeError("llm failed")
        service = TrainingTaskPredictionService(
            user_service=user_service,
            llm_client=llm_client,
            fallback_enabled=False,
        )

        with self.assertRaisesRegex(RuntimeError, "llm failed"):
            service.predict_from_pipeline_result(
                {
                    "patient_id": "40",
                    "candidate_summary": {"candidate_ids": ["201"]},
                },
                base_date="2022-05-22",
                window_days=14,
                use_llm=True,
                task_top_k=1,
            )


if __name__ == "__main__":
    unittest.main()
