"""Tests for source patient selection rules."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.similar_user.services.source_patient_selection import (
    SECONDARY_ABILITY_ANY_RULE,
    SourcePatientSelectionService,
    get_source_patient_selection_rule,
)


class SourcePatientSelectionTest(unittest.TestCase):
    def test_secondary_ability_rule_declares_criteria(self) -> None:
        rule = get_source_patient_selection_rule(SECONDARY_ABILITY_ANY_RULE)

        self.assertEqual(rule.name, "secondary_ability_any")
        self.assertEqual(rule.criteria["requires_training_date"], True)
        self.assertEqual(rule.criteria["requires_game"], True)
        self.assertEqual(rule.criteria["secondary_ability_rule"], "any_non_null")

    def test_list_source_patient_ids_uses_registered_rule(self) -> None:
        mock_user_service = Mock()
        mock_user_service.get_source_patient_ids_with_secondary_ability_scores.return_value = [
            "40",
            "41",
        ]
        service = SourcePatientSelectionService(user_service=mock_user_service)

        result = service.list_source_patient_ids(SECONDARY_ABILITY_ANY_RULE)

        self.assertEqual(result, ["40", "41"])
        mock_user_service.get_source_patient_ids_with_secondary_ability_scores.assert_called_once_with()

    def test_build_source_patient_payload_includes_rule_metadata(self) -> None:
        mock_user_service = Mock()
        mock_user_service.get_source_patient_ids_with_secondary_ability_scores.return_value = [
            "40",
            "41",
        ]
        service = SourcePatientSelectionService(user_service=mock_user_service)

        result = service.build_source_patient_payload(SECONDARY_ABILITY_ANY_RULE)

        self.assertEqual(result["rule"], "secondary_ability_any")
        self.assertEqual(result["count"], 2)
        self.assertEqual(result["patient_ids"], ["40", "41"])
        self.assertEqual(result["criteria"]["secondary_ability_rule"], "any_non_null")

    def test_get_source_patient_selection_rule_rejects_unknown_rule(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported source patient"):
            get_source_patient_selection_rule("missing")


if __name__ == "__main__":
    unittest.main()
