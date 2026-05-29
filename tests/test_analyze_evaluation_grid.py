"""Tests for evaluation grid analysis reports."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import analyze_evaluation_grid


class AnalyzeEvaluationGridTest(unittest.TestCase):
    def test_analyze_evaluation_grid_compares_best_with_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            grid_dir = Path(temp_dir)
            baseline_summary = grid_dir / "baseline_summary.json"
            best_summary = grid_dir / "best_summary.json"
            second_best_summary = grid_dir / "second_best_summary.json"
            baseline_summary.write_text(
                json.dumps(
                    {
                        "failed_count": 0,
                        "candidate_training_tasks_actual_missing_rate": 0.0,
                    }
                ),
                encoding="utf-8",
            )
            best_summary.write_text(
                json.dumps(
                    {
                        "failed_count": 0,
                        "candidate_training_tasks_actual_missing_rate": 0.0,
                    }
                ),
                encoding="utf-8",
            )
            second_best_summary.write_text(
                json.dumps(
                    {
                        "failed_count": 0,
                        "candidate_training_tasks_actual_missing_rate": 0.0,
                    }
                ),
                encoding="utf-8",
            )
            (grid_dir / "leaderboard.json").write_text(
                json.dumps(
                    [
                        {
                            "rank": 1,
                            "name": "exp_002_more-path-candidates",
                            "rank_metric": "micro_recall",
                            "micro_recall": 0.3,
                            "micro_f1": 0.25,
                            "task_hit_rate": 0.8,
                            "micro_precision": 0.2,
                            "avg_elapsed_seconds": 20,
                            "summary_path": str(best_summary),
                            "overrides": {"query.a": 2},
                        },
                        {
                            "rank": 2,
                            "name": "exp_003_second-best",
                            "rank_metric": "micro_recall",
                            "micro_recall": 0.25,
                            "micro_f1": 0.22,
                            "task_hit_rate": 0.75,
                            "micro_precision": 0.2,
                            "avg_elapsed_seconds": 15,
                            "summary_path": str(second_best_summary),
                            "overrides": {"query.a": 3},
                        },
                        {
                            "rank": 3,
                            "name": "exp_001_baseline-best",
                            "rank_metric": "micro_recall",
                            "micro_recall": 0.2,
                            "micro_f1": 0.2,
                            "task_hit_rate": 0.7,
                            "micro_precision": 0.2,
                            "avg_elapsed_seconds": 10,
                            "summary_path": str(baseline_summary),
                            "overrides": {"query.a": 1},
                        },
                    ]
                ),
                encoding="utf-8",
            )
            (grid_dir / "grid_summary.json").write_text(
                json.dumps({"failed_count": 0}),
                encoding="utf-8",
            )

            analysis = analyze_evaluation_grid.analyze_evaluation_grid(grid_dir)

        self.assertEqual(analysis["status"], "ok")
        self.assertEqual(
            analysis["best_experiment"]["name"],
            "exp_002_more-path-candidates",
        )
        self.assertEqual(
            analysis["baseline_experiment"]["name"],
            "exp_001_baseline-best",
        )
        self.assertEqual(
            analysis["second_best_experiment"]["name"],
            "exp_003_second-best",
        )
        self.assertEqual(
            analysis["metric_comparison"]["micro_recall"]["delta"],
            0.1,
        )
        self.assertEqual(
            analysis["second_best_metric_comparison"]["micro_recall"]["delta"],
            0.05,
        )
        self.assertEqual(
            analysis["second_best_metric_comparison"]["micro_recall"]["baseline"],
            0.2,
        )
        self.assertEqual(
            analysis["parameter_diff"],
            {"query.a": {"baseline": 1, "best": 2}},
        )
        self.assertEqual(
            analysis["second_best_parameter_diff"],
            {"query.a": {"baseline": 1, "best": 3}},
        )

    def test_analyze_and_write_evaluation_grid_report_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            grid_dir = Path(temp_dir)
            (grid_dir / "leaderboard.json").write_text("[]\n", encoding="utf-8")

            output_paths = (
                analyze_evaluation_grid.analyze_and_write_evaluation_grid_report(
                    grid_dir
                )
            )

            json_text = output_paths["json"].read_text(encoding="utf-8")
            markdown_text = output_paths["markdown"].read_text(encoding="utf-8")

        self.assertIn('"status": "no_leaderboard_rows"', json_text)
        self.assertIn("# Evaluation Grid Analysis", markdown_text)

    def test_analyze_evaluation_grid_recommends_by_score_delta(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            grid_dir = Path(temp_dir)
            baseline_summary = grid_dir / "baseline_summary.json"
            best_summary = grid_dir / "best_summary.json"
            baseline_summary.write_text(
                json.dumps(
                    {
                        "failed_count": 0,
                        "avg_score_delta": 1.0,
                        "avg_kg_score": 80.0,
                        "avg_csv_score": 79.0,
                    }
                ),
                encoding="utf-8",
            )
            best_summary.write_text(
                json.dumps(
                    {
                        "failed_count": 0,
                        "avg_score_delta": 2.5,
                        "avg_kg_score": 82.0,
                        "avg_csv_score": 79.5,
                    }
                ),
                encoding="utf-8",
            )
            (grid_dir / "leaderboard.json").write_text(
                json.dumps(
                    [
                        {
                            "rank": 1,
                            "name": "exp_002_score",
                            "rank_metric": "avg_score_delta",
                            "avg_score_delta": 2.5,
                            "avg_kg_score": 82.0,
                            "avg_csv_score": 79.5,
                            "summary_path": str(best_summary),
                            "overrides": {"query.a": 2},
                        },
                        {
                            "rank": 2,
                            "name": "exp_001_baseline-best",
                            "rank_metric": "avg_score_delta",
                            "avg_score_delta": 1.0,
                            "avg_kg_score": 80.0,
                            "avg_csv_score": 79.0,
                            "summary_path": str(baseline_summary),
                            "overrides": {"query.a": 1},
                        },
                    ]
                ),
                encoding="utf-8",
            )
            (grid_dir / "grid_summary.json").write_text(
                json.dumps({"failed_count": 0}),
                encoding="utf-8",
            )

            analysis = analyze_evaluation_grid.analyze_evaluation_grid(grid_dir)

        self.assertEqual(analysis["rank_by"], "avg_score_delta")
        self.assertEqual(analysis["metric_comparison"]["avg_score_delta"]["delta"], 1.5)
        self.assertIn("avg_score_delta", analysis["recommendation"])


if __name__ == "__main__":
    unittest.main()
