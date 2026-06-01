"""Read algorithm request/result snapshots from internal validation CSV files."""

from __future__ import annotations

import ast
import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_ALGORITHM_REQUEST_RESULTS_PATH = Path(
    "/home/temp/dataset/20260525_Algorithm_Request_Results/"
    "20260525_Algorithm_Request_Results.csv"
)

ALGORITHM_REQUEST_GENDER_LABELS = {
    "1": "男",
    "1.0": "男",
    "男": "男",
    "男性": "男",
    "2": "女",
    "2.0": "女",
    "女": "女",
    "女性": "女",
}

ALGORITHM_REQUEST_EDUCATION_LABELS = {
    "12": "未上过学",
    "12.0": "未上过学",
    "13": "小学",
    "13.0": "小学",
    "14": "初中",
    "14.0": "初中",
    "15": "高中",
    "15.0": "高中",
    "16": "大专",
    "16.0": "大专",
    "17": "本科",
    "17.0": "本科",
    "18": "研究生",
    "18.0": "研究生",
    "19": "博士",
    "19.0": "博士",
    "20": "保密",
    "20.0": "保密",
    "21": "中专",
    "21.0": "中专",
    "22": "大专",
    "22.0": "大专",
    "小学": "小学",
    "初中": "初中",
    "高中": "高中",
    "中专": "中专",
    "大专": "大专",
    "专科": "大专",
    "本科": "本科",
    "研究生": "研究生",
    "硕士": "研究生",
    "博士": "博士",
    "未上过学": "未上过学",
    "保密": "保密",
}


@dataclass(frozen=True)
class AlgorithmRequestResultRecord:
    """A parsed row from an algorithm request/result CSV snapshot."""

    row_number: int
    patient_id: str
    raw_user_id: str
    ai_params: dict[str, Any]
    recommen_train: dict[str, Any]


class AlgorithmRequestResultIndex:
    """In-memory index for patient request/result snapshot lookup."""

    def __init__(self, records: list[AlgorithmRequestResultRecord]) -> None:
        self._records_by_patient_id: dict[str, list[AlgorithmRequestResultRecord]] = {}
        for record in records:
            self._records_by_patient_id.setdefault(record.patient_id, []).append(record)

    def get_by_patient_id(self, patient_id: str | int) -> dict[str, Any]:
        """Return all records matching a patient ID."""
        normalized_patient_id = normalize_patient_id(patient_id)
        records = self._records_by_patient_id.get(normalized_patient_id, [])
        return {
            "patient_id": normalized_patient_id,
            "matched_count": len(records),
            "records": [
                {
                    "row_number": record.row_number,
                    "patient_id": record.patient_id,
                    "raw_user_id": record.raw_user_id,
                    "ai_params": record.ai_params,
                    "recommen_train": record.recommen_train,
                }
                for record in records
            ],
        }


def normalize_patient_id(patient_id: str | int) -> str:
    """Normalize IDs so ``20123188`` and ``20123188_old`` match the same record."""
    normalized = str(patient_id).strip()
    if normalized.endswith("_old"):
        normalized = normalized[: -len("_old")]
    return normalized


def normalize_algorithm_request_gender(value: object) -> str:
    """Normalize algorithm request gender code or label into KG-facing text."""
    text = _normalize_optional_text(value)
    if text is None:
        raise ValueError("gender is required.")
    try:
        return ALGORITHM_REQUEST_GENDER_LABELS[text]
    except KeyError as exc:
        raise ValueError(f"unsupported gender value: {value}") from exc


def normalize_algorithm_request_education(value: object) -> str:
    """Normalize algorithm request education code or label into KG-facing text."""
    text = _normalize_optional_text(value)
    if text is None:
        raise ValueError("education is required.")
    try:
        return ALGORITHM_REQUEST_EDUCATION_LABELS[text]
    except KeyError as exc:
        raise ValueError(f"unsupported education value: {value}") from exc


def load_algorithm_request_results(
    csv_path: str | Path = DEFAULT_ALGORITHM_REQUEST_RESULTS_PATH,
) -> AlgorithmRequestResultIndex:
    """Load an algorithm request/result CSV snapshot into an in-memory index."""
    path = Path(csv_path)
    records: list[AlgorithmRequestResultRecord] = []
    with path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        required_columns = {"ai_params", "recommen_train"}
        missing_columns = required_columns - set(reader.fieldnames or [])
        if missing_columns:
            missing = ", ".join(sorted(missing_columns))
            raise ValueError(f"Missing required CSV columns: {missing}")

        for row_number, row in enumerate(reader, start=2):
            ai_params = _parse_mapping_cell(row["ai_params"], row_number, "ai_params")
            recommen_train = _parse_mapping_cell(
                row["recommen_train"],
                row_number,
                "recommen_train",
            )
            raw_user_id = ai_params.get("user_id")
            if raw_user_id is None:
                raise ValueError(f"Missing ai_params user_id at row {row_number}.")
            raw_user_id_text = str(raw_user_id).strip()
            if not raw_user_id_text:
                raise ValueError(f"Blank ai_params user_id at row {row_number}.")

            records.append(
                AlgorithmRequestResultRecord(
                    row_number=row_number,
                    patient_id=normalize_patient_id(raw_user_id_text),
                    raw_user_id=raw_user_id_text,
                    ai_params=ai_params,
                    recommen_train=recommen_train,
                )
            )

    return AlgorithmRequestResultIndex(records)


def get_algorithm_request_result(
    patient_id: str | int,
    csv_path: str | Path = DEFAULT_ALGORITHM_REQUEST_RESULTS_PATH,
) -> dict[str, Any]:
    """Load the snapshot CSV and return records for a patient ID."""
    return load_algorithm_request_results(csv_path).get_by_patient_id(patient_id)


def _parse_mapping_cell(value: str, row_number: int, column_name: str) -> dict[str, Any]:
    parsed = _literal_eval_cell(value, row_number, column_name)
    if isinstance(parsed, str):
        parsed = _literal_eval_cell(parsed, row_number, column_name)
    if not isinstance(parsed, dict):
        raise ValueError(f"{column_name} at row {row_number} must parse to a mapping.")
    return parsed


def _literal_eval_cell(value: str, row_number: int, column_name: str) -> Any:
    try:
        return ast.literal_eval(value)
    except (SyntaxError, ValueError) as exc:
        raise ValueError(
            f"Failed to parse {column_name} at row {row_number}: {exc}"
        ) from exc


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None
