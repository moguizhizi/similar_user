"""Explicit mapping between supported path patterns and Cypher queries."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias

from ..domain.graph_schema import PathPattern
from ..domain.path_models import (
    PatientTasksetDiseaseTasksetPatientPath,
    PatientTasksetSymptomTasksetPatientPath,
    PatientTasksetTaskGameTaskTasksetPatientPath,
)
from .cypher_queries import (
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY,
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


PathModel: TypeAlias = (
    type[PatientTasksetTaskGameTaskTasksetPatientPath]
    | type[PatientTasksetDiseaseTasksetPatientPath]
    | type[PatientTasksetSymptomTasksetPatientPath]
)


class QueryDateVariant(str, Enum):
    """Static query variant selected by date-window bounds."""

    BASE = "base"
    START_DATE = "start_date"
    END_DATE = "end_date"
    DATE_RANGE = "date_range"


@dataclass(frozen=True)
class QueryDateWindow:
    """Date bounds used to select one static Cypher query variant."""

    start_date: str | None = None
    end_date: str | None = None

    @property
    def variant(self) -> QueryDateVariant:
        """Return the query variant implied by the supplied date bounds."""
        if self.start_date is not None and self.end_date is not None:
            return QueryDateVariant.DATE_RANGE
        if self.start_date is not None:
            return QueryDateVariant.START_DATE
        if self.end_date is not None:
            return QueryDateVariant.END_DATE
        return QueryDateVariant.BASE

    def parameters(self) -> dict[str, str]:
        """Return only date parameters required by this window."""
        parameters: dict[str, str] = {}
        if self.start_date is not None:
            parameters["start_date"] = self.start_date
        if self.end_date is not None:
            parameters["end_date"] = self.end_date
        return parameters


@dataclass(frozen=True)
class QueryVariants:
    """Date-bound variants for one Cypher query purpose."""

    base: str
    by_start_date: str
    by_end_date: str
    by_date_range: str

    def select(self, window: QueryDateWindow) -> str:
        """Select the static query matching the supplied date window."""
        if window.variant == QueryDateVariant.DATE_RANGE:
            return self.by_date_range
        if window.variant == QueryDateVariant.START_DATE:
            return self.by_start_date
        if window.variant == QueryDateVariant.END_DATE:
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

    families: dict[str, PatternQueryFamilySpec]

    def family(self, name: str) -> PatternQueryFamilySpec:
        """Return a registered query family by its public family name."""
        normalized_name = name.strip() if isinstance(name, str) else ""
        try:
            return self.families[normalized_name]
        except KeyError as exc:
            supported = ", ".join(sorted(self.families))
            raise ValueError(
                f"Pattern does not support query family: {name}. "
                f"Supported query families: {supported}"
            ) from exc


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
        families={
            "date_window": PatternQueryFamilySpec(
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
            "training_order": PatternQueryFamilySpec(
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
        },
    ),
)

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_SPEC = PathPatternSpec(
    pattern=PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT,
    description="患者-任务集-疾病-任务集-患者",
    path_shape="(p:Patient)--(s1:TaskInstanceSet)--(dis:Disease)--(s2:TaskInstanceSet)--(p2:Patient)",
    row_fields=("p", "s1", "dis", "s2", "p2"),
    group_field="dis",
    path_model=PatientTasksetDiseaseTasksetPatientPath,
    queries=PatternQuerySet(
        families={
            "date_window": PatternQueryFamilySpec(
                randomized_path=QueryVariants(
                    base=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
                    by_start_date=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
                    by_end_date=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
                    by_date_range=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
                ),
                statistics=QueryVariants(
                    base=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
                    by_start_date=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
                    by_end_date=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
                    by_date_range=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
                ),
            ),
            "training_order": PatternQueryFamilySpec(
                randomized_path=QueryVariants(
                    base=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY,
                    by_start_date=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY,
                    by_end_date=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY,
                    by_date_range=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
                ),
                statistics=QueryVariants(
                    base=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY,
                    by_start_date=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY,
                    by_end_date=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY,
                    by_date_range=PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
                ),
            ),
        },
    ),
)

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_SPEC = PathPatternSpec(
    pattern=PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT,
    description="患者-任务集-症状-任务集-患者",
    path_shape="(p:Patient)--(s1:TaskInstanceSet)--(sym:Symptom)--(s2:TaskInstanceSet)--(p2:Patient)",
    row_fields=("p", "s1", "sym", "s2", "p2"),
    group_field="sym",
    path_model=PatientTasksetSymptomTasksetPatientPath,
    queries=PatternQuerySet(
        families={
            "date_window": PatternQueryFamilySpec(
                randomized_path=QueryVariants(
                    base=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
                    by_start_date=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
                    by_end_date=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
                    by_date_range=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
                ),
                statistics=QueryVariants(
                    base=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
                    by_start_date=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
                    by_end_date=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
                    by_date_range=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
                ),
            ),
            "training_order": PatternQueryFamilySpec(
                randomized_path=QueryVariants(
                    base=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY,
                    by_start_date=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY,
                    by_end_date=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY,
                    by_date_range=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
                ),
                statistics=QueryVariants(
                    base=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY,
                    by_start_date=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY,
                    by_end_date=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY,
                    by_date_range=PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
                ),
            ),
        },
    ),
)


PATH_PATTERN_SPECS: dict[PathPattern, PathPatternSpec] = {
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT_SPEC.pattern: PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT_SPEC,
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_SPEC.pattern: PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_SPEC,
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_SPEC.pattern: PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_SPEC,
}

PATH_PATTERN_ALIASES: dict[str, PathPattern] = {
    "patient_game_patient": PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    "patient_disease_patient": PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT,
    "patient_symptom_patient": PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT,
}


def available_path_pattern_aliases() -> tuple[str, ...]:
    """Return public pattern aliases accepted from external string input."""
    return tuple(sorted(PATH_PATTERN_ALIASES))


def resolve_path_pattern_alias(value: str) -> PathPattern:
    """Resolve a public pattern alias from external string input."""
    if isinstance(value, str) and value.strip():
        normalized_value = value.strip()
        alias_pattern = PATH_PATTERN_ALIASES.get(normalized_value)
        if alias_pattern is not None:
            return alias_pattern
        supported = ", ".join(available_path_pattern_aliases())
        raise ValueError(
            f"Unsupported path pattern alias: {normalized_value}. "
            f"Supported aliases: {supported}"
        )
    raise ValueError("pattern must be a non-empty supported path pattern alias.")


def get_path_pattern_spec(pattern: PathPattern | str) -> PathPatternSpec:
    """Return the data-access spec for a query-supported path pattern."""
    normalized_pattern = resolve_path_pattern(pattern)
    try:
        return PATH_PATTERN_SPECS[normalized_pattern]
    except KeyError as exc:
        raise ValueError(
            f"Path pattern has no registered Cypher query set: {normalized_pattern.value}"
        ) from exc


def resolve_path_pattern(value: PathPattern | str) -> PathPattern:
    """Resolve a public alias, stored enum value, or internal enum to a PathPattern."""
    if isinstance(value, PathPattern):
        return value
    if isinstance(value, str) and value.strip():
        normalized_value = value.strip()
        alias_pattern = PATH_PATTERN_ALIASES.get(normalized_value)
        if alias_pattern is not None:
            return alias_pattern
        try:
            return PathPattern(normalized_value)
        except ValueError as exc:
            supported = ", ".join(available_path_pattern_aliases())
            raise ValueError(
                f"Unsupported path pattern alias: {normalized_value}. "
                f"Supported aliases: {supported}"
            ) from exc
    raise ValueError("pattern must be a non-empty supported path pattern string.")
