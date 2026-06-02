"""Tests for external training-task prediction request normalization."""

from __future__ import annotations

from datetime import date
import unittest

from src.similar_user.api.external_task_prediction import (
    build_unified_prediction_input,
    normalize_user_id,
)


class ExternalTaskPredictionAdapterTest(unittest.TestCase):
    def test_normalizes_external_payload_for_unified_prediction(self) -> None:
        result = build_unified_prediction_input(
            {
                "user_id": "20123188_old",
                "age": 84,
                "sex": 2,
                "education": 15,
                "sicksName": ["良性遗忘"],
                "behavior_data": {
                    "current_day": "2026-05-24",
                    "gender": "女",
                    "edu": "高中",
                },
            },
            today=lambda: date(2026, 6, 2),
        )

        self.assertEqual(result.patient_id, "20123188")
        self.assertEqual(result.base_date, "2026-06-02")
        self.assertEqual(result.age, 84)
        self.assertEqual(result.gender, "女")
        self.assertEqual(result.education, "高中")
        self.assertEqual(result.disease_names, ["良性遗忘"])
        self.assertEqual(result.task_top_k, 7)
        self.assertEqual(result.output_level, "scores")

    def test_normalize_user_id_only_removes_old_suffix(self) -> None:
        self.assertEqual(normalize_user_id("20123188_old"), "20123188")
        self.assertEqual(normalize_user_id("old_20123188"), "old_20123188")

    def test_rejects_missing_user_id(self) -> None:
        with self.assertRaisesRegex(ValueError, "user_id"):
            build_unified_prediction_input({}, today=lambda: date(2026, 6, 2))


if __name__ == "__main__":
    unittest.main()
