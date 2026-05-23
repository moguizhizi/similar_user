"""Tests for training date export script."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import export_training_dates


class ExportTrainingDatesTest(unittest.TestCase):
    def test_write_training_dates_writes_one_date_per_line(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "training_dates.txt"

            written_path = export_training_dates.write_training_dates(
                ["2024-02-23", "2024-02-22"],
                output_path,
            )

            self.assertEqual(written_path, output_path)
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "2024-02-23\n2024-02-22\n",
            )

    @patch("scripts.export_training_dates.Neo4jClient")
    def test_export_training_dates_fetches_and_writes_dates(
        self,
        mock_client_class: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "training_dates.txt"
            mock_client = Mock()
            mock_client.run_query.return_value = [
                {"training_date": "2024-02-23"},
                {"training_date": "2024-02-22"},
                {"training_date": ""},
                {"training_date": None},
            ]
            mock_client_class.from_config.return_value.__enter__.return_value = (
                mock_client
            )

            result = export_training_dates.export_training_dates(
                config_path="config/settings.yaml",
                output_path=output_path,
            )

            self.assertEqual(
                result,
                {
                    "training_date_count": 2,
                    "output_path": str(output_path),
                },
            )
            self.assertEqual(
                output_path.read_text(encoding="utf-8"),
                "2024-02-23\n2024-02-22\n",
            )
            mock_client_class.from_config.assert_called_once_with(
                "config/settings.yaml"
            )
            mock_client.run_query.assert_called_once_with(
                export_training_dates.TRAINING_DATES_DESC_QUERY,
                parameters={},
            )


if __name__ == "__main__":
    unittest.main()
