"""Tests for reusable graph query registration."""

from __future__ import annotations

import unittest

from src.similar_user.data_access.cypher_queries import (
    DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
)
from src.similar_user.data_access.graph_query_registry import (
    GRAPH_QUERY_SPECS,
    GraphQueryCategory,
    get_graph_query_spec,
    list_graph_query_specs,
)


class GraphQueryRegistryTest(unittest.TestCase):
    def test_registered_disease_expansion_declares_contract(self) -> None:
        spec = get_graph_query_spec("disease_taskset_task_game_sampled_per_game")

        self.assertEqual(spec.name, "disease_taskset_task_game_sampled_per_game")
        self.assertEqual(spec.category, GraphQueryCategory.ENTITY_EXPANSION)
        self.assertEqual(spec.source_label, "Disease")
        self.assertEqual(spec.source_parameter, "disease_id")
        self.assertEqual(
            spec.path_shape,
            "(d:Disease)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
        )
        self.assertEqual(spec.row_fields, ("d", "s", "i", "g"))
        self.assertEqual(spec.group_field, "g")
        self.assertEqual(spec.query, DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY)

    def test_list_graph_query_specs_can_filter_by_category(self) -> None:
        specs = list_graph_query_specs(category=GraphQueryCategory.ENTITY_EXPANSION)

        self.assertEqual(
            tuple(spec.name for spec in specs),
            ("disease_taskset_task_game_sampled_per_game",),
        )

    def test_list_graph_query_specs_can_filter_by_category_string(self) -> None:
        specs = list_graph_query_specs(category="entity_expansion")

        self.assertEqual(
            tuple(spec.name for spec in specs),
            ("disease_taskset_task_game_sampled_per_game",),
        )

    def test_registered_specs_are_keyed_by_name(self) -> None:
        for name, spec in GRAPH_QUERY_SPECS.items():
            with self.subTest(name=name):
                self.assertEqual(name, spec.name)

    def test_get_graph_query_spec_rejects_unknown_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "Supported graph queries"):
            get_graph_query_spec("missing_query")


if __name__ == "__main__":
    unittest.main()
