"""Tests for similarity helper functions."""

from __future__ import annotations

import unittest

from src.similar_user.services.similarity.utils import (
    calculate_common_game_score_similarity,
    calculate_cosine_similarity,
    calculate_game_composite_score,
    calculate_game_series_features,
    calculate_game_similarity_with_diversity_score,
    calculate_pearson_correlation,
    calculate_relative_l2_distance,
    calculate_set_same_score,
)


class SimilarityUtilsTest(unittest.TestCase):
    def test_calculate_game_series_features_uses_mean_std_and_trend(self) -> None:
        result = calculate_game_series_features([80, 90, 100])

        self.assertEqual(result["count"], 3)
        self.assertAlmostEqual(float(result["mean_score"]), 90.0)
        self.assertAlmostEqual(float(result["std"]), 8.16496580927726)
        self.assertAlmostEqual(float(result["trend"]), 10.0)
        self.assertAlmostEqual(float(result["score"]), 135.91751709536137)

    def test_calculate_game_composite_score_accepts_numeric_strings(self) -> None:
        result = calculate_game_composite_score(["91", "95"])

        self.assertAlmostEqual(result, 112.0)

    def test_calculate_game_series_features_ignores_non_numeric_values(self) -> None:
        result = calculate_game_series_features(["", "80", None, "bad", 90])

        self.assertEqual(result["count"], 2)
        self.assertAlmostEqual(float(result["score"]), 132.5)

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

    def test_calculate_set_same_score_uses_common_and_unique_items(self) -> None:
        result = calculate_set_same_score(
            ["睡眠障碍", "记忆下降", "焦虑"],
            ["睡眠障碍", "记忆下降", "头晕", "乏力"],
        )

        self.assertEqual(result["common_count"], 2)
        self.assertEqual(result["source_only_count"], 1)
        self.assertEqual(result["candidate_only_count"], 2)
        self.assertAlmostEqual(float(result["source_same_component"]), 2 / 3)
        self.assertAlmostEqual(float(result["candidate_same_component"]), 2 / 4)
        self.assertAlmostEqual(float(result["score"]), (2 / 3) * (2 / 4))

    def test_calculate_set_same_score_returns_one_for_same_items(self) -> None:
        result = calculate_set_same_score(
            ["睡眠障碍", "记忆下降"],
            ["记忆下降", "睡眠障碍"],
        )

        self.assertEqual(result["common_count"], 2)
        self.assertEqual(result["source_only_count"], 0)
        self.assertEqual(result["candidate_only_count"], 0)
        self.assertAlmostEqual(float(result["source_same_component"]), 1.0)
        self.assertAlmostEqual(float(result["candidate_same_component"]), 1.0)
        self.assertAlmostEqual(float(result["score"]), 1.0)

    def test_calculate_set_same_score_returns_zero_for_no_overlap(self) -> None:
        result = calculate_set_same_score(
            ["睡眠障碍"],
            ["头晕"],
        )

        self.assertEqual(result["common_count"], 0)
        self.assertEqual(result["source_only_count"], 1)
        self.assertEqual(result["candidate_only_count"], 1)
        self.assertAlmostEqual(float(result["score"]), 0.0)

    def test_calculate_set_same_score_deduplicates_and_ignores_blank_values(self) -> None:
        result = calculate_set_same_score(
            ["睡眠障碍", "睡眠障碍", "", None],
            ["睡眠障碍", "  ", None, "头晕", "头晕"],
        )

        self.assertEqual(result["common_count"], 1)
        self.assertEqual(result["source_only_count"], 0)
        self.assertEqual(result["candidate_only_count"], 1)
        self.assertAlmostEqual(float(result["score"]), 0.5)

    def test_calculate_set_same_score_returns_zero_when_one_side_is_empty(self) -> None:
        result = calculate_set_same_score([], ["头晕"])

        self.assertEqual(result["common_count"], 0)
        self.assertEqual(result["source_only_count"], 0)
        self.assertEqual(result["candidate_only_count"], 1)
        self.assertAlmostEqual(float(result["score"]), 0.0)

    def test_calculate_pearson_correlation_returns_linear_correlation(self) -> None:
        self.assertAlmostEqual(
            calculate_pearson_correlation([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]),
            1.0,
        )
        self.assertAlmostEqual(
            calculate_pearson_correlation([1.0, 2.0, 3.0], [6.0, 4.0, 2.0]),
            -1.0,
        )

    def test_calculate_pearson_correlation_returns_none_when_not_enough_data(
        self,
    ) -> None:
        self.assertIsNone(calculate_pearson_correlation([1.0], [1.0]))

    def test_calculate_pearson_correlation_returns_none_for_zero_variance(self) -> None:
        self.assertIsNone(calculate_pearson_correlation([1.0, 1.0], [2.0, 3.0]))

    def test_calculate_pearson_correlation_rejects_different_lengths(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "vector_a and vector_b must have the same length.",
        ):
            calculate_pearson_correlation([1.0, 2.0], [1.0])

    def test_calculate_cosine_similarity_returns_vector_similarity(self) -> None:
        self.assertAlmostEqual(
            calculate_cosine_similarity([1.0, 2.0, 3.0], [2.0, 4.0, 6.0]),
            1.0,
        )
        self.assertAlmostEqual(
            calculate_cosine_similarity([1.0, 0.0], [0.0, 1.0]),
            0.0,
        )

    def test_calculate_cosine_similarity_returns_none_for_empty_or_zero_vector(
        self,
    ) -> None:
        self.assertIsNone(calculate_cosine_similarity([], []))
        self.assertIsNone(calculate_cosine_similarity([0.0, 0.0], [1.0, 2.0]))

    def test_calculate_cosine_similarity_rejects_different_lengths(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "vector_a and vector_b must have the same length.",
        ):
            calculate_cosine_similarity([1.0, 2.0], [1.0])

    def test_calculate_relative_l2_distance_uses_relative_matrix_difference(
        self,
    ) -> None:
        result = calculate_relative_l2_distance(
            [[2.0, -4.0], [10.0, 5.0]],
            [[1.0, -2.0], [12.0, 0.0]],
            epsilon=1.0,
        )

        expected = (
            ((2.0 - 1.0) / (abs(2.0) + 1.0)) ** 2
            + ((-4.0 - -2.0) / (abs(-4.0) + 1.0)) ** 2
            + ((10.0 - 12.0) / (abs(10.0) + 1.0)) ** 2
            + ((5.0 - 0.0) / (abs(5.0) + 1.0)) ** 2
        ) ** 0.5
        self.assertAlmostEqual(result, expected)

    def test_calculate_relative_l2_distance_accepts_vectors(self) -> None:
        result = calculate_relative_l2_distance([1, "2", 4], [2, 1, 8], epsilon=1)

        expected = (
            ((1 - 2) / (abs(1) + 1)) ** 2
            + ((2 - 1) / (abs(2) + 1)) ** 2
            + ((4 - 8) / (abs(4) + 1)) ** 2
        ) ** 0.5
        self.assertAlmostEqual(result, expected)

    def test_calculate_relative_l2_distance_uses_epsilon_for_zero_baseline(
        self,
    ) -> None:
        result = calculate_relative_l2_distance([0.0], [0.5], epsilon=0.5)

        self.assertAlmostEqual(result, 1.0)

    def test_calculate_relative_l2_distance_rejects_shape_mismatch(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "matrix_a and matrix_b must have the same shape.",
        ):
            calculate_relative_l2_distance([[1.0, 2.0]], [[1.0]])

    def test_calculate_relative_l2_distance_rejects_non_numeric_values(self) -> None:
        with self.assertRaisesRegex(
            ValueError,
            "matrix_a\\[0\\] must contain only finite numeric values.",
        ):
            calculate_relative_l2_distance([[1.0, "bad"]], [[1.0, 2.0]])

    def test_calculate_relative_l2_distance_rejects_invalid_epsilon(self) -> None:
        with self.assertRaisesRegex(ValueError, "epsilon must be a positive number."):
            calculate_relative_l2_distance([1.0], [2.0], epsilon=0.0)

    def test_calculate_common_game_score_similarity_uses_query_records(self) -> None:
        result = calculate_common_game_score_similarity(
            [
                {
                    "game": "打怪物",
                    "scores_p1": ["80", "90"],
                    "scores_p2": ["82", "92"],
                },
                {
                    "game": "真假句辨别",
                    "scores_p1": ["90", "100"],
                    "scores_p2": ["93", "103"],
                },
                {
                    "game": "空间搜索",
                    "scores_p1": ["100", "110"],
                    "scores_p2": ["104", "114"],
                },
            ]
        )

        self.assertEqual(result["common_games"], ["打怪物", "真假句辨别", "空间搜索"])
        self.assertEqual(result["valid_game_count"], 3)
        self.assertEqual(result["source_vector"], [132.5, 142.5, 152.5])
        self.assertEqual(result["candidate_vector"], [134.5, 145.5, 156.5])
        self.assertAlmostEqual(float(result["similarity"]), 0.9999902556016596)

    def test_calculate_common_game_score_similarity_skips_invalid_records(self) -> None:
        result = calculate_common_game_score_similarity(
            [
                {
                    "game": "打怪物",
                    "scores_p1": ["80", "90"],
                    "scores_p2": ["82", "92"],
                },
                {
                    "game": "坏数据",
                    "scores_p1": [],
                    "scores_p2": ["82", "92"],
                },
                {
                    "game": "非序列",
                    "scores_p1": "80",
                    "scores_p2": ["82", "92"],
                },
            ]
        )

        self.assertEqual(result["common_games"], ["打怪物"])
        self.assertEqual(result["valid_game_count"], 1)
        self.assertAlmostEqual(float(result["similarity"]), 1.0)

    def test_calculate_common_game_score_similarity_ignores_zero_variance(
        self,
    ) -> None:
        result = calculate_common_game_score_similarity(
            [
                {
                    "game": "打怪物",
                    "scores_p1": ["90"],
                    "scores_p2": ["80"],
                },
                {
                    "game": "真假句辨别",
                    "scores_p1": ["90"],
                    "scores_p2": ["100"],
                },
            ]
        )

        self.assertEqual(result["source_vector"], [90.0, 90.0])
        self.assertEqual(result["candidate_vector"], [80.0, 100.0])
        self.assertAlmostEqual(float(result["similarity"]), 0.9938837346736189)


if __name__ == "__main__":
    unittest.main()
