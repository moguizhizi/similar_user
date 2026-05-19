"""Helpers shared by similarity implementations."""

from __future__ import annotations

import math
from collections.abc import Sequence
from typing import Any


SECONDARY_ABILITY_SCORE_FIELDS = (
    "二级_书写能力",
    "二级_任务切换",
    "二级_冲突抑制",
    "二级_前瞻记忆",
    "二级_反应速度",
    "二级_口语生成",
    "二级_听理解",
    "二级_客体识别",
    "二级_工作记忆",
    "二级_归纳与推理",
    "二级_心算",
    "二级_情景记忆",
    "二级_情绪识别",
    "二级_情绪调节",
    "二级_手眼协调",
    "二级_持续注意",
    "二级_注意分配",
    "二级_注意广度",
    "二级_积极情绪",
    "二级_空间知觉",
    "二级_空间记忆",
    "二级_联结记忆",
    "二级_节律感知",
    "二级_表象与想象",
    "二级_记忆广度",
    "二级_语义系统",
    "二级_路径规划",
    "二级_运动知觉",
    "二级_选择注意",
    "二级_问题解决",
    "二级_阅读能力",
)


def calculate_game_series_features(scores: Sequence[object]) -> dict[str, float | int]:
    """从单个游戏的有序分数序列中提取统计特征和综合分。

    综合分以平均分为基础，扣除分数波动带来的不稳定性，并加入少量趋势奖励。
    """
    numeric_scores = _coerce_numeric_scores(scores)
    if not numeric_scores:
        raise ValueError("scores must contain at least one numeric value.")

    mean_score = sum(numeric_scores) / len(numeric_scores)
    std = math.sqrt(
        sum((score - mean_score) ** 2 for score in numeric_scores)
        / len(numeric_scores)
    )
    trend = _calculate_linear_trend(numeric_scores)
    score = mean_score - 0.5 * std + 5 * trend

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


def calculate_common_game_score_similarity(
    records: Sequence[dict[str, Any]],
) -> dict[str, object]:
    """Calculate cosine similarity from common-game score series records."""
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
        "similarity": calculate_cosine_similarity(source_vector, candidate_vector),
    }


def calculate_cosine_similarity(
    vector_a: Sequence[float],
    vector_b: Sequence[float],
) -> float | None:
    """Calculate cosine similarity for two same-length vectors."""
    if len(vector_a) != len(vector_b):
        raise ValueError("vector_a and vector_b must have the same length.")
    if not vector_a:
        return None

    numerator = sum(value_a * value_b for value_a, value_b in zip(vector_a, vector_b))
    denominator_a = math.sqrt(sum(value_a**2 for value_a in vector_a))
    denominator_b = math.sqrt(sum(value_b**2 for value_b in vector_b))
    denominator = denominator_a * denominator_b
    if denominator == 0:
        return None

    return numerator / denominator


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


def calculate_relative_l2_distance(
    matrix_a: Sequence[object],
    matrix_b: Sequence[object],
    *,
    epsilon: float = 1e-8,
) -> float:
    """Calculate sqrt(sum(((a_ij - b_ij) / (abs(a_ij) + epsilon))^2))."""
    if not isinstance(epsilon, (int, float)) or isinstance(epsilon, bool):
        raise ValueError("epsilon must be a positive number.")
    if epsilon <= 0 or not math.isfinite(float(epsilon)):
        raise ValueError("epsilon must be a positive number.")

    rows_a = _coerce_numeric_matrix(matrix_a, "matrix_a")
    rows_b = _coerce_numeric_matrix(matrix_b, "matrix_b")
    _validate_same_matrix_shape(rows_a, rows_b)

    squared_sum = 0.0
    for row_a, row_b in zip(rows_a, rows_b):
        for value_a, value_b in zip(row_a, row_b):
            relative_difference = (value_a - value_b) / (abs(value_a) + epsilon)
            squared_sum += relative_difference**2

    return math.sqrt(squared_sum)


def calculate_secondary_ability_relative_distance(
    primary_rows: Sequence[dict[str, Any]],
    comparison_rows: Sequence[dict[str, Any]],
    *,
    epsilon: float = 1e-8,
    ability_fields: Sequence[str] = SECONDARY_ABILITY_SCORE_FIELDS,
) -> dict[str, object]:
    """Calculate masked relative distance for ordered secondary-ability rows."""
    sorted_primary_rows = _sort_secondary_ability_rows(primary_rows)
    sorted_comparison_rows = _sort_secondary_ability_rows(comparison_rows)
    if len(sorted_primary_rows) != len(sorted_comparison_rows):
        return {
            "distance": None,
            "reason": "row count mismatch",
            "row_count_primary": len(sorted_primary_rows),
            "row_count_comparison": len(sorted_comparison_rows),
        }

    values_primary: list[float] = []
    values_comparison: list[float] = []
    used_positions: list[dict[str, object]] = []
    skipped_count = 0
    for row_index, (primary_row, comparison_row) in enumerate(
        zip(sorted_primary_rows, sorted_comparison_rows)
    ):
        primary_scores = _extract_secondary_ability_scores(primary_row)
        comparison_scores = _extract_secondary_ability_scores(comparison_row)
        for field in ability_fields:
            value_primary = _coerce_optional_numeric_value(primary_scores.get(field))
            value_comparison = _coerce_optional_numeric_value(
                comparison_scores.get(field)
            )
            if value_primary is None or value_comparison is None:
                skipped_count += 1
                continue

            values_primary.append(value_primary)
            values_comparison.append(value_comparison)
            used_positions.append(
                {
                    "row_index": row_index,
                    "field": field,
                    "primary_training_date": primary_row.get("training_date"),
                    "comparison_training_date": comparison_row.get("training_date"),
                }
            )

    if not values_primary:
        return {
            "distance": None,
            "reason": "no common non-null secondary ability scores",
            "row_count": len(sorted_primary_rows),
            "used_count": 0,
            "skipped_count": skipped_count,
        }

    return {
        "distance": calculate_relative_l2_distance(
            values_primary,
            values_comparison,
            epsilon=epsilon,
        ),
        "row_count": len(sorted_primary_rows),
        "used_count": len(values_primary),
        "skipped_count": skipped_count,
        "used_positions": used_positions,
    }


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


def _coerce_numeric_matrix(matrix: Sequence[object], field_name: str) -> list[list[float]]:
    if isinstance(matrix, (str, bytes)) or not isinstance(matrix, Sequence):
        raise ValueError(f"{field_name} must be a non-empty sequence.")
    if not matrix:
        raise ValueError(f"{field_name} must be a non-empty sequence.")

    if _is_scalar_numeric_value(matrix[0]):
        return [[_coerce_required_float(value, field_name) for value in matrix]]

    rows: list[list[float]] = []
    for row_index, row in enumerate(matrix):
        row_name = f"{field_name}[{row_index}]"
        if isinstance(row, (str, bytes)) or not isinstance(row, Sequence):
            raise ValueError(f"{row_name} must be a non-empty sequence.")
        if not row:
            raise ValueError(f"{row_name} must be a non-empty sequence.")
        rows.append([_coerce_required_float(value, row_name) for value in row])

    return rows


def _sort_secondary_ability_rows(
    rows: Sequence[dict[str, Any]],
) -> list[dict[str, Any]]:
    return sorted(rows, key=lambda row: str(row.get("training_date") or ""))


def _extract_secondary_ability_scores(row: dict[str, Any]) -> dict[str, Any]:
    scores = row.get("secondary_ability_scores")
    return scores if isinstance(scores, dict) else {}


def _coerce_optional_numeric_value(value: object) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        numeric_value = float(value)
    elif isinstance(value, str):
        stripped_value = value.strip()
        if not stripped_value:
            return None
        try:
            numeric_value = float(stripped_value)
        except ValueError:
            return None
    else:
        return None

    return numeric_value if math.isfinite(numeric_value) else None


def _validate_same_matrix_shape(
    matrix_a: list[list[float]],
    matrix_b: list[list[float]],
) -> None:
    if len(matrix_a) != len(matrix_b):
        raise ValueError("matrix_a and matrix_b must have the same shape.")
    for row_a, row_b in zip(matrix_a, matrix_b):
        if len(row_a) != len(row_b):
            raise ValueError("matrix_a and matrix_b must have the same shape.")


def _coerce_required_float(value: object, field_name: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must contain only finite numeric values.")
    if isinstance(value, (int, float)):
        numeric_value = float(value)
    elif isinstance(value, str):
        stripped_value = value.strip()
        if not stripped_value:
            raise ValueError(f"{field_name} must contain only finite numeric values.")
        try:
            numeric_value = float(stripped_value)
        except ValueError as exc:
            raise ValueError(
                f"{field_name} must contain only finite numeric values."
            ) from exc
    else:
        raise ValueError(f"{field_name} must contain only finite numeric values.")

    if not math.isfinite(numeric_value):
        raise ValueError(f"{field_name} must contain only finite numeric values.")
    return numeric_value


def _is_scalar_numeric_value(value: object) -> bool:
    return isinstance(value, (int, float, str)) and not isinstance(value, bool)


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
