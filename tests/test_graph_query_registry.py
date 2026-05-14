"""Tests for reusable graph query registration."""

from __future__ import annotations

import unittest

from src.similar_user.data_access.cypher_queries import (
    DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
    PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY,
    PATIENT_GAMES_BY_DATE_RANGE_QUERY,
    SYMPTOM_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
    UNKNOWN_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY,
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
        self.assertEqual(spec.source_parameters, ("disease_id",))
        self.assertEqual(spec.source_parameter, "disease_id")
        self.assertEqual(
            spec.path_shape,
            "(d:Disease)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
        )
        self.assertEqual(spec.row_fields, ("d", "s", "i", "g"))
        self.assertEqual(spec.group_field, "g")
        self.assertEqual(spec.query, DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY)

    def test_registered_symptom_expansion_declares_contract(self) -> None:
        spec = get_graph_query_spec("symptom_taskset_task_game_sampled_per_game")

        self.assertEqual(spec.name, "symptom_taskset_task_game_sampled_per_game")
        self.assertEqual(spec.category, GraphQueryCategory.ENTITY_EXPANSION)
        self.assertEqual(spec.source_label, "Symptom")
        self.assertEqual(spec.source_parameter, "symptom_id")
        self.assertEqual(
            spec.path_shape,
            "(sym:Symptom)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
        )
        self.assertEqual(spec.row_fields, ("sym", "s", "i", "g"))
        self.assertEqual(spec.group_field, "g")
        self.assertEqual(spec.query, SYMPTOM_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY)

    def test_registered_unknown_expansion_declares_contract(self) -> None:
        spec = get_graph_query_spec("unknown_taskset_task_game_sampled_per_game")

        self.assertEqual(spec.name, "unknown_taskset_task_game_sampled_per_game")
        self.assertEqual(spec.category, GraphQueryCategory.ENTITY_EXPANSION)
        self.assertEqual(spec.source_label, "Unknown")
        self.assertEqual(spec.source_parameter, "unknown_id")
        self.assertEqual(
            spec.path_shape,
            "(un:Unknown)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
        )
        self.assertEqual(spec.row_fields, ("un", "s", "i", "g"))
        self.assertEqual(spec.group_field, "g")
        self.assertEqual(spec.query, UNKNOWN_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY)

    def test_list_graph_query_specs_can_filter_by_category(self) -> None:
        specs = list_graph_query_specs(category=GraphQueryCategory.ENTITY_EXPANSION)

        self.assertEqual(
            tuple(spec.name for spec in specs),
            (
                "disease_taskset_task_game_sampled_per_game",
                "symptom_taskset_task_game_sampled_per_game",
                "unknown_taskset_task_game_sampled_per_game",
            ),
        )

    def test_list_graph_query_specs_can_filter_by_category_string(self) -> None:
        specs = list_graph_query_specs(category="entity_expansion")

        self.assertEqual(
            tuple(spec.name for spec in specs),
            (
                "disease_taskset_task_game_sampled_per_game",
                "symptom_taskset_task_game_sampled_per_game",
                "unknown_taskset_task_game_sampled_per_game",
            ),
        )

    def test_registered_patient_identity_query_declares_contract(self) -> None:
        spec = get_graph_query_spec("patient_ids_with_training_on_date")

        self.assertEqual(spec.category, GraphQueryCategory.PATIENT_IDENTITY)
        self.assertEqual(spec.source_label, "Patient")
        self.assertEqual(spec.source_parameters, ("base_date",))
        self.assertEqual(spec.path_shape, "(p:Patient)--(s:TaskInstanceSet)")
        self.assertEqual(spec.row_fields, ("patient_id",))

    def test_registered_patient_training_history_query_declares_contract(self) -> None:
        spec = get_graph_query_spec("patient_training_task_history")

        self.assertEqual(spec.category, GraphQueryCategory.PATIENT_TRAINING_HISTORY)
        self.assertEqual(spec.source_label, "Patient")
        self.assertEqual(spec.source_parameters, ("patient_id",))
        self.assertEqual(
            spec.path_shape,
            "(p:Patient)--(s:TaskInstanceSet)--(i:TaskInstance)--(g:Game)",
        )
        self.assertEqual(spec.row_fields, ("trainingDate", "s", "i", "g"))

    def test_registered_patient_game_collection_queries_declare_contracts(self) -> None:
        distinct_spec = get_graph_query_spec("patient_distinct_games_by_start_date")
        game_rows_spec = get_graph_query_spec("patient_games_by_date_range")

        self.assertEqual(
            distinct_spec.category, GraphQueryCategory.PATIENT_GAME_COLLECTION
        )
        self.assertEqual(distinct_spec.source_parameters, ("patient_id", "start_date"))
        self.assertEqual(distinct_spec.row_fields, ("g",))
        self.assertEqual(distinct_spec.query, PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY)

        self.assertEqual(
            game_rows_spec.category, GraphQueryCategory.PATIENT_GAME_COLLECTION
        )
        self.assertEqual(
            game_rows_spec.source_parameters,
            ("patient_id", "start_date", "end_date"),
        )
        self.assertEqual(game_rows_spec.row_fields, ("g",))
        self.assertEqual(game_rows_spec.query, PATIENT_GAMES_BY_DATE_RANGE_QUERY)

    def test_registered_patient_comparison_query_declares_contract(self) -> None:
        spec = get_graph_query_spec("patient_game_set_comparison_by_date_range")

        self.assertEqual(spec.category, GraphQueryCategory.PATIENT_SET_COMPARISON)
        self.assertEqual(
            spec.source_parameters,
            ("primary_patient_id", "comparison_patient_id", "start_date", "end_date"),
        )
        self.assertEqual(spec.row_fields, ("games1", "games2"))

    def test_list_graph_query_specs_can_filter_patient_categories(self) -> None:
        self.assertEqual(
            len(list_graph_query_specs(category=GraphQueryCategory.PATIENT_IDENTITY)),
            2,
        )
        self.assertEqual(
            len(
                list_graph_query_specs(
                    category=GraphQueryCategory.PATIENT_TRAINING_HISTORY
                )
            ),
            4,
        )
        self.assertEqual(
            len(list_graph_query_specs(category=GraphQueryCategory.PATIENT_GAME_COLLECTION)),
            7,
        )
        self.assertEqual(
            len(
                list_graph_query_specs(
                    category=GraphQueryCategory.PATIENT_ENTITY_COLLECTION
                )
            ),
            12,
        )
        self.assertEqual(
            len(list_graph_query_specs(category=GraphQueryCategory.PATIENT_SET_COMPARISON)),
            12,
        )
        self.assertEqual(
            len(
                list_graph_query_specs(
                    category=GraphQueryCategory.PATIENT_SCORE_COMPARISON
                )
            ),
            1,
        )

    def test_registered_specs_are_keyed_by_name(self) -> None:
        for name, spec in GRAPH_QUERY_SPECS.items():
            with self.subTest(name=name):
                self.assertEqual(name, spec.name)

    def test_registered_specs_have_query_contracts(self) -> None:
        for spec in GRAPH_QUERY_SPECS.values():
            with self.subTest(name=spec.name):
                self.assertTrue(spec.query)
                self.assertTrue(spec.path_shape)
                self.assertTrue(spec.row_fields)

    def test_get_graph_query_spec_rejects_unknown_name(self) -> None:
        with self.assertRaisesRegex(ValueError, "Supported graph queries"):
            get_graph_query_spec("missing_query")


if __name__ == "__main__":
    unittest.main()
