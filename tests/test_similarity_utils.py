"""Tests for similarity helper functions."""

from __future__ import annotations

import unittest

from src.similar_user.services.similarity.utils import (
    calculate_game_composite_score,
    calculate_game_series_features,
    calculate_game_similarity_with_diversity_score,
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

    def test_calculate_game_similarity_with_diversity_score_uses_common_and_unique_games(
        self,
    ) -> None:
        result = calculate_game_similarity_with_diversity_score(
            ["打怪物", "真假句辨别", "记忆广度"],
            ["打怪物", "真假句辨别", "空间搜索", "连连看"],
        )

        self.assertEqual(result["common_game_count"], 2)
        self.assertEqual(result["source_only_game_count"], 1)
        self.assertEqual(result["candidate_only_game_count"], 2)
        self.assertAlmostEqual(float(result["similarity_component"]), 2 / 3)
        self.assertAlmostEqual(float(result["diversity_component"]), 2 / 4)
        self.assertAlmostEqual(float(result["score"]), (2 / 3) * (2 / 4))

    def test_calculate_game_similarity_with_diversity_score_deduplicates_games(
        self,
    ) -> None:
        result = calculate_game_similarity_with_diversity_score(
            ["打怪物", "打怪物", "真假句辨别"],
            ["打怪物", "空间搜索", "空间搜索"],
        )

        self.assertEqual(result["common_game_count"], 1)
        self.assertEqual(result["source_only_game_count"], 1)
        self.assertEqual(result["candidate_only_game_count"], 1)
        self.assertAlmostEqual(float(result["score"]), 0.25)

    def test_calculate_game_similarity_with_diversity_score_returns_zero_for_same_games(
        self,
    ) -> None:
        result = calculate_game_similarity_with_diversity_score(
            ["打怪物", "真假句辨别"],
            ["真假句辨别", "打怪物"],
        )

        self.assertEqual(result["common_game_count"], 2)
        self.assertEqual(result["source_only_game_count"], 0)
        self.assertEqual(result["candidate_only_game_count"], 0)
        self.assertAlmostEqual(float(result["similarity_component"]), 1.0)
        self.assertAlmostEqual(float(result["diversity_component"]), 0.0)
        self.assertAlmostEqual(float(result["score"]), 0.0)

    def test_calculate_game_similarity_with_diversity_score_returns_zero_for_no_overlap(
        self,
    ) -> None:
        result = calculate_game_similarity_with_diversity_score(
            ["打怪物"],
            ["空间搜索"],
        )

        self.assertEqual(result["common_game_count"], 0)
        self.assertEqual(result["source_only_game_count"], 1)
        self.assertEqual(result["candidate_only_game_count"], 1)
        self.assertAlmostEqual(float(result["similarity_component"]), 0.0)
        self.assertAlmostEqual(float(result["diversity_component"]), 1.0)
        self.assertAlmostEqual(float(result["score"]), 0.0)

    def test_calculate_game_similarity_with_diversity_score_ignores_blank_game_values(
        self,
    ) -> None:
        result = calculate_game_similarity_with_diversity_score(
            ["打怪物", "", None],
            ["打怪物", "  ", None, "空间搜索"],
        )

        self.assertEqual(result["common_game_count"], 1)
        self.assertEqual(result["source_only_game_count"], 0)
        self.assertEqual(result["candidate_only_game_count"], 1)
        self.assertAlmostEqual(float(result["similarity_component"]), 1.0)
        self.assertAlmostEqual(float(result["diversity_component"]), 0.5)
        self.assertAlmostEqual(float(result["score"]), 0.5)


if __name__ == "__main__":
    unittest.main()
