"""Helpers shared by similarity implementations."""

from __future__ import annotations

import math
from collections.abc import Sequence


def calculate_game_series_features(scores: Sequence[object]) -> dict[str, float | int]:
    """Calculate game score features from one ordered score series."""
    numeric_scores = _coerce_numeric_scores(scores)
    if not numeric_scores:
        raise ValueError("scores must contain at least one numeric value.")

    mean_score = sum(numeric_scores) / len(numeric_scores)
    std = math.sqrt(
        sum((score - mean_score) ** 2 for score in numeric_scores)
        / len(numeric_scores)
    )
    trend = _calculate_linear_trend(numeric_scores)
    score = mean_score - 0.5 * std + 0.3 * trend

    return {
        "count": len(numeric_scores),
        "mean_score": mean_score,
        "std": std,
        "trend": trend,
        "score": score,
    }


def calculate_game_composite_score(scores: Sequence[object]) -> float:
    """Calculate the composite game score used by similarity features."""
    return float(calculate_game_series_features(scores)["score"])


def calculate_game_similarity_with_diversity_score(
    source_games: Sequence[object],
    candidate_games: Sequence[object],
) -> dict[str, float | int]:
    """Calculate a score for candidates that are similar but not identical."""
    source_game_set = _coerce_game_set(source_games)
    candidate_game_set = _coerce_game_set(candidate_games)

    common_game_count = len(source_game_set & candidate_game_set)
    source_only_game_count = len(source_game_set - candidate_game_set)
    candidate_only_game_count = len(candidate_game_set - source_game_set)

    source_game_count = common_game_count + source_only_game_count
    candidate_game_count = common_game_count + candidate_only_game_count
    similarity_component = (
        0.0 if source_game_count == 0 else common_game_count / source_game_count
    )
    diversity_component = (
        0.0
        if candidate_game_count == 0
        else candidate_only_game_count / candidate_game_count
    )
    score = similarity_component * diversity_component

    return {
        "common_game_count": common_game_count,
        "source_only_game_count": source_only_game_count,
        "candidate_only_game_count": candidate_only_game_count,
        "similarity_component": similarity_component,
        "diversity_component": diversity_component,
        "score": score,
    }


def _coerce_game_set(games: Sequence[object]) -> set[str]:
    """Convert game identifiers to a normalized set."""
    game_set: set[str] = set()
    for game in games:
        if game is None:
            continue
        normalized_game = str(game).strip()
        if normalized_game:
            game_set.add(normalized_game)

    return game_set


def _coerce_numeric_scores(scores: Sequence[object]) -> list[float]:
    """Convert numeric score values and numeric strings to floats."""
    numeric_scores: list[float] = []
    for score in scores:
        if isinstance(score, bool):
            continue
        if isinstance(score, (int, float)):
            numeric_score = float(score)
        elif isinstance(score, str):
            stripped_score = score.strip()
            if not stripped_score:
                continue
            try:
                numeric_score = float(stripped_score)
            except ValueError:
                continue
        else:
            continue

        if math.isfinite(numeric_score):
            numeric_scores.append(numeric_score)

    return numeric_scores


def _calculate_linear_trend(scores: Sequence[float]) -> float:
    """Return the slope of a simple least-squares line for ordered scores."""
    if len(scores) < 2:
        return 0.0

    x_mean = (len(scores) - 1) / 2
    y_mean = sum(scores) / len(scores)
    denominator = sum((index - x_mean) ** 2 for index in range(len(scores)))
    if denominator == 0:
        return 0.0

    numerator = sum(
        (index - x_mean) * (score - y_mean)
        for index, score in enumerate(scores)
    )
    return numerator / denominator
