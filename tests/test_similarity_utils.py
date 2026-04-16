"""Tests for similarity helper functions."""

from __future__ import annotations

import unittest

from src.similar_user.services.similarity.utils import (
    calculate_game_composite_score,
    calculate_game_series_features,
)


class SimilarityUtilsTest(unittest.TestCase):
    def test_calculate_game_series_features_uses_mean_std_and_trend(self) -> None:
        result = calculate_game_series_features([80, 90, 100])

        self.assertEqual(result["count"], 3)
        self.assertAlmostEqual(float(result["mean_score"]), 90.0)
        self.assertAlmostEqual(float(result["std"]), 8.16496580927726)
        self.assertAlmostEqual(float(result["trend"]), 10.0)
        self.assertAlmostEqual(float(result["score"]), 88.91751709536137)

    def test_calculate_game_composite_score_accepts_numeric_strings(self) -> None:
        result = calculate_game_composite_score(["91", "95"])

        self.assertAlmostEqual(result, 93.2)

    def test_calculate_game_series_features_ignores_non_numeric_values(self) -> None:
        result = calculate_game_series_features(["", "80", None, "bad", 90])

        self.assertEqual(result["count"], 2)
        self.assertAlmostEqual(float(result["score"]), 85.5)

    def test_calculate_game_series_features_rejects_empty_numeric_series(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "scores must contain at least one numeric value.",
        ):
            calculate_game_series_features(["", None, "bad"])

if __name__ == "__main__":
    unittest.main()
