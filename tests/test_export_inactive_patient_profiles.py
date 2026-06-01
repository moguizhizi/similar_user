"""Tests for inactive non-KG patient profile export."""

from __future__ import annotations

import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts.export_inactive_patient_profiles import (
    build_profile_record,
    export_inactive_patient_profiles,
    normalize_disease_names,
    normalize_education,
    normalize_education_from_sources,
    normalize_gender,
)


class ExportInactivePatientProfilesTest(unittest.TestCase):
    def test_build_profile_record_prefers_behavior_data_labels(self) -> None:
        record = {
            "row_number": 2,
            "raw_user_id": "31127868_old",
            "ai_params": {
                "age": 79,
                "sex": 1,
                "education": 17,
                "sicksName": ["轻度认知障碍（MCI）"],
                "behavior_data": {
                    "age": 80,
                    "gender": "男",
                    "edu": "本科",
                    "sicks": "轻度认知障碍（MCI）",
                    "dt": "2026-05-24",
                },
            },
        }

        profile = build_profile_record("31127868", record, "2026-05-25")

        self.assertEqual(profile["patient_id"], "31127868")
        self.assertEqual(profile["age"], 80)
        self.assertEqual(profile["gender"], "男")
        self.assertEqual(profile["education"], "本科")
        self.assertEqual(profile["disease_names"], ["轻度认知障碍（MCI）"])
        self.assertEqual(profile["source"]["raw_user_id"], "31127868_old")

    def test_normalizers_handle_algorithm_values(self) -> None:
        self.assertEqual(normalize_gender(1), "男")
        self.assertEqual(normalize_gender(2), "女")
        self.assertEqual(normalize_education(15), "高中")
        self.assertEqual(normalize_education(17), "本科")
        self.assertEqual(normalize_education(22), "大专")
        self.assertEqual(normalize_education_from_sources("未上过学", 12), "未上过学")
        self.assertEqual(
            normalize_disease_names("轻度认知障碍（MCI），失眠"),
            ["轻度认知障碍（MCI）", "失眠"],
        )

    def test_export_inactive_patient_profiles_writes_jsonl_and_summary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            ids_path = root / "patients.txt"
            csv_path = root / "request_results.csv"
            output_path = root / "profiles.jsonl"
            ids_path.write_text("31127868\nmissing\n", encoding="utf-8")
            self._write_csv(
                csv_path,
                [
                    {
                        "ai_params": {
                            "user_id": "31127868_old",
                            "age": 79,
                            "sex": 1,
                            "education": 17,
                            "sicksName": ["轻度认知障碍（MCI）"],
                        },
                        "recommen_train": {"id": [449]},
                    }
                ],
            )

            summary = export_inactive_patient_profiles(
                base_date="2026-05-25",
                patient_ids_path=ids_path,
                csv_path=csv_path,
                output_path=output_path,
            )

            records = [
                json.loads(line)
                for line in output_path.read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(summary["profile_count"], 1)
            self.assertEqual(summary["missing_patient_ids"], ["missing"])
            self.assertEqual(records[0]["patient_id"], "31127868")
            self.assertEqual(records[0]["disease_names"], ["轻度认知障碍（MCI）"])
            self.assertTrue(Path(summary["summary_output_path"]).exists())

    def _write_csv(self, path: Path, rows: list[dict[str, object]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as file:
            writer = csv.DictWriter(file, fieldnames=["ai_params", "recommen_train"])
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        "ai_params": repr(row["ai_params"]),
                        "recommen_train": repr(row["recommen_train"]),
                    }
                )


if __name__ == "__main__":
    unittest.main()
