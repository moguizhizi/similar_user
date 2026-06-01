"""Export non-KG patient profiles from algorithm request/result snapshots.

The output JSONL is intended as input for the direct-entity, non-patient
prediction flow.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from similar_user.data_access.algorithm_request_results import (  # noqa: E402
    DEFAULT_ALGORITHM_REQUEST_RESULTS_PATH,
    load_algorithm_request_results,
    normalize_algorithm_request_education,
    normalize_algorithm_request_gender,
)
from similar_user.utils.logger import get_logger  # noqa: E402


LOGGER = get_logger(__name__)
DEFAULT_BASE_DATE = "2026-05-25"
DEFAULT_PATIENT_IDS_PATH = Path(
    "data/patient_ids/base_2026-05-25/patients_inactive_2026-05-25.txt"
)
DEFAULT_OUTPUT_DIR = Path("data/direct_entity_inputs")


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Export inactive non-KG patient profiles for direct entity prediction."
    )
    parser.add_argument("--base-date", default=DEFAULT_BASE_DATE)
    parser.add_argument(
        "--patient-ids-path",
        default=str(DEFAULT_PATIENT_IDS_PATH),
        help="Text file containing one inactive patient ID per line.",
    )
    parser.add_argument(
        "--csv-path",
        default=str(DEFAULT_ALGORITHM_REQUEST_RESULTS_PATH),
        help="Algorithm_Request_Results CSV path.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSONL output path.",
    )
    parser.add_argument(
        "--summary-output",
        help="Optional summary JSON output path.",
    )
    return parser.parse_args()


def export_inactive_patient_profiles(
    *,
    base_date: str = DEFAULT_BASE_DATE,
    patient_ids_path: str | Path = DEFAULT_PATIENT_IDS_PATH,
    csv_path: str | Path = DEFAULT_ALGORITHM_REQUEST_RESULTS_PATH,
    output_path: str | Path | None = None,
    summary_output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Build profile JSONL records from inactive IDs and algorithm request CSV."""
    patient_ids = read_patient_ids(patient_ids_path)
    index = load_algorithm_request_results(csv_path)
    profiles: list[dict[str, Any]] = []
    missing_patient_ids: list[str] = []
    skipped_patient_ids: list[dict[str, str]] = []

    for patient_id in patient_ids:
        lookup = index.get_by_patient_id(patient_id)
        records = lookup.get("records") or []
        if not records:
            missing_patient_ids.append(patient_id)
            continue
        try:
            profiles.append(build_profile_record(patient_id, records[0], base_date))
        except ValueError as exc:
            skipped_patient_ids.append(
                {
                    "patient_id": patient_id,
                    "reason": str(exc),
                }
            )

    resolved_output_path = Path(output_path) if output_path else build_output_path(base_date)
    write_jsonl_atomic(resolved_output_path, profiles)

    summary = {
        "base_date": base_date,
        "patient_ids_path": str(patient_ids_path),
        "csv_path": str(csv_path),
        "output_path": str(resolved_output_path),
        "patient_id_count": len(patient_ids),
        "profile_count": len(profiles),
        "missing_count": len(missing_patient_ids),
        "skipped_count": len(skipped_patient_ids),
        "missing_patient_ids": missing_patient_ids,
        "skipped_patient_ids": skipped_patient_ids,
    }
    resolved_summary_path = (
        Path(summary_output_path)
        if summary_output_path
        else resolved_output_path.with_suffix(".summary.json")
    )
    write_json_atomic(resolved_summary_path, summary)
    summary["summary_output_path"] = str(resolved_summary_path)
    LOGGER.info(json.dumps(summary, ensure_ascii=False, indent=2))
    return summary


def build_profile_record(
    patient_id: str,
    record: dict[str, Any],
    base_date: str,
) -> dict[str, Any]:
    """Normalize one CSV record into direct-entity prediction input."""
    ai_params = record.get("ai_params")
    if not isinstance(ai_params, dict):
        raise ValueError("ai_params must be a mapping.")

    behavior_data = ai_params.get("behavior_data")
    if not isinstance(behavior_data, dict):
        behavior_data = {}

    age = _parse_required_int(_first_present(behavior_data.get("age"), ai_params.get("age")), "age")
    gender = normalize_gender(_first_present(behavior_data.get("gender"), ai_params.get("sex")))
    education = normalize_education_from_sources(
        behavior_data.get("edu"),
        ai_params.get("education"),
    )
    disease_names = normalize_disease_names(
        _first_present(behavior_data.get("sicks"), ai_params.get("sicksName"))
    )

    return {
        "patient_id": patient_id,
        "base_date": base_date,
        "age": age,
        "education": education,
        "gender": gender,
        "disease_names": disease_names,
        "source": {
            "row_number": record.get("row_number"),
            "raw_user_id": record.get("raw_user_id"),
        },
        "raw_profile": {
            "age": ai_params.get("age"),
            "sex": ai_params.get("sex"),
            "education": ai_params.get("education"),
            "sicksName": ai_params.get("sicksName"),
            "behavior_data": {
                key: behavior_data.get(key)
                for key in ("age", "gender", "edu", "sicks", "dt")
                if key in behavior_data
            },
        },
    }


def read_patient_ids(path: str | Path) -> list[str]:
    """Read non-empty patient IDs from a line-delimited text file."""
    resolved_path = Path(path)
    patient_ids = []
    seen: set[str] = set()
    for line in resolved_path.read_text(encoding="utf-8").splitlines():
        patient_id = line.strip()
        if not patient_id or patient_id in seen:
            continue
        patient_ids.append(patient_id)
        seen.add(patient_id)
    return patient_ids


def build_output_path(base_date: str) -> Path:
    """Return the default inactive profile JSONL path."""
    return (
        DEFAULT_OUTPUT_DIR
        / f"base_{base_date}"
        / f"inactive_patient_profiles_{base_date}.jsonl"
    )


def normalize_gender(value: object) -> str:
    """Normalize CSV gender values into KG-facing text."""
    return normalize_algorithm_request_gender(value)


def normalize_education(value: object) -> str:
    """Normalize algorithm request education code or label into KG-facing text."""
    return normalize_algorithm_request_education(value)


def normalize_education_from_sources(*values: object) -> str:
    """Normalize education from preferred sources, falling back on later values."""
    errors = []
    for value in values:
        if _normalize_optional_text(value) is None:
            continue
        try:
            return normalize_education(value)
        except ValueError as exc:
            errors.append(str(exc))
    if errors:
        raise ValueError(errors[-1])
    raise ValueError("education is required.")


def normalize_disease_names(value: object) -> list[str]:
    """Normalize disease-name cells to a de-duplicated list."""
    raw_items: list[object]
    if value is None:
        raw_items = []
    elif isinstance(value, list):
        raw_items = value
    elif isinstance(value, tuple):
        raw_items = list(value)
    else:
        raw_items = str(value).replace("，", ",").replace("；", ",").split(",")

    names = []
    seen: set[str] = set()
    for item in raw_items:
        text = _normalize_optional_text(item)
        if text is None or text in seen:
            continue
        names.append(text)
        seen.add(text)
    return names


def write_jsonl_atomic(path: Path, records: list[dict[str, Any]]) -> None:
    """Write JSONL atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        for record in records:
            temp_file.write(json.dumps(record, ensure_ascii=False, default=str))
            temp_file.write("\n")
        temp_path = Path(temp_file.name)
    os.replace(temp_path, path)


def write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    """Write JSON atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        json.dump(payload, temp_file, ensure_ascii=False, indent=2, default=str)
        temp_path = Path(temp_file.name)
    os.replace(temp_path, path)


def _first_present(*values: object) -> object:
    for value in values:
        if _normalize_optional_text(value) is not None:
            return value
    return None


def _parse_required_int(value: object, field_name: str) -> int:
    text = _normalize_optional_text(value)
    if text is None:
        raise ValueError(f"{field_name} is required.")
    try:
        parsed = int(float(text))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative.")
    return parsed


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def main() -> int:
    """Run the profile export."""
    args = parse_args()
    try:
        export_inactive_patient_profiles(
            base_date=args.base_date,
            patient_ids_path=args.patient_ids_path,
            csv_path=args.csv_path,
            output_path=args.output,
            summary_output_path=args.summary_output,
        )
    except Exception as exc:
        LOGGER.exception("Inactive profile export failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
