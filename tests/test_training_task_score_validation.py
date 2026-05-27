"""Tests for training-task score validation reports."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from src.similar_user.services.training_task_score_validation import (
    build_training_task_score_validation,
)


class TrainingTaskScoreValidationTest(unittest.TestCase):
    def test_build_validation_compares_kg_and_csv_task_scores(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "request_results.csv"
            self._write_csv(
                csv_path,
                [
                    {
                        "ai_params": {
                            "user_id": "20123188_old",
                            "ba": [0.5],
                            "sex": 1,
                            "education": 2,
                            "age": 30,
                            "sicksName": [],
                        },
                        "recommen_train": {
                            "id": [306, 686],
                        },
                    }
                ],
            )

            result = build_training_task_score_validation(
                {
                    "training_task_prediction": {
                        "predicted_training_tasks": [
                            {"game_id": "299"},
                            {"game_id": "306"},
                        ]
                    }
                },
                patient_id="20123188",
                score_url="http://score.test/training_task_score",
                csv_path=csv_path,
                client=_FakeScoreClient(
                    {
                        "299": 60.0,
                        "306": 70.0,
                        "686": 50.0,
                    }
                ),
            )

            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["kg_task_ids"], ["299", "306"])
            self.assertEqual(result["csv_task_ids"], ["306", "686"])
            self.assertEqual(result["overlap_task_ids"], ["306"])
            self.assertEqual(result["kg_avg_score"], 65.0)
            self.assertEqual(result["csv_avg_score"], 60.0)
            self.assertEqual(result["score_delta"], 5.0)
            self.assertEqual(result["kg_better_than_csv_avg_count"], 1)

    def test_build_validation_skips_missing_csv_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "request_results.csv"
            self._write_csv(
                csv_path,
                [
                    {
                        "ai_params": {
                            "user_id": "20123188_old",
                        },
                        "recommen_train": {
                            "id": [306],
                        },
                    }
                ],
            )

            result = build_training_task_score_validation(
                {"predicted_training_tasks": [{"game_id": "299"}]},
                patient_id="missing",
                score_url="http://score.test/training_task_score",
                csv_path=csv_path,
                client=_FakeScoreClient({}),
            )

            self.assertEqual(result["status"], "skipped")
            self.assertEqual(result["reason"], "no_algorithm_request_result_record")
            self.assertEqual(result["kg_task_ids"], ["299"])

    def _write_csv(self, path: Path, rows: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["ai_params", "recommen_train"])
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "ai_params": repr(row["ai_params"]),
                        "recommen_train": repr(row["recommen_train"]),
                    }
                )


class _FakeScoreClient:
    def __init__(self, scores_by_task_id: dict[str, float]) -> None:
        self.scores_by_task_id = scores_by_task_id

    def score_tasks(
        self,
        task_ids: list[str],
        *,
        ai_params: dict[str, object],
    ) -> list[dict[str, object]]:
        return [
            {
                "task_id": task_id,
                "score": self.scores_by_task_id[task_id],
            }
            for task_id in task_ids
        ]


if __name__ == "__main__":
    unittest.main()
