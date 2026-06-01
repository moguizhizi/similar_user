"""Tests for internal algorithm request/result CSV lookups."""

from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from similar_user.data_access.algorithm_request_results import (
    get_algorithm_request_result,
    load_algorithm_request_results,
    normalize_algorithm_request_education,
    normalize_algorithm_request_gender,
    normalize_patient_id,
)


class AlgorithmRequestResultsTest(unittest.TestCase):
    def test_normalize_patient_id_removes_old_suffix(self) -> None:
        self.assertEqual(normalize_patient_id("20123188_old"), "20123188")
        self.assertEqual(normalize_patient_id("20123188"), "20123188")
        self.assertEqual(normalize_patient_id(20123188), "20123188")

    def test_normalize_algorithm_request_demographics(self) -> None:
        self.assertEqual(normalize_algorithm_request_gender(1), "男")
        self.assertEqual(normalize_algorithm_request_gender(2), "女")
        self.assertEqual(normalize_algorithm_request_education(12), "未上过学")
        self.assertEqual(normalize_algorithm_request_education(15), "高中")
        self.assertEqual(normalize_algorithm_request_education(16), "大专")
        self.assertEqual(normalize_algorithm_request_education(22), "大专")
        self.assertEqual(normalize_algorithm_request_education("硕士"), "研究生")

    def test_get_by_patient_id_returns_matching_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "request_results.csv"
            self._write_csv(
                csv_path,
                [
                    {
                        "ai_params": {
                            "user_id": "20123188_old",
                            "age": 84,
                        },
                        "recommen_train": {
                            "id": [306, 686],
                        },
                    }
                ],
            )

            index = load_algorithm_request_results(csv_path)

            result = index.get_by_patient_id("20123188")

            self.assertEqual(result["patient_id"], "20123188")
            self.assertEqual(result["matched_count"], 1)
            self.assertEqual(result["records"][0]["row_number"], 2)
            self.assertEqual(result["records"][0]["raw_user_id"], "20123188_old")
            self.assertEqual(result["records"][0]["ai_params"]["age"], 84)
            self.assertEqual(result["records"][0]["recommen_train"]["id"], [306, 686])

    def test_get_by_patient_id_accepts_old_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "request_results.csv"
            self._write_csv(
                csv_path,
                [
                    {
                        "ai_params": {
                            "user_id": "20123188_old",
                        },
                        "recommen_train": {
                            "id": [306],
                        },
                    }
                ],
            )

            result = get_algorithm_request_result("20123188_old", csv_path)

            self.assertEqual(result["patient_id"], "20123188")
            self.assertEqual(result["matched_count"], 1)

    def test_duplicate_patient_id_returns_all_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "request_results.csv"
            self._write_csv(
                csv_path,
                [
                    {
                        "ai_params": {
                            "user_id": "30021301_old",
                            "group": "A",
                        },
                        "recommen_train": {
                            "id": [300],
                        },
                    },
                    {
                        "ai_params": {
                            "user_id": "30021301_old",
                            "group": "B",
                        },
                        "recommen_train": {
                            "id": [301],
                        },
                    },
                ],
            )

            result = get_algorithm_request_result("30021301", csv_path)

            self.assertEqual(result["matched_count"], 2)
            self.assertEqual(
                [record["row_number"] for record in result["records"]],
                [2, 3],
            )
            self.assertEqual(
                [record["ai_params"]["group"] for record in result["records"]],
                ["A", "B"],
            )

    def test_missing_patient_id_returns_empty_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            csv_path = Path(temp_dir) / "request_results.csv"
            self._write_csv(
                csv_path,
                [
                    {
                        "ai_params": {
                            "user_id": "20123188_old",
                        },
                        "recommen_train": {
                            "id": [306],
                        },
                    }
                ],
            )

            result = get_algorithm_request_result("missing", csv_path)

            self.assertEqual(
                result,
                {
                    "patient_id": "missing",
                    "matched_count": 0,
                    "records": [],
                },
            )

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
