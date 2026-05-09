"""Explicit mapping between supported path patterns and Cypher queries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from ..domain.graph_schema import PathPattern
from ..domain.path_models import PatientTasksetTaskGameTaskTasksetPatientPath
from .cypher_queries import (
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY,
)


PathModel: TypeAlias = type[PatientTasksetTaskGameTaskTasksetPatientPath]


@dataclass(frozen=True)
class QueryVariants:
    """Date-bound variants for one Cypher query purpose."""

    base: str
    by_start_date: str
    by_end_date: str
    by_date_range: str

    def select(self, *, start_date: str | None, end_date: str | None) -> str:
        """Select the static query matching the supplied date-bound shape."""
        if start_date is not None and end_date is not None:
            return self.by_date_range
        if start_date is not None:
            return self.by_start_date
        if end_date is not None:
            return self.by_end_date
        return self.base


@dataclass(frozen=True)
class PatternQueryFamilySpec:
    """Paired Cypher queries for one candidate-space family."""

    randomized_path: QueryVariants
    statistics: QueryVariants


@dataclass(frozen=True)
class PatternQuerySet:
    """Cypher query families for one path pattern."""

    date_window: PatternQueryFamilySpec
    training_order: PatternQueryFamilySpec

    def family(self, name: str) -> PatternQueryFamilySpec:
        """Return the query family by its public family name."""
        if name == "date_window":
            return self.date_window
        if name == "training_order":
            return self.training_order
        raise ValueError(f"Unsupported pattern query family: {name}")


@dataclass(frozen=True)
class PathPatternSpec:
    """Data-access contract for one fixed path pattern."""

    pattern: PathPattern
    description: str
    path_shape: str
    row_fields: tuple[str, ...]
    group_field: str
    path_model: PathModel
    queries: PatternQuerySet


PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT_SPEC = PathPatternSpec(
    pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    description="患者-任务集-任务-游戏-任务-任务集-患者",
    path_shape="(p:Patient)--(s1:TaskInstanceSet)--(i1:TaskInstance)--(g:Game)--(i2:TaskInstance)--(s2:TaskInstanceSet)--(p2:Patient)",
    row_fields=("p", "s1", "i1", "g", "i2", "s2", "p2"),
    group_field="g",
    path_model=PatientTasksetTaskGameTaskTasksetPatientPath,
    queries=PatternQuerySet(
        date_window=PatternQueryFamilySpec(
            randomized_path=QueryVariants(
                base=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
                by_start_date=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
                by_end_date=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
                by_date_range=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            ),
            statistics=QueryVariants(
                base=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
                by_start_date=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
                by_end_date=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
                by_date_range=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            ),
        ),
        training_order=PatternQueryFamilySpec(
            randomized_path=QueryVariants(
                base=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_QUERY,
                by_start_date=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY,
                by_end_date=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
                by_date_range=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
            ),
            statistics=QueryVariants(
                base=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY,
                by_start_date=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY,
                by_end_date=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY,
                by_date_range=PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
            ),
        ),
    ),
)


PATH_PATTERN_SPECS: dict[PathPattern, PathPatternSpec] = {
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT_SPEC.pattern: PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT_SPEC,
}


def get_path_pattern_spec(pattern: PathPattern | str) -> PathPatternSpec:
    """Return the data-access spec for a query-supported path pattern."""
    normalized_pattern = _coerce_path_pattern(pattern)
    try:
        return PATH_PATTERN_SPECS[normalized_pattern]
    except KeyError as exc:
        raise ValueError(
            f"Path pattern has no registered Cypher query set: {normalized_pattern.value}"
        ) from exc


def _coerce_path_pattern(value: PathPattern | str) -> PathPattern:
    if isinstance(value, PathPattern):
        return value
    if isinstance(value, str) and value.strip():
        return PathPattern(value.strip())
    raise ValueError("pattern must be a non-empty supported path pattern string.")
