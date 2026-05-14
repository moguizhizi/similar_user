"""Tests for the source patient listing script."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from scripts.list_source_patients import list_source_patients


class ListSourcePatientsScriptTest(unittest.TestCase):
    def test_list_source_patients_writes_payload_to_json(self) -> None:
        expected_payload = {
            "rule": "secondary_ability_any",
            "description": "训练记录中任意二级脑能力字段非空",
            "criteria": {"secondary_ability_rule": "any_non_null"},
            "count": 2,
            "patient_ids": ["40", "41"],
        }
        mock_client = Mock()
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_client)
        mock_context.__exit__ = Mock(return_value=None)

        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "source_patients.json"
            with patch(
                "scripts.list_source_patients.Neo4jClient.from_config",
                return_value=mock_context,
            ) as mock_from_config, patch(
                "scripts.list_source_patients.SourcePatientSelectionService"
            ) as mock_service_cls:
                mock_service_cls.return_value.build_source_patient_payload.return_value = (
                    expected_payload
                )

                result = list_source_patients(
                    rule="secondary_ability_any",
                    output_path=output_path,
                    config_path="config/test.yaml",
                )
                written_payload = json.loads(output_path.read_text(encoding="utf-8"))

        self.assertEqual(result, expected_payload)
        self.assertEqual(written_payload, expected_payload)
        mock_from_config.assert_called_once_with("config/test.yaml")
        mock_service_cls.return_value.build_source_patient_payload.assert_called_once_with(
            "secondary_ability_any"
        )

    def test_list_source_patients_uses_rule_based_default_output_path(self) -> None:
        mock_client = Mock()
        mock_context = MagicMock()
        mock_context.__enter__ = Mock(return_value=mock_client)
        mock_context.__exit__ = Mock(return_value=None)

        with tempfile.TemporaryDirectory() as tmpdir, patch(
            "scripts.list_source_patients.DEFAULT_OUTPUT_DIR",
            Path(tmpdir),
        ), patch(
            "scripts.list_source_patients.Neo4jClient.from_config",
            return_value=mock_context,
        ), patch(
            "scripts.list_source_patients.SourcePatientSelectionService"
        ) as mock_service_cls:
            mock_service_cls.return_value.build_source_patient_payload.return_value = {
                "rule": "secondary_ability_any",
                "description": "",
                "criteria": {},
                "count": 0,
                "patient_ids": [],
            }

            list_source_patients(rule="secondary_ability_any")

            self.assertTrue((Path(tmpdir) / "secondary_ability_any.json").exists())


if __name__ == "__main__":
    unittest.main()
