"""Structured registry for reusable graph queries outside PathPattern builds."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .cypher_queries import (
    DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
    DISTINCT_TRAINING_GAMES_QUERY,
    PATIENT_DISEASE_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_DISEASE_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_DISEASES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_SYMPTOMS_BY_START_DATE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY,
    PATIENT_DISTINCT_UNKNOWNS_BY_START_DATE_QUERY,
    PATIENT_GAMES_BY_DATE_RANGE_QUERY,
    PATIENT_GAMES_BY_END_DATE_QUERY,
    PATIENT_GAMES_BY_START_DATE_QUERY,
    PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_GAME_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_IDS_QUERY,
    PATIENT_IDS_WITH_TRAINING_ON_DATE_QUERY,
    PATIENT_SYMPTOM_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_SYMPTOM_SET_COMPARISON_BY_START_DATE_QUERY,
    PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY,
    PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY,
    PATIENT_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY,
    PATIENT_TRAINING_TASK_HISTORY_QUERY,
    PATIENT_UNKNOWN_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY,
    PATIENT_UNKNOWN_SET_COMPARISON_BY_START_DATE_QUERY,
    SYMPTOM_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
    UNKNOWN_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
)


class GraphQueryCategory(str, Enum):
    """High-level purpose of a reusable graph query."""

    ENTITY_EXPANSION = "entity_expansion"
    PATIENT_IDENTITY = "patient_identity"
    PATIENT_TRAINING_HISTORY = "patient_training_history"
    PATIENT_GAME_COLLECTION = "patient_game_collection"
    PATIENT_ENTITY_COLLECTION = "patient_entity_collection"
    PATIENT_SET_COMPARISON = "patient_set_comparison"
    PATIENT_SCORE_COMPARISON = "patient_score_comparison"


@dataclass(frozen=True)
class GraphQuerySpec:
    """Data-access contract for a reusable graph query."""

    name: str
    category: GraphQueryCategory
    description: str
    source_label: str
    source_parameters: tuple[str, ...]
    path_shape: str
    row_fields: tuple[str, ...]
    group_field: str | None
    query: str

    @property
    def source_parameter(self) -> str:
        """Return the first source parameter for single-source query callers."""
        return self.source_parameters[0]


def _spec(
    *,
    name: str,
    category: GraphQueryCategory,
    description: str,
    source_label: str,
    source_parameters: tuple[str, ...],
    path_shape: str,
    row_fields: tuple[str, ...],
    query: str,
    group_field: str | None = None,
) -> GraphQuerySpec:
    return GraphQuerySpec(
        name=name,
        category=category,
        description=description,
        source_label=source_label,
        source_parameters=source_parameters,
        path_shape=path_shape,
        row_fields=row_fields,
        group_field=group_field,
        query=query,
    )


DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_SPEC = _spec(
    name="disease_taskset_task_game_sampled_per_game",
    category=GraphQueryCategory.ENTITY_EXPANSION,
    description="从疾病扩展到相关游戏，每个游戏随机保留一条路径",
    source_label="Disease",
    source_parameters=("disease_id",),
    path_shape="(d:Disease)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
    row_fields=("d", "s", "i", "g"),
    group_field="g",
    query=DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
)

SYMPTOM_TASKSET_TASK_GAME_SAMPLED_PER_GAME_SPEC = _spec(
    name="symptom_taskset_task_game_sampled_per_game",
    category=GraphQueryCategory.ENTITY_EXPANSION,
    description="从症状扩展到相关游戏，每个游戏随机保留一条路径",
    source_label="Symptom",
    source_parameters=("symptom_id",),
    path_shape="(sym:Symptom)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
    row_fields=("sym", "s", "i", "g"),
    group_field="g",
    query=SYMPTOM_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
)

UNKNOWN_TASKSET_TASK_GAME_SAMPLED_PER_GAME_SPEC = _spec(
    name="unknown_taskset_task_game_sampled_per_game",
    category=GraphQueryCategory.ENTITY_EXPANSION,
    description="从未知节点扩展到相关游戏，每个游戏随机保留一条路径",
    source_label="Unknown",
    source_parameters=("unknown_id",),
    path_shape="(un:Unknown)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
    row_fields=("un", "s", "i", "g"),
    group_field="g",
    query=UNKNOWN_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
)

PATIENT_IDENTITY_SPECS = (
    _spec(
        name="patient_ids",
        category=GraphQueryCategory.PATIENT_IDENTITY,
        description="查询全库患者 ID",
        source_label="Patient",
        source_parameters=(),
        path_shape="(p:Patient)",
        row_fields=("patient_id",),
        query=PATIENT_IDS_QUERY,
    ),
    _spec(
        name="patient_ids_with_training_on_date",
        category=GraphQueryCategory.PATIENT_IDENTITY,
        description="查询指定日期有训练记录的患者 ID",
        source_label="Patient",
        source_parameters=("base_date",),
        path_shape="(p:Patient)--(s:TaskInstanceSet)",
        row_fields=("patient_id",),
        query=PATIENT_IDS_WITH_TRAINING_ON_DATE_QUERY,
    ),
)

PATIENT_TRAINING_HISTORY_SPECS = (
    _spec(
        name="patient_training_date_games_by_start_date",
        category=GraphQueryCategory.PATIENT_TRAINING_HISTORY,
        description="查询患者从某日期开始的训练日期与游戏集合",
        source_label="Patient",
        source_parameters=("patient_id",),
        path_shape="(p:Patient)--(s1:TaskInstanceSet)--(i1:TaskInstance)--(g:Game)",
        row_fields=("trainingDate", "games"),
        query=PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY,
    ),
    _spec(
        name="patient_task_instance_set_ordered_training_dates",
        category=GraphQueryCategory.PATIENT_TRAINING_HISTORY,
        description="查询患者训练日期的有序列表",
        source_label="Patient",
        source_parameters=("patient_id",),
        path_shape="(p:Patient)--(s:TaskInstanceSet)",
        row_fields=("p", "orderedDatesa"),
        query=PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY,
    ),
    _spec(
        name="patient_training_task_history",
        category=GraphQueryCategory.PATIENT_TRAINING_HISTORY,
        description="查询患者训练任务历史明细",
        source_label="Patient",
        source_parameters=("patient_id",),
        path_shape="(p:Patient)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
        row_fields=("trainingDate", "s", "i", "g"),
        query=PATIENT_TRAINING_TASK_HISTORY_QUERY,
    ),
    _spec(
        name="patient_training_task_history_by_date_window",
        category=GraphQueryCategory.PATIENT_TRAINING_HISTORY,
        description="查询患者左闭右开日期窗口内的游戏历史",
        source_label="Patient",
        source_parameters=("patient_id", "start_date", "end_date"),
        path_shape="(p:Patient)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
        row_fields=("trainingDate", "g"),
        query=PATIENT_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY,
    ),
)

_PATIENT_GAME_COLLECTION_BASE_SPECS = (
    _spec(
        name="distinct_training_games",
        category=GraphQueryCategory.PATIENT_GAME_COLLECTION,
        description="查询全库训练记录中出现过的去重游戏",
        source_label="TaskInstanceSet",
        source_parameters=(),
        path_shape="(:TaskInstanceSet)--(:TaskInstance)--(g:Game)",
        row_fields=("g",),
        query=DISTINCT_TRAINING_GAMES_QUERY,
    ),
)

_PATIENT_GAME_COLLECTION_DEFINITIONS = (
    (
        "patient_distinct_games",
        "去重游戏",
        PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY,
        PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY,
        PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY,
    ),
    (
        "patient_games",
        "游戏记录",
        PATIENT_GAMES_BY_START_DATE_QUERY,
        PATIENT_GAMES_BY_END_DATE_QUERY,
        PATIENT_GAMES_BY_DATE_RANGE_QUERY,
    ),
)

PATIENT_GAME_COLLECTION_SPECS = (
    *_PATIENT_GAME_COLLECTION_BASE_SPECS,
    *tuple(
        _spec(
            name=f"{prefix}_by_{date_variant}",
            category=GraphQueryCategory.PATIENT_GAME_COLLECTION,
            description=f"查询患者{date_description}的{description_suffix}",
            source_label="Patient",
            source_parameters=source_parameters,
            path_shape="(p:Patient)--(s1:TaskInstanceSet)--(i1:TaskInstance)--(g:Game)",
            row_fields=("g",),
            query=query,
        )
        for (
            prefix,
            description_suffix,
            start_query,
            end_query,
            range_query,
        ) in _PATIENT_GAME_COLLECTION_DEFINITIONS
        for date_variant, date_description, source_parameters, query in (
            ("start_date", "从某日期开始", ("patient_id", "start_date"), start_query),
            ("end_date", "早于 end_date", ("patient_id", "end_date"), end_query),
            (
                "date_range",
                "左闭右开日期区间内",
                ("patient_id", "start_date", "end_date"),
                range_query,
            ),
        )
    ),
)

_PATIENT_ENTITY_DEFINITIONS = (
    (
        "patient_distinct_task_instances",
        "TaskInstance",
        "i1",
        "(p:Patient)--(s1:TaskInstanceSet)--(i1:TaskInstance)",
        PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY,
        PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY,
        PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY,
    ),
    (
        "patient_distinct_symptoms",
        "Symptom",
        "sym",
        "(p:Patient)--(s1:TaskInstanceSet)--(sym:Symptom)",
        PATIENT_DISTINCT_SYMPTOMS_BY_START_DATE_QUERY,
        PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY,
        PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY,
    ),
    (
        "patient_distinct_diseases",
        "Disease",
        "dis",
        "(p:Patient)--(s1:TaskInstanceSet)--(dis:Disease)",
        PATIENT_DISTINCT_DISEASES_BY_START_DATE_QUERY,
        PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY,
        PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY,
    ),
    (
        "patient_distinct_unknowns",
        "Unknown",
        "un",
        "(p:Patient)--(s1:TaskInstanceSet)--(un:Unknown)",
        PATIENT_DISTINCT_UNKNOWNS_BY_START_DATE_QUERY,
        PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY,
        PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY,
    ),
)

PATIENT_ENTITY_COLLECTION_SPECS = tuple(
    _spec(
        name=f"{prefix}_by_{date_variant}",
        category=GraphQueryCategory.PATIENT_ENTITY_COLLECTION,
        description=f"查询患者{date_description}的去重 {entity_label} 节点",
        source_label="Patient",
        source_parameters=source_parameters,
        path_shape=path_shape,
        row_fields=(row_field,),
        query=query,
    )
    for (
        prefix,
        entity_label,
        row_field,
        path_shape,
        start_query,
        end_query,
        range_query,
    ) in _PATIENT_ENTITY_DEFINITIONS
    for date_variant, date_description, source_parameters, query in (
        ("start_date", "从某日期开始", ("patient_id", "start_date"), start_query),
        ("end_date", "早于 end_date", ("patient_id", "end_date"), end_query),
        (
            "date_range",
            "左闭右开日期区间内",
            ("patient_id", "start_date", "end_date"),
            range_query,
        ),
    )
)

_PATIENT_SET_COMPARISON_DEFINITIONS = (
    (
        "patient_game_set_comparison",
        "Game",
        ("games1", "games2"),
        "(p:Patient)--(s:TaskInstanceSet)--(:TaskInstance)--(g:Game)",
        PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY,
        PATIENT_GAME_SET_COMPARISON_BY_END_DATE_QUERY,
        PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    ),
    (
        "patient_symptom_set_comparison",
        "Symptom",
        ("symptoms1", "symptoms2"),
        "(p:Patient)--(s:TaskInstanceSet)--(sym:Symptom)",
        PATIENT_SYMPTOM_SET_COMPARISON_BY_START_DATE_QUERY,
        PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY,
        PATIENT_SYMPTOM_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    ),
    (
        "patient_disease_set_comparison",
        "Disease",
        ("diseases1", "diseases2"),
        "(p:Patient)--(s:TaskInstanceSet)--(dis:Disease)",
        PATIENT_DISEASE_SET_COMPARISON_BY_START_DATE_QUERY,
        PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY,
        PATIENT_DISEASE_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    ),
    (
        "patient_unknown_set_comparison",
        "Unknown",
        ("unknowns1", "unknowns2"),
        "(p:Patient)--(s:TaskInstanceSet)--(un:Unknown)",
        PATIENT_UNKNOWN_SET_COMPARISON_BY_START_DATE_QUERY,
        PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY,
        PATIENT_UNKNOWN_SET_COMPARISON_BY_DATE_RANGE_QUERY,
    ),
)

PATIENT_SET_COMPARISON_SPECS = tuple(
    _spec(
        name=f"{prefix}_by_{date_variant}",
        category=GraphQueryCategory.PATIENT_SET_COMPARISON,
        description=f"比较两个患者{date_description}的 {entity_label} 集合",
        source_label="Patient",
        source_parameters=source_parameters,
        path_shape=path_shape,
        row_fields=row_fields,
        query=query,
    )
    for (
        prefix,
        entity_label,
        row_fields,
        path_shape,
        start_query,
        end_query,
        range_query,
    ) in _PATIENT_SET_COMPARISON_DEFINITIONS
    for date_variant, date_description, source_parameters, query in (
        (
            "start_date",
            "从某日期开始",
            ("primary_patient_id", "comparison_patient_id", "start_date"),
            start_query,
        ),
        (
            "end_date",
            "早于 end_date",
            ("primary_patient_id", "comparison_patient_id", "end_date"),
            end_query,
        ),
        (
            "date_range",
            "左闭右开日期区间内",
            (
                "primary_patient_id",
                "comparison_patient_id",
                "start_date",
                "end_date",
            ),
            range_query,
        ),
    )
)

PATIENT_SCORE_COMPARISON_SPECS = (
    _spec(
        name="patient_game_norm_score_series_comparison_by_end_date",
        category=GraphQueryCategory.PATIENT_SCORE_COMPARISON,
        description="查询两个患者共同游戏上的常模分序列",
        source_label="Patient",
        source_parameters=("primary_patient_id", "comparison_patient_id", "end_date"),
        path_shape="(p:Patient)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
        row_fields=("game", "scores_p1", "scores_p2"),
        query=PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY,
    ),
)

GRAPH_QUERY_SPEC_LIST = (
    DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_SPEC,
    SYMPTOM_TASKSET_TASK_GAME_SAMPLED_PER_GAME_SPEC,
    UNKNOWN_TASKSET_TASK_GAME_SAMPLED_PER_GAME_SPEC,
    *PATIENT_IDENTITY_SPECS,
    *PATIENT_TRAINING_HISTORY_SPECS,
    *PATIENT_GAME_COLLECTION_SPECS,
    *PATIENT_ENTITY_COLLECTION_SPECS,
    *PATIENT_SET_COMPARISON_SPECS,
    *PATIENT_SCORE_COMPARISON_SPECS,
)

GRAPH_QUERY_SPECS: dict[str, GraphQuerySpec] = {
    spec.name: spec for spec in GRAPH_QUERY_SPEC_LIST
}


def get_graph_query_spec(name: str) -> GraphQuerySpec:
    """Return a registered graph query spec by public query name."""
    normalized_name = name.strip() if isinstance(name, str) else ""
    try:
        return GRAPH_QUERY_SPECS[normalized_name]
    except KeyError as exc:
        supported = ", ".join(sorted(GRAPH_QUERY_SPECS)) or "none"
        raise ValueError(
            f"Unsupported graph query: {name}. Supported graph queries: {supported}"
        ) from exc


def list_graph_query_specs(
    *,
    category: GraphQueryCategory | str | None = None,
) -> tuple[GraphQuerySpec, ...]:
    """Return registered graph query specs, optionally filtered by category."""
    specs = tuple(GRAPH_QUERY_SPECS[name] for name in sorted(GRAPH_QUERY_SPECS))
    if category is None:
        return specs

    normalized_category = (
        category
        if isinstance(category, GraphQueryCategory)
        else GraphQueryCategory(str(category).strip())
    )
    return tuple(spec for spec in specs if spec.category == normalized_category)
