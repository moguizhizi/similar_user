"""Structured registry for reusable graph queries outside PathPattern builds."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .cypher_queries import DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY


class GraphQueryCategory(str, Enum):
    """High-level purpose of a reusable graph query."""

    ENTITY_EXPANSION = "entity_expansion"


@dataclass(frozen=True)
class GraphQuerySpec:
    """Data-access contract for a reusable graph query."""

    name: str
    category: GraphQueryCategory
    description: str
    source_label: str
    source_parameter: str
    path_shape: str
    row_fields: tuple[str, ...]
    group_field: str | None
    query: str


DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_SPEC = GraphQuerySpec(
    name="disease_taskset_task_game_sampled_per_game",
    category=GraphQueryCategory.ENTITY_EXPANSION,
    description="从疾病扩展到相关游戏，每个游戏随机保留一条路径",
    source_label="Disease",
    source_parameter="disease_id",
    path_shape="(d:Disease)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
    row_fields=("d", "s", "i", "g"),
    group_field="g",
    query=DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
)


GRAPH_QUERY_SPECS: dict[str, GraphQuerySpec] = {
    DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_SPEC.name: (
        DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_SPEC
    ),
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
