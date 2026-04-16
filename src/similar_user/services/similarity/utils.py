"""Helpers shared by similarity implementations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any


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


def calculate_set_same_score(
    source_items: Sequence[object],
    candidate_items: Sequence[object],
) -> dict[str, float | int]:
    """Calculate same-score for disease, symptom, or other item collections."""
    source_item_set = _coerce_item_set(source_items)
    candidate_item_set = _coerce_item_set(candidate_items)

    common_count = len(source_item_set & candidate_item_set)
    source_only_count = len(source_item_set - candidate_item_set)
    candidate_only_count = len(candidate_item_set - source_item_set)

    source_count = common_count + source_only_count
    candidate_count = common_count + candidate_only_count
    source_same_component = 0.0 if source_count == 0 else common_count / source_count
    candidate_same_component = (
        0.0 if candidate_count == 0 else common_count / candidate_count
    )
    score = source_same_component * candidate_same_component

    return {
        "common_count": common_count,
        "source_only_count": source_only_count,
        "candidate_only_count": candidate_only_count,
        "source_same_component": source_same_component,
        "candidate_same_component": candidate_same_component,
        "score": score,
    }


def calculate_common_game_score_correlation(
    records: Sequence[dict[str, Any]],
) -> dict[str, object]:
    """Calculate Pearson correlation from common-game score series records."""
    common_games: list[str] = []
    source_vector: list[float] = []
    candidate_vector: list[float] = []

    for record in records:
        game = record.get("game")
        scores_p1 = record.get("scores_p1")
        scores_p2 = record.get("scores_p2")
        if not isinstance(scores_p1, Sequence) or isinstance(scores_p1, (str, bytes)):
            continue
        if not isinstance(scores_p2, Sequence) or isinstance(scores_p2, (str, bytes)):
            continue

        try:
            source_score = calculate_game_composite_score(scores_p1)
            candidate_score = calculate_game_composite_score(scores_p2)
        except ValueError:
            continue

        common_games.append("" if game is None else str(game))
        source_vector.append(source_score)
        candidate_vector.append(candidate_score)

    return {
        "common_games": common_games,
        "source_vector": source_vector,
        "candidate_vector": candidate_vector,
        "valid_game_count": len(common_games),
        "correlation": calculate_pearson_correlation(source_vector, candidate_vector),
    }


def calculate_pearson_correlation(
    vector_a: Sequence[float],
    vector_b: Sequence[float],
) -> float | None:
    """Calculate Pearson correlation for two same-length vectors."""
    if len(vector_a) != len(vector_b):
        raise ValueError("vector_a and vector_b must have the same length.")
    if len(vector_a) < 2:
        return None

    mean_a = sum(vector_a) / len(vector_a)
    mean_b = sum(vector_b) / len(vector_b)
    numerator = sum(
        (value_a - mean_a) * (value_b - mean_b)
        for value_a, value_b in zip(vector_a, vector_b)
    )
    denominator_a = math.sqrt(sum((value_a - mean_a) ** 2 for value_a in vector_a))
    denominator_b = math.sqrt(sum((value_b - mean_b) ** 2 for value_b in vector_b))
    denominator = denominator_a * denominator_b
    if denominator == 0:
        return None

    return numerator / denominator


def _coerce_game_set(games: Sequence[object]) -> set[str]:
    """Convert game identifiers to a normalized set."""
    return _coerce_item_set(games)


def _coerce_item_set(items: Sequence[object]) -> set[str]:
    """Convert item identifiers to a normalized set."""
    item_set: set[str] = set()
    for item in items:
        if item is None:
            continue
        normalized_item = str(item).strip()
        if normalized_item:
            item_set.add(normalized_item)

    return item_set


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
