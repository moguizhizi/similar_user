"""Tests for active patient ID export script."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import export_patient_ids_with_training_on_date


class ExportPatientIdsWithTrainingOnDateTest(unittest.TestCase):
    def test_build_patient_ids_output_path_uses_base_date_subdir(self) -> None:
        output_path = (
            export_patient_ids_with_training_on_date.build_patient_ids_output_path(
                base_date="2023-10-15",
                output_dir="data/patient_ids",
            )
        )

        self.assertEqual(
            output_path,
            Path("data/patient_ids/base_2023-10-15/patients_active_2023-10-15.txt"),
        )

    def test_write_patient_ids_writes_one_id_per_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "base_2023-10-15" / "patients.txt"

            written_path = export_patient_ids_with_training_on_date.write_patient_ids(
                ["20102686", "20103001"],
                output_path,
            )

            self.assertEqual(written_path, output_path)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "20102686\n20103001\n",
            )

    @patch("scripts.export_patient_ids_with_training_on_date.Neo4jClient")
    @patch("scripts.export_patient_ids_with_training_on_date.KgRepository")
    @patch("scripts.export_patient_ids_with_training_on_date.UserService")
    def test_export_patient_ids_fetches_and_writes_active_patients(
        self,
        mock_user_service_class: Mock,
        mock_repository_class: Mock,
        mock_client_class: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_client = Mock()
            mock_client_class.from_config.return_value.__enter__.return_value = (
                mock_client
            )
            mock_user_service = Mock()
            mock_user_service.get_patient_ids_with_training_on_date.return_value = [
                "20102686",
                "20103001",
            ]
            mock_user_service_class.return_value = mock_user_service

            result = (
                export_patient_ids_with_training_on_date.export_patient_ids_with_training_on_date(
                    base_date="2023-10-15",
                    config_path="config/settings.yaml",
                    output_dir=temp_dir,
                )
            )

            output_path = (
                Path(temp_dir)
                / "base_2023-10-15"
                / "patients_active_2023-10-15.txt"
            )
            self.assertEqual(
                result,
                {
                    "base_date": "2023-10-15",
                    "limit": 100,
                    "patient_count": 2,
                    "output_path": str(output_path),
                },
            )
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "20102686\n20103001\n",
            )
            mock_client_class.from_config.assert_called_once_with("config/settings.yaml")
            mock_repository_class.assert_called_once_with(
                client=mock_client,
                config_path=Path("config/settings.yaml"),
            )
            mock_user_service.get_patient_ids_with_training_on_date.assert_called_once_with(
                "2023-10-15",
                100,
            )

    @patch("scripts.export_patient_ids_with_training_on_date.Neo4jClient")
    @patch("scripts.export_patient_ids_with_training_on_date.KgRepository")
    @patch("scripts.export_patient_ids_with_training_on_date.UserService")
    def test_export_patient_ids_limits_query_and_output_path(
        self,
        mock_user_service_class: Mock,
        mock_repository_class: Mock,
        mock_client_class: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            mock_client = Mock()
            mock_client_class.from_config.return_value.__enter__.return_value = (
                mock_client
            )
            mock_user_service = Mock()
            mock_user_service.get_patient_ids_with_training_on_date.return_value = [
                "20102686",
            ]
            mock_user_service_class.return_value = mock_user_service

            result = (
                export_patient_ids_with_training_on_date.export_patient_ids_with_training_on_date(
                    base_date="2023-10-15",
                    config_path="config/settings.yaml",
                    output_dir=temp_dir,
                    limit=100,
                )
            )

            output_path = (
                Path(temp_dir)
                / "base_2023-10-15"
                / "patients_active_2023-10-15.txt"
            )
            self.assertEqual(
                result,
                {
                    "base_date": "2023-10-15",
                    "limit": 100,
                    "patient_count": 1,
                    "output_path": str(output_path),
                },
            )
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "20102686\n",
            )
            mock_user_service.get_patient_ids_with_training_on_date.assert_called_once_with(
                "2023-10-15",
                100,
            )


if __name__ == "__main__":
    unittest.main()
