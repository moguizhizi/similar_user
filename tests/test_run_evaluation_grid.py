"""Tests for evaluation grid runner."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import run_evaluation_grid


class RunEvaluationGridTest(unittest.TestCase):
    def test_build_grid_overrides_expands_cartesian_product(self) -> None:
        overrides = run_evaluation_grid.build_grid_overrides(
            {
                "query.candidate_ranking.disease_course_window_days": [7, 14],
                "query.score_pattern_paths.top_k": [30, 50],
            }
        )

        self.assertEqual(
            overrides,
            [
                {
                    "query.candidate_ranking.disease_course_window_days": 7,
                    "query.score_pattern_paths.top_k": 30,
                },
                {
                    "query.candidate_ranking.disease_course_window_days": 7,
                    "query.score_pattern_paths.top_k": 50,
                },
                {
                    "query.candidate_ranking.disease_course_window_days": 14,
                    "query.score_pattern_paths.top_k": 30,
                },
                {
                    "query.candidate_ranking.disease_course_window_days": 14,
                    "query.score_pattern_paths.top_k": 50,
                },
            ],
        )

    def test_build_experiment_override_specs_prefers_named_experiments(self) -> None:
        specs = run_evaluation_grid.build_experiment_override_specs(
            {
                "baseline_overrides": {
                    "query.score_pattern_paths.top_k": 50,
                    "query.candidate_ranking.total_score_match_top_k": 3,
                },
                "experiments": [
                    {
                        "name": "baseline",
                        "overrides": {
                            "query.candidate_ranking.disease_course_window_days": 14
                        },
                    },
                    {
                        "name": "more_path_candidates",
                        "overrides": {
                            "query.candidate_ranking.total_score_match_top_k": 10
                        },
                    },
                ],
                "grid": {
                    "query.score_pattern_paths.top_k": [30, 50],
                },
            }
        )

        self.assertEqual(
            specs,
            [
                (
                    "baseline",
                    {
                        "query.score_pattern_paths.top_k": 50,
                        "query.candidate_ranking.total_score_match_top_k": 3,
                        "query.candidate_ranking.disease_course_window_days": 14,
                    },
                ),
                (
                    "more_path_candidates",
                    {
                        "query.score_pattern_paths.top_k": 50,
                        "query.candidate_ranking.total_score_match_top_k": 10,
                    },
                ),
            ],
        )

    def test_get_stage_name_requires_stage(self) -> None:
        self.assertEqual(
            run_evaluation_grid.get_stage_name({"stage": "coarse_10_users"}),
            "coarse_10_users",
        )
        with self.assertRaisesRegex(ValueError, "stage"):
            run_evaluation_grid.get_stage_name({})

    def test_build_stage_output_root_uses_stage_subdirectory(self) -> None:
        self.assertEqual(
            run_evaluation_grid.build_stage_output_root(
                "data/evaluation_grid",
                "coarse 10 users",
            ),
            Path("data/evaluation_grid/coarse-10-users"),
        )

    def test_build_experiment_override_specs_falls_back_to_grid(self) -> None:
        specs = run_evaluation_grid.build_experiment_override_specs(
            {
                "grid": {
                    "query.score_pattern_paths.top_k": [30, 50],
                }
            }
        )

        self.assertEqual(
            specs,
            [
                (None, {"query.score_pattern_paths.top_k": 30}),
                (None, {"query.score_pattern_paths.top_k": 50}),
            ],
        )

    def test_build_experiment_override_specs_merges_baseline_overrides_with_grid(
        self,
    ) -> None:
        specs = run_evaluation_grid.build_experiment_override_specs(
            {
                "baseline_overrides": {
                    "query.candidate_ranking.disease_course_window_days": 14,
                    "query.score_pattern_paths.top_k": 50,
                },
                "grid": {
                    "query.score_pattern_paths.top_k": [80],
                },
            }
        )

        self.assertEqual(
            specs,
            [
                (
                    None,
                    {
                        "query.candidate_ranking.disease_course_window_days": 14,
                        "query.score_pattern_paths.top_k": 80,
                    },
                )
            ],
        )

    def test_apply_dot_path_override_updates_nested_mapping(self) -> None:
        config = {"query": {"candidate_ranking": {"disease_course_window_days": 14}}}

        run_evaluation_grid.apply_dot_path_override(
            config,
            "query.candidate_ranking.disease_course_window_days",
            30,
        )

        self.assertEqual(
            config["query"]["candidate_ranking"]["disease_course_window_days"],
            30,
        )

    def test_build_evaluation_command_uses_base_options(self) -> None:
        command = run_evaluation_grid.build_evaluation_command(
            base_options={
                "base_date": "2023-10-15",
                "window_days": 14,
                "task_top_k": 7,
                "use_llm": False,
                "skip_path_build": True,
                "limit": 10,
            },
            config_path="data/evaluation_grid/generated_configs/exp_001.yaml",
            output_dir="data/evaluation_grid/runs/exp_001",
        )

        self.assertEqual(
            command[1:],
            [
                "scripts/evaluate_predict_training_tasks.py",
                "--base-date",
                "2023-10-15",
                "--window-days",
                "14",
                "--config",
                "data/evaluation_grid/generated_configs/exp_001.yaml",
                "--task-top-k",
                "7",
                "--output-dir",
                "data/evaluation_grid/runs/exp_001",
                "--limit",
                "10",
                "--dry-run",
                "--skip-path-build",
            ],
        )

    def test_run_evaluation_grid_skips_existing_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "runs" / "exp_001"
            summary_dir = output_dir / "base_2023-10-15_window_14"
            summary_dir.mkdir(parents=True)
            (summary_dir / "predict_training_tasks_summary.json").write_text(
                "{}\n",
                encoding="utf-8",
            )
            run = run_evaluation_grid.EvaluationGridRun(
                index=1,
                name="exp_001",
                overrides={"query.score_pattern_paths.top_k": 50},
                config_path=str(Path(temp_dir) / "exp_001.yaml"),
                output_dir=str(output_dir),
                command=["python", "evaluate"],
            )

            with patch("scripts.run_evaluation_grid.subprocess.run") as mock_run:
                result = run_evaluation_grid.run_evaluation_grid(
                    [run],
                    output_root=temp_dir,
                )

        mock_run.assert_not_called()
        self.assertEqual(result["skipped_count"], 1)
        self.assertEqual(result["success_count"], 0)

    def test_run_evaluation_grid_keeps_going_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            runs = [
                run_evaluation_grid.EvaluationGridRun(
                    index=1,
                    name="exp_001",
                    overrides={},
                    config_path=str(Path(temp_dir) / "exp_001.yaml"),
                    output_dir=str(Path(temp_dir) / "runs" / "exp_001"),
                    command=["python", "fail"],
                ),
                run_evaluation_grid.EvaluationGridRun(
                    index=2,
                    name="exp_002",
                    overrides={},
                    config_path=str(Path(temp_dir) / "exp_002.yaml"),
                    output_dir=str(Path(temp_dir) / "runs" / "exp_002"),
                    command=["python", "ok"],
                ),
            ]

            with patch("scripts.run_evaluation_grid.subprocess.run") as mock_run:
                mock_run.side_effect = [Mock(returncode=1), Mock(returncode=0)]
                result = run_evaluation_grid.run_evaluation_grid(
                    runs,
                    output_root=temp_dir,
                )

        self.assertEqual(mock_run.call_count, 2)
        self.assertEqual(result["failed_count"], 1)
        self.assertEqual(result["success_count"], 1)

    def test_build_leaderboard_ranks_completed_summaries(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            first_output_dir = Path(temp_dir) / "runs" / "exp_001"
            second_output_dir = Path(temp_dir) / "runs" / "exp_002"
            first_summary_dir = first_output_dir / "base_2023-10-15_window_14"
            second_summary_dir = second_output_dir / "base_2023-10-15_window_14"
            first_summary_dir.mkdir(parents=True)
            second_summary_dir.mkdir(parents=True)
            (first_summary_dir / "predict_training_tasks_summary.json").write_text(
                '{"micro_recall": 0.1, "micro_f1": 0.2, "task_hit_rate": 0.5, "avg_elapsed_seconds": 10}\n',
                encoding="utf-8",
            )
            (second_summary_dir / "predict_training_tasks_summary.json").write_text(
                '{"micro_recall": 0.3, "micro_f1": 0.1, "task_hit_rate": 0.4, "avg_elapsed_seconds": 20}\n',
                encoding="utf-8",
            )
            runs = [
                run_evaluation_grid.EvaluationGridRun(
                    index=1,
                    name="exp_001",
                    overrides={"query.score_pattern_paths.top_k": 30},
                    config_path=str(Path(temp_dir) / "exp_001.yaml"),
                    output_dir=str(first_output_dir),
                    command=["python", "evaluate"],
                ),
                run_evaluation_grid.EvaluationGridRun(
                    index=2,
                    name="exp_002",
                    overrides={"query.score_pattern_paths.top_k": 50},
                    config_path=str(Path(temp_dir) / "exp_002.yaml"),
                    output_dir=str(second_output_dir),
                    command=["python", "evaluate"],
                ),
            ]

            leaderboard = run_evaluation_grid.build_leaderboard(runs)

        self.assertEqual([row["name"] for row in leaderboard], ["exp_002", "exp_001"])
        self.assertEqual(leaderboard[0]["rank"], 1)
        self.assertEqual(leaderboard[0]["overrides"], {"query.score_pattern_paths.top_k": 50})

    def test_write_leaderboard_outputs_writes_json_and_csv(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            json_path, csv_path = run_evaluation_grid.write_leaderboard_outputs(
                [
                    {
                        "rank": 1,
                        "name": "exp_001",
                        "rank_metric": "micro_recall",
                        "micro_recall": 0.3,
                        "micro_f1": 0.2,
                        "task_hit_rate": 0.5,
                        "micro_precision": 0.1,
                        "avg_elapsed_seconds": 10,
                        "summary_path": "summary.json",
                        "overrides": {"query.score_pattern_paths.top_k": 50},
                    }
                ],
                temp_dir,
            )

            json_text = json_path.read_text(encoding="utf-8")
            csv_text = csv_path.read_text(encoding="utf-8")

        self.assertIn('"name": "exp_001"', json_text)
        self.assertIn("rank,name,rank_metric", csv_text)
        self.assertIn("exp_001", csv_text)

    def test_build_promoted_baseline_payload_uses_best_experiment_metrics(self) -> None:
        payload = run_evaluation_grid.build_promoted_baseline_payload(
            {
                "rank": 1,
                "name": "exp_001",
                "rank_metric": "micro_recall",
                "micro_recall": 0.3,
                "summary_path": "summary.json",
                "overrides": {"query.a": 1},
            },
            stage="coarse_10_users",
        )

        self.assertEqual(
            payload,
            {
                "source_stage": "coarse_10_users",
                "source_experiment": "exp_001",
                "rank": 1,
                "rank_metric": "micro_recall",
                "metric_value": 0.3,
                "summary_path": "summary.json",
                "overrides": {"query.a": 1},
            },
        )

    def test_write_promoted_baseline_overrides_appends_non_active_block(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "evaluation_grid.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        'stage: "coarse_10_users"',
                        "",
                        "baseline_overrides:",
                        "  query.a: 1",
                        "",
                        "experiments:",
                        "  - name: baseline",
                        "    overrides: {}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            run_evaluation_grid.write_promoted_baseline_overrides(
                config_path,
                {
                    "source_stage": "coarse_10_users",
                    "source_experiment": "exp_001",
                    "rank_metric": "micro_recall",
                    "metric_value": 0.3,
                    "overrides": {"query.a": 2},
                },
            )

            updated_text = config_path.read_text(encoding="utf-8")
            updated_config = run_evaluation_grid.load_experiment_config(config_path)

        self.assertIn("baseline_overrides:\n  query.a: 1", updated_text)
        self.assertIn("promoted_baseline_overrides:", updated_text)
        self.assertEqual(updated_config["baseline_overrides"], {"query.a": 1})
        self.assertEqual(
            updated_config["promoted_baseline_overrides"]["overrides"],
            {"query.a": 2},
        )

    def test_write_promoted_baseline_overrides_comments_previous_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "evaluation_grid.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        'stage: "coarse_10_users"',
                        "",
                        "promoted_baseline_overrides:",
                        "  source_experiment: old",
                        "  overrides:",
                        "    query.a: 1",
                        "",
                        "experiments:",
                        "  - name: baseline",
                        "    overrides: {}",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )

            run_evaluation_grid.write_promoted_baseline_overrides(
                config_path,
                {
                    "source_experiment": "new",
                    "overrides": {"query.a": 2},
                },
            )

            updated_text = config_path.read_text(encoding="utf-8")
            updated_config = run_evaluation_grid.load_experiment_config(config_path)

        self.assertIn("# Previous promoted_baseline_overrides:", updated_text)
        self.assertIn("# promoted_baseline_overrides:", updated_text)
        self.assertEqual(
            updated_config["promoted_baseline_overrides"]["source_experiment"],
            "new",
        )


if __name__ == "__main__":
    unittest.main()
