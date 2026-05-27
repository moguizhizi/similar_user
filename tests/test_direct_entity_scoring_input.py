"""Tests for direct entity scoring input resolution."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.similar_user.services.direct_entity_scoring_input import (
    DirectEntityScoringInput,
    load_profile_from_kg,
    resolve_scoring_input,
)


class DirectEntityScoringInputTest(unittest.TestCase):
    def test_resolve_skips_when_patient_exists_and_disabled(self) -> None:
        repository = Mock()
        repository.patient_exists.return_value = True

        result = resolve_scoring_input(
            kg_repository=repository,
            patient_id=" 20123188 ",
            use_when_patient_exists=False,
        )

        self.assertFalse(result.should_score)
        self.assertEqual(result.reason, "patient_exists_direct_entity_path_disabled")
        self.assertIsNone(result.scoring_input)
        repository.patient_exists.assert_called_once_with("20123188")
        repository.get_patient_direct_entity_scoring_profile.assert_not_called()

    def test_resolve_loads_kg_profile_when_patient_exists_and_enabled(self) -> None:
        repository = Mock()
        repository.patient_exists.return_value = True
        repository.get_patient_direct_entity_scoring_profile.return_value = [
            {
                "patient_id": "20123188",
                "effective_date": "2026-05-20",
                "gender": "男",
                "education": "本科",
                "profile_age": 66,
                "age_at_base_date": 66,
                "disease_ids": ["AU_DIS_0029", "AU_DIS_0029"],
                "symptom_ids": ["AU_SYM_0001"],
                "unknown_ids": [],
            }
        ]

        result = resolve_scoring_input(
            kg_repository=repository,
            patient_id="20123188",
            base_date="2026-05-26",
            use_when_patient_exists=True,
        )

        self.assertTrue(result.should_score)
        self.assertEqual(result.reason, "kg_profile")
        self.assertEqual(
            result.scoring_input,
            DirectEntityScoringInput(
                patient_id="20123188",
                age=66,
                education="本科",
                gender="男",
                disease_ids=("AU_DIS_0029",),
                symptom_ids=("AU_SYM_0001",),
                unknown_ids=(),
                source="kg_profile",
                effective_date="2026-05-20",
                profile_age=66,
            ),
        )

    def test_resolve_requires_manual_input_when_patient_missing(self) -> None:
        repository = Mock()
        repository.patient_exists.return_value = False

        result = resolve_scoring_input(
            kg_repository=repository,
            patient_id="20123188",
            age="66",
            education=" 本科 ",
            gender=" 男 ",
            disease_ids=["AU_DIS_0029", ""],
        )

        self.assertTrue(result.should_score)
        self.assertEqual(result.reason, "manual_input_patient_not_in_kg")
        assert result.scoring_input is not None
        self.assertEqual(result.scoring_input.patient_id, "20123188")
        self.assertEqual(result.scoring_input.age, 66)
        self.assertEqual(result.scoring_input.education, "本科")
        self.assertEqual(result.scoring_input.gender, "男")
        self.assertEqual(result.scoring_input.disease_ids, ("AU_DIS_0029",))
        self.assertEqual(result.scoring_input.source, "manual_cli_patient_not_in_kg")

    def test_resolve_explains_missing_manual_input_when_patient_missing(self) -> None:
        repository = Mock()
        repository.patient_exists.return_value = False

        with self.assertRaisesRegex(ValueError, "does not exist in KG"):
            resolve_scoring_input(
                kg_repository=repository,
                patient_id="201231885555",
            )

    def test_resolve_requires_manual_input_without_patient_id(self) -> None:
        repository = Mock()

        result = resolve_scoring_input(
            kg_repository=repository,
            age=70,
            education="大专",
            gender="女",
            symptom_ids=["AU_SYM_0001"],
        )

        self.assertTrue(result.should_score)
        self.assertEqual(result.reason, "manual_input_without_patient_id")
        assert result.scoring_input is not None
        self.assertIsNone(result.scoring_input.patient_id)
        self.assertEqual(result.scoring_input.symptom_ids, ("AU_SYM_0001",))
        repository.patient_exists.assert_not_called()

    def test_resolve_can_force_manual_input_with_patient_id(self) -> None:
        repository = Mock()

        result = resolve_scoring_input(
            kg_repository=repository,
            patient_id="201231885555",
            age=66,
            education="本科",
            gender="男",
            disease_ids=["AU_DIS_0029"],
            force_manual_input=True,
        )

        self.assertTrue(result.should_score)
        self.assertEqual(result.reason, "manual_input_forced")
        assert result.scoring_input is not None
        self.assertEqual(result.scoring_input.patient_id, "201231885555")
        self.assertEqual(result.scoring_input.source, "manual_cli_forced")
        repository.patient_exists.assert_not_called()

    def test_resolve_rejects_manual_input_without_entities(self) -> None:
        repository = Mock()

        with self.assertRaisesRegex(ValueError, "At least one"):
            resolve_scoring_input(
                kg_repository=repository,
                age=70,
                education="大专",
                gender="女",
            )

    def test_load_profile_from_kg_returns_none_without_rows(self) -> None:
        repository = Mock()
        repository.get_patient_direct_entity_scoring_profile.return_value = []

        result = load_profile_from_kg(
            kg_repository=repository,
            patient_id="20123188",
            base_date="2026-05-26",
        )

        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
