"""Tests for path pattern query registration."""

from __future__ import annotations

import unittest

from src.similar_user.data_access.cypher_queries import (
    DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
    SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
    UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
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
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY,
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY,
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
from src.similar_user.data_access.pattern_registry import (
    PATH_PATTERN_SPECS,
    PatternQueryMode,
    PatternQuerySet,
    QueryDateVariant,
    QueryDateWindow,
    available_path_pattern_aliases,
    get_path_pattern_spec,
    resolve_path_pattern_alias,
    resolve_path_pattern,
)
from src.similar_user.domain.graph_schema import PathPattern
from src.similar_user.domain.path_models import (
    DiseaseTasksetPatientPath,
    PatientTasksetDiseaseTasksetPatientPath,
    PatientTasksetSymptomTasksetPatientPath,
    PatientTasksetTaskGameTaskTasksetPatientPath,
    PatientTasksetUnknownTasksetPatientPath,
    SymptomTasksetPatientPath,
    UnknownTasksetPatientPath,
)


class PathPatternRegistryTest(unittest.TestCase):
    def test_registered_task_game_pattern_declares_contract(self) -> None:
        spec = get_path_pattern_spec(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT
        )

        self.assertEqual(
            spec.pattern,
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        )
        self.assertEqual(spec.row_fields, ("p", "s1", "i1", "g", "i2", "s2", "p2"))
        self.assertEqual(spec.group_field, "g")
        self.assertIs(spec.path_model, PatientTasksetTaskGameTaskTasksetPatientPath)
        date_window = spec.queries.family("date_window")
        training_order = spec.queries.family("training_order")
        self.assertEqual(
            date_window.randomized_path.base,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_start_date,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_end_date,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_date_range,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.base,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_start_date,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_end_date,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_date_range,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.base,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_start_date,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_end_date,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_date_range,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )
        self.assertNotEqual(
            training_order.randomized_path.by_start_date,
            training_order.randomized_path.base,
        )
        self.assertNotEqual(
            training_order.randomized_path.by_end_date,
            training_order.randomized_path.base,
        )
        self.assertNotEqual(
            training_order.randomized_path.by_date_range,
            training_order.randomized_path.base,
        )
        self.assertEqual(
            training_order.statistics.base,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_start_date,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_end_date,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_date_range,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
        )

    def test_query_family_keeps_randomized_path_and_statistics_together(self) -> None:
        spec = get_path_pattern_spec(
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT
        )

        self.assertEqual(
            spec.queries.family("date_window").randomized_path.by_date_range,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            spec.queries.family("date_window").statistics.by_date_range,
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
        )

    def test_registered_disease_pattern_declares_contract(self) -> None:
        spec = get_path_pattern_spec(PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT)

        self.assertEqual(spec.pattern, PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT)
        self.assertEqual(spec.row_fields, ("p", "s1", "dis", "s2", "p2"))
        self.assertEqual(spec.group_field, "dis")
        self.assertIs(spec.path_model, PatientTasksetDiseaseTasksetPatientPath)
        date_window = spec.queries.family("date_window")
        training_order = spec.queries.family("training_order")
        self.assertEqual(
            date_window.randomized_path.base,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_start_date,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_end_date,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_date_range,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.base,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_start_date,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_end_date,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_date_range,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.base,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_start_date,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_end_date,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_date_range,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.base,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_start_date,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_end_date,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_date_range,
            PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
        )

    def test_registered_symptom_pattern_declares_contract(self) -> None:
        spec = get_path_pattern_spec(PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT)

        self.assertEqual(spec.pattern, PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT)
        self.assertEqual(spec.row_fields, ("p", "s1", "sym", "s2", "p2"))
        self.assertEqual(spec.group_field, "sym")
        self.assertIs(spec.path_model, PatientTasksetSymptomTasksetPatientPath)
        date_window = spec.queries.family("date_window")
        training_order = spec.queries.family("training_order")
        self.assertEqual(
            date_window.randomized_path.base,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_start_date,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_end_date,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_date_range,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.base,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_start_date,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_end_date,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_date_range,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.base,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_start_date,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_end_date,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_date_range,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.base,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_start_date,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_end_date,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_date_range,
            PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
        )

    def test_registered_unknown_pattern_declares_contract(self) -> None:
        spec = get_path_pattern_spec(PathPattern.PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT)

        self.assertEqual(spec.pattern, PathPattern.PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT)
        self.assertEqual(spec.row_fields, ("p", "s1", "un", "s2", "p2"))
        self.assertEqual(spec.group_field, "un")
        self.assertIs(spec.path_model, PatientTasksetUnknownTasksetPatientPath)
        date_window = spec.queries.family("date_window")
        training_order = spec.queries.family("training_order")
        self.assertEqual(
            date_window.randomized_path.base,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_start_date,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_end_date,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            date_window.randomized_path.by_date_range,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.base,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_start_date,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_end_date,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            date_window.statistics.by_date_range,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.base,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_start_date,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_end_date,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            training_order.randomized_path.by_date_range,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.base,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_start_date,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_end_date,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            training_order.statistics.by_date_range,
            PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY,
        )

    def test_registered_direct_disease_patient_pattern_declares_contract(self) -> None:
        spec = get_path_pattern_spec(PathPattern.DISEASE_TASKSET_PATIENT)

        self.assertEqual(spec.pattern, PathPattern.DISEASE_TASKSET_PATIENT)
        self.assertEqual(spec.description, "疾病-任务集-患者")
        self.assertEqual(spec.path_shape, "(d:Disease)--(s:TaskInstanceSet)--(p:Patient)")
        self.assertEqual(spec.row_fields, ("d", "s", "p"))
        self.assertEqual(spec.group_field, "p")
        self.assertIs(spec.path_model, DiseaseTasksetPatientPath)
        self.assertEqual(spec.query_mode, PatternQueryMode.DIRECT_PATH)
        self.assertEqual(spec.source_parameter, "disease_id")
        self.assertEqual(spec.queries.families, {})
        self.assertIsNotNone(spec.direct_queries)
        assert spec.direct_queries is not None
        self.assertEqual(
            spec.direct_queries.randomized_path.base,
            DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            spec.direct_queries.randomized_path.by_start_date,
            DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            spec.direct_queries.randomized_path.by_end_date,
            DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            spec.direct_queries.randomized_path.by_date_range,
            DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )

        with self.assertRaisesRegex(ValueError, "Supported query families: none"):
            spec.queries.family("date_window")

    def test_registered_direct_symptom_patient_pattern_declares_contract(self) -> None:
        spec = get_path_pattern_spec(PathPattern.SYMPTOM_TASKSET_PATIENT)

        self.assertEqual(spec.pattern, PathPattern.SYMPTOM_TASKSET_PATIENT)
        self.assertEqual(spec.description, "症状-任务集-患者")
        self.assertEqual(spec.path_shape, "(sym:Symptom)--(s:TaskInstanceSet)--(p:Patient)")
        self.assertEqual(spec.row_fields, ("sym", "s", "p"))
        self.assertEqual(spec.group_field, "p")
        self.assertIs(spec.path_model, SymptomTasksetPatientPath)
        self.assertEqual(spec.query_mode, PatternQueryMode.DIRECT_PATH)
        self.assertEqual(spec.source_parameter, "symptom_id")
        self.assertEqual(spec.queries.families, {})
        self.assertIsNotNone(spec.direct_queries)
        assert spec.direct_queries is not None
        self.assertEqual(
            spec.direct_queries.randomized_path.base,
            SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            spec.direct_queries.randomized_path.by_start_date,
            SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            spec.direct_queries.randomized_path.by_end_date,
            SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            spec.direct_queries.randomized_path.by_date_range,
            SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )

        with self.assertRaisesRegex(ValueError, "Supported query families: none"):
            spec.queries.family("date_window")

    def test_registered_direct_unknown_patient_pattern_declares_contract(self) -> None:
        spec = get_path_pattern_spec(PathPattern.UNKNOWN_TASKSET_PATIENT)

        self.assertEqual(spec.pattern, PathPattern.UNKNOWN_TASKSET_PATIENT)
        self.assertEqual(spec.description, "未知-任务集-患者")
        self.assertEqual(spec.path_shape, "(un:Unknown)--(s:TaskInstanceSet)--(p:Patient)")
        self.assertEqual(spec.row_fields, ("un", "s", "p"))
        self.assertEqual(spec.group_field, "p")
        self.assertIs(spec.path_model, UnknownTasksetPatientPath)
        self.assertEqual(spec.query_mode, PatternQueryMode.DIRECT_PATH)
        self.assertEqual(spec.source_parameter, "unknown_id")
        self.assertEqual(spec.queries.families, {})
        self.assertIsNotNone(spec.direct_queries)
        assert spec.direct_queries is not None
        self.assertEqual(
            spec.direct_queries.randomized_path.base,
            UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            spec.direct_queries.randomized_path.by_start_date,
            UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            spec.direct_queries.randomized_path.by_end_date,
            UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            spec.direct_queries.randomized_path.by_date_range,
            UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )

        with self.assertRaisesRegex(ValueError, "Supported query families: none"):
            spec.queries.family("date_window")

    def test_query_date_window_selects_matching_query_variant(self) -> None:
        variants = get_path_pattern_spec(
            "patient_game_patient"
        ).queries.family("date_window").randomized_path

        self.assertEqual(QueryDateWindow().variant, QueryDateVariant.BASE)
        self.assertEqual(
            variants.select(QueryDateWindow()),
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY,
        )
        self.assertEqual(
            variants.select(QueryDateWindow(start_date="2022-01-01")),
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY,
        )
        self.assertEqual(
            variants.select(QueryDateWindow(end_date="2022-01-13")),
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY,
        )
        self.assertEqual(
            variants.select(
                QueryDateWindow(start_date="2022-01-01", end_date="2022-01-13")
            ),
            PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY,
        )

    def test_query_date_window_returns_only_required_date_parameters(self) -> None:
        self.assertEqual(QueryDateWindow().parameters(), {})
        self.assertEqual(
            QueryDateWindow(start_date="2022-01-01").parameters(),
            {"start_date": "2022-01-01"},
        )
        self.assertEqual(
            QueryDateWindow(end_date="2022-01-13").parameters(),
            {"end_date": "2022-01-13"},
        )
        self.assertEqual(
            QueryDateWindow(
                start_date="2022-01-01",
                end_date="2022-01-13",
            ).parameters(),
            {"start_date": "2022-01-01", "end_date": "2022-01-13"},
        )

    def test_query_family_rejects_unregistered_family(self) -> None:
        spec = get_path_pattern_spec("patient_game_patient")

        with self.assertRaisesRegex(ValueError, "does not support query family"):
            spec.queries.family("unsupported_family")

    def test_query_family_rejects_family_not_registered_for_pattern(self) -> None:
        spec = get_path_pattern_spec("patient_game_patient")
        query_set = PatternQuerySet(
            families={"date_window": spec.queries.family("date_window")}
        )

        with self.assertRaisesRegex(ValueError, "does not support query family"):
            query_set.family("training_order")

    def test_registered_specs_are_keyed_by_their_pattern(self) -> None:
        for pattern, spec in PATH_PATTERN_SPECS.items():
            with self.subTest(pattern=pattern):
                self.assertEqual(pattern, spec.pattern)

    def test_patient_game_patient_alias_resolves_to_registered_pattern(self) -> None:
        self.assertEqual(
            resolve_path_pattern("patient_game_patient"),
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        )
        self.assertIs(
            get_path_pattern_spec("patient_game_patient"),
            get_path_pattern_spec(
                PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT
            ),
        )

    def test_patient_disease_patient_alias_resolves_to_registered_pattern(self) -> None:
        self.assertEqual(
            resolve_path_pattern("patient_disease_patient"),
            PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT,
        )
        self.assertIs(
            get_path_pattern_spec("patient_disease_patient"),
            get_path_pattern_spec(PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT),
        )

    def test_patient_symptom_patient_alias_resolves_to_registered_pattern(self) -> None:
        self.assertEqual(
            resolve_path_pattern("patient_symptom_patient"),
            PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT,
        )
        self.assertIs(
            get_path_pattern_spec("patient_symptom_patient"),
            get_path_pattern_spec(PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT),
        )

    def test_patient_unknown_patient_alias_resolves_to_registered_pattern(self) -> None:
        self.assertEqual(
            resolve_path_pattern("patient_unknown_patient"),
            PathPattern.PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT,
        )
        self.assertIs(
            get_path_pattern_spec("patient_unknown_patient"),
            get_path_pattern_spec(PathPattern.PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT),
        )

    def test_disease_patient_alias_resolves_to_registered_pattern(self) -> None:
        self.assertEqual(
            resolve_path_pattern("disease_patient"),
            PathPattern.DISEASE_TASKSET_PATIENT,
        )
        self.assertIs(
            get_path_pattern_spec("disease_patient"),
            get_path_pattern_spec(PathPattern.DISEASE_TASKSET_PATIENT),
        )

    def test_symptom_patient_alias_resolves_to_registered_pattern(self) -> None:
        self.assertEqual(
            resolve_path_pattern("symptom_patient"),
            PathPattern.SYMPTOM_TASKSET_PATIENT,
        )
        self.assertIs(
            get_path_pattern_spec("symptom_patient"),
            get_path_pattern_spec(PathPattern.SYMPTOM_TASKSET_PATIENT),
        )

    def test_unknown_patient_alias_resolves_to_registered_pattern(self) -> None:
        self.assertEqual(
            resolve_path_pattern("unknown_patient"),
            PathPattern.UNKNOWN_TASKSET_PATIENT,
        )
        self.assertIs(
            get_path_pattern_spec("unknown_patient"),
            get_path_pattern_spec(PathPattern.UNKNOWN_TASKSET_PATIENT),
        )

    def test_available_path_pattern_aliases_returns_public_aliases_only(self) -> None:
        self.assertEqual(
            available_path_pattern_aliases(),
            (
                "disease_patient",
                "patient_disease_patient",
                "patient_game_patient",
                "patient_symptom_patient",
                "patient_unknown_patient",
                "symptom_patient",
                "unknown_patient",
            ),
        )

    def test_path_pattern_alias_rejects_unregistered_alias(self) -> None:
        with self.assertRaisesRegex(ValueError, "Supported aliases"):
            resolve_path_pattern_alias("patient_dis_patient")

    def test_get_path_pattern_spec_rejects_unsupported_pattern_alias(self) -> None:
        with self.assertRaisesRegex(ValueError, "Supported aliases"):
            get_path_pattern_spec("UNREGISTERED_PATTERN")


if __name__ == "__main__":
    unittest.main()
