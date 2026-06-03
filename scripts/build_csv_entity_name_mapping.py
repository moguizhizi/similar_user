"""Build CSV disease-name to KG entity reverse mappings.

The script reads algorithm request/result CSV rows, extracts disease names from
``ai_params.sicksName`` and maps them to Neo4j Disease/Symptom/Unknown nodes by
normalizing KG names and aliases into a reverse index.
"""

from __future__ import annotations

import argparse
import ast
import csv
import json
import re
import sys
import unicodedata
from collections import defaultdict
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
    normalize_patient_id,
)
from similar_user.data_access.neo4j_client import Neo4jClient  # noqa: E402
from similar_user.utils.logger import get_logger  # noqa: E402


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
DEFAULT_OUTPUT_DIR = Path("data/entity_mappings")
DEFAULT_BASE_DATE = "2026-05-25"
ENTITY_TYPES = ("disease", "symptom", "unknown")
ENTITY_LABELS = {
    "disease": "Disease",
    "symptom": "Symptom",
    "unknown": "Unknown",
}
ID_KEYS = ("id", "ID", "编号", "编码")
NAME_KEYS = (
    "name",
    "Name",
    "名称",
    "标准名称",
    "disease_name",
    "symptom_name",
    "unknown_name",
)
ALIAS_KEYS = (
    "alias",
    "aliases",
    "Alias",
    "Aliases",
    "别名",
    "同义词",
    "同义名称",
    "synonym",
    "synonyms",
    "other_name",
    "other_names",
)
TEXT_SPLIT_RE = re.compile(r"[,，、;/；|]+")
CODE_PREFIX_RE = re.compile(r"^[A-Za-z][A-Za-z0-9.]*\s+(.+)$")
LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build reverse mappings from CSV disease names to KG "
            "Disease/Symptom/Unknown entity IDs."
        )
    )
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_ALGORITHM_REQUEST_RESULTS_PATH),
        help="Algorithm request/result CSV path.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to Neo4j YAML config.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for mapping outputs.",
    )
    parser.add_argument(
        "--base-date",
        default=DEFAULT_BASE_DATE,
        help="Date suffix used in generated file names.",
    )
    parser.add_argument(
        "--patient-ids-file",
        default=None,
        help="Optional file containing patient IDs to include.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional maximum number of CSV patients to process after filtering.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        result = build_csv_entity_name_mapping(
            csv_path=args.csv,
            config_path=args.config,
            output_dir=args.output_dir,
            base_date=args.base_date,
            patient_ids_file=args.patient_ids_file,
            limit=args.limit,
        )
    except Exception as exc:
        LOGGER.exception("CSV entity-name mapping failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result["summary"], ensure_ascii=False, indent=2))
    return 0


def build_csv_entity_name_mapping(
    *,
    csv_path: str | Path = DEFAULT_ALGORITHM_REQUEST_RESULTS_PATH,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    base_date: str = DEFAULT_BASE_DATE,
    patient_ids_file: str | Path | None = None,
    limit: int | None = None,
) -> dict[str, Any]:
    """Build and persist CSV disease-name mapping files."""
    patient_id_filter = read_patient_id_filter(patient_ids_file)
    entities = load_kg_entities(config_path)
    reverse_index = build_reverse_index(entities)
    csv_patients = read_csv_patient_disease_names(
        csv_path,
        patient_id_filter=patient_id_filter,
        limit=limit,
    )
    matches = build_patient_entity_matches(csv_patients, reverse_index)

    output_paths = write_mapping_outputs(
        output_dir=output_dir,
        base_date=base_date,
        reverse_index=reverse_index,
        matches=matches,
        entities=entities,
        csv_path=csv_path,
        patient_ids_file=patient_ids_file,
    )
    return {
        "summary": output_paths["summary"],
        "output_paths": output_paths,
    }


def load_kg_entities(config_path: str | Path) -> list[dict[str, Any]]:
    """Load Disease/Symptom/Unknown nodes and their properties from Neo4j."""
    query_parts = []
    for entity_type, label in ENTITY_LABELS.items():
        query_parts.append(
            f"""
MATCH (n:{label})
WHERE n.id IS NOT NULL
RETURN
    '{entity_type}' AS entity_type,
    labels(n) AS labels,
    properties(n) AS properties
""".strip()
        )
    query = "\nUNION ALL\n".join(query_parts)
    with Neo4jClient.from_config(config_path) as client:
        rows = client.run_query(query)

    entities: list[dict[str, Any]] = []
    for row in rows:
        properties = row.get("properties")
        if not isinstance(properties, dict):
            continue
        entity_id = first_text(properties, ID_KEYS)
        if not entity_id:
            continue
        entity_type = str(row.get("entity_type") or "").strip()
        name = first_text(properties, NAME_KEYS)
        entities.append(
            {
                "entity_type": entity_type,
                "entity_id": entity_id,
                "name": name,
                "labels": row.get("labels") or [],
                "properties": properties,
                "names": extract_entity_names(properties),
            }
        )
    return entities


def build_reverse_index(entities: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    """Build normalized name to entity matches."""
    index: dict[str, list[dict[str, Any]]] = defaultdict(list)
    seen: set[tuple[str, str, str]] = set()
    for entity in entities:
        for raw_name in entity.get("names") or []:
            for normalized in normalized_name_variants(raw_name):
                key = (
                    normalized,
                    str(entity["entity_type"]),
                    str(entity["entity_id"]),
                )
                if key in seen:
                    continue
                seen.add(key)
                index[normalized].append(
                    {
                        "entity_type": entity["entity_type"],
                        "entity_id": entity["entity_id"],
                        "entity_name": entity.get("name"),
                        "matched_kg_name": raw_name,
                    }
                )
    return dict(sorted(index.items()))


def read_csv_patient_disease_names(
    csv_path: str | Path,
    *,
    patient_id_filter: set[str] | None = None,
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Read patient disease names from algorithm request/result CSV."""
    patients: list[dict[str, Any]] = []
    seen_patients: set[str] = set()
    with Path(csv_path).open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        if "ai_params" not in (reader.fieldnames or []):
            raise ValueError("CSV must contain ai_params column.")
        for row_number, row in enumerate(reader, start=2):
            ai_params = parse_mapping_cell(row.get("ai_params"), row_number)
            raw_user_id = ai_params.get("user_id")
            if raw_user_id is None:
                continue
            patient_id = normalize_patient_id(raw_user_id)
            if patient_id_filter is not None and patient_id not in patient_id_filter:
                continue
            if patient_id in seen_patients:
                continue
            disease_names = extract_csv_disease_names(ai_params)
            patients.append(
                {
                    "row_number": row_number,
                    "patient_id": patient_id,
                    "raw_user_id": str(raw_user_id).strip(),
                    "disease_names": disease_names,
                }
            )
            seen_patients.add(patient_id)
            if limit is not None and len(patients) >= limit:
                break
    return patients


def build_patient_entity_matches(
    patients: list[dict[str, Any]],
    reverse_index: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    """Map each CSV disease name to zero, one, or many KG entities."""
    patient_matches: list[dict[str, Any]] = []
    for patient in patients:
        disease_results = []
        matched_entities: dict[tuple[str, str], dict[str, Any]] = {}
        unmatched_names = []
        ambiguous_names = []
        for raw_name in patient.get("disease_names") or []:
            keys = normalized_name_variants(raw_name)
            matches = merge_entity_matches(
                match for key in keys for match in reverse_index.get(key, [])
            )
            status = "unmatched"
            if len(matches) == 1:
                status = "matched"
            elif len(matches) > 1:
                status = "ambiguous"
                ambiguous_names.append(raw_name)
            else:
                unmatched_names.append(raw_name)
            for match in matches:
                matched_entities[(match["entity_type"], match["entity_id"])] = match
            disease_results.append(
                {
                    "raw_name": raw_name,
                    "normalized_keys": keys,
                    "status": status,
                    "matches": matches,
                }
            )
        patient_matches.append(
            {
                **patient,
                "disease_name_results": disease_results,
                "matched_entity_count": len(matched_entities),
                "matched_entities": list(matched_entities.values()),
                "unmatched_names": unmatched_names,
                "ambiguous_names": ambiguous_names,
            }
        )
    return patient_matches


def write_mapping_outputs(
    *,
    output_dir: str | Path,
    base_date: str,
    reverse_index: dict[str, list[dict[str, Any]]],
    matches: list[dict[str, Any]],
    entities: list[dict[str, Any]],
    csv_path: str | Path,
    patient_ids_file: str | Path | None,
) -> dict[str, Any]:
    """Persist reverse index and CSV match diagnostics."""
    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    date_slug = slug_part(base_date)

    reverse_index_path = resolved_output_dir / "entity_name_reverse_index.json"
    matches_path = resolved_output_dir / f"csv_patient_entity_matches_{date_slug}.json"
    unmatched_path = resolved_output_dir / f"unmatched_csv_disease_names_{date_slug}.txt"
    ambiguous_path = resolved_output_dir / f"ambiguous_csv_disease_names_{date_slug}.json"
    summary_path = resolved_output_dir / f"csv_entity_mapping_summary_{date_slug}.json"

    unmatched_names = sorted(
        {name for item in matches for name in item.get("unmatched_names", [])}
    )
    ambiguous_items = [
        result
        for item in matches
        for result in item.get("disease_name_results", [])
        if result.get("status") == "ambiguous"
    ]
    entity_type_counts: dict[str, int] = {}
    for entity in entities:
        entity_type = str(entity.get("entity_type"))
        entity_type_counts[entity_type] = entity_type_counts.get(entity_type, 0) + 1

    summary = {
        "csv_path": str(csv_path),
        "patient_ids_file": str(patient_ids_file) if patient_ids_file else None,
        "patient_count": len(matches),
        "entity_count": len(entities),
        "entity_type_counts": entity_type_counts,
        "reverse_index_key_count": len(reverse_index),
        "patients_with_match_count": sum(
            1 for item in matches if item.get("matched_entity_count", 0) > 0
        ),
        "patients_without_match_count": sum(
            1 for item in matches if item.get("matched_entity_count", 0) == 0
        ),
        "unique_unmatched_name_count": len(unmatched_names),
        "ambiguous_name_count": len(ambiguous_items),
        "reverse_index_path": str(reverse_index_path),
        "matches_path": str(matches_path),
        "unmatched_path": str(unmatched_path),
        "ambiguous_path": str(ambiguous_path),
        "summary_path": str(summary_path),
    }

    reverse_index_path.write_text(
        json.dumps(reverse_index, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    matches_path.write_text(
        json.dumps(matches, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    unmatched_path.write_text(
        "".join(f"{name}\n" for name in unmatched_names),
        encoding="utf-8",
    )
    ambiguous_path.write_text(
        json.dumps(ambiguous_items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "summary": summary,
        "reverse_index_path": reverse_index_path,
        "matches_path": matches_path,
        "unmatched_path": unmatched_path,
        "ambiguous_path": ambiguous_path,
        "summary_path": summary_path,
    }


def extract_entity_names(properties: dict[str, Any]) -> list[str]:
    """Extract canonical names and aliases from an entity property map."""
    names: list[str] = []
    for key in (*NAME_KEYS, *ALIAS_KEYS):
        if key not in properties:
            continue
        for value in flatten_text_values(properties.get(key)):
            if value not in names:
                names.append(value)
    return names


def extract_csv_disease_names(ai_params: dict[str, Any]) -> list[str]:
    """Extract disease names from CSV ai_params."""
    names: list[str] = []
    for value in flatten_text_values(ai_params.get("sicksName")):
        for part in split_name_text(value):
            if part not in names:
                names.append(part)
    behavior_data = ai_params.get("behavior_data")
    if isinstance(behavior_data, dict):
        for value in flatten_text_values(behavior_data.get("sicks")):
            for part in split_name_text(value):
                if part not in names:
                    names.append(part)
    return names


def normalized_name_variants(value: object) -> list[str]:
    """Return normalized keys for a disease/entity name."""
    text = normalize_name(value)
    if not text:
        return []
    variants = [text]
    for candidate in (strip_code_prefix_raw(value), strip_code_prefix(text)):
        stripped = normalize_name(candidate)
        if stripped and stripped not in variants:
            variants.append(stripped)
    return variants


def normalize_name(value: object) -> str:
    text = str(value if value is not None else "").strip()
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = text.lower()
    text = re.sub(r"\s+", "", text)
    return text.strip(" ,，、;；/|")


def strip_code_prefix(normalized_text: str) -> str:
    spaced = re.sub(r"^([a-z0-9][a-z0-9.]*)([^a-z0-9.].*)$", r"\1 \2", normalized_text)
    match = CODE_PREFIX_RE.match(spaced)
    if not match:
        return ""
    return normalize_name(match.group(1))


def strip_code_prefix_raw(value: object) -> str:
    text = unicodedata.normalize("NFKC", str(value if value is not None else "")).strip()
    match = CODE_PREFIX_RE.match(text)
    return match.group(1) if match else ""


def split_name_text(value: object) -> list[str]:
    text = str(value if value is not None else "").strip()
    if not text:
        return []
    parts = [part.strip() for part in TEXT_SPLIT_RE.split(text)]
    return [part for part in parts if part and part.lower() not in {"none", "null", "无"}]


def flatten_text_values(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        texts: list[str] = []
        for item in value:
            texts.extend(flatten_text_values(item))
        return texts
    if isinstance(value, str):
        parsed = parse_literal_if_collection(value)
        if parsed is not value:
            return flatten_text_values(parsed)
        return split_name_text(value)
    return [str(value).strip()] if str(value).strip() else []


def parse_literal_if_collection(value: str) -> Any:
    stripped = value.strip()
    if not stripped or stripped[0] not in "[{(":
        return value
    try:
        return ast.literal_eval(stripped)
    except (SyntaxError, ValueError):
        return value


def merge_entity_matches(matches: Any) -> list[dict[str, Any]]:
    merged: dict[tuple[str, str], dict[str, Any]] = {}
    for match in matches:
        key = (str(match["entity_type"]), str(match["entity_id"]))
        merged.setdefault(key, match)
    return sorted(
        merged.values(),
        key=lambda item: (str(item["entity_type"]), str(item["entity_id"])),
    )


def first_text(properties: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        if key not in properties:
            continue
        values = flatten_text_values(properties.get(key))
        if values:
            return values[0]
    return None


def parse_mapping_cell(value: object, row_number: int) -> dict[str, Any]:
    if not isinstance(value, str):
        raise ValueError(f"ai_params at row {row_number} must be a string.")
    try:
        parsed = ast.literal_eval(value)
        if isinstance(parsed, str):
            parsed = ast.literal_eval(parsed)
    except (SyntaxError, ValueError) as exc:
        raise ValueError(f"Failed to parse ai_params at row {row_number}: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"ai_params at row {row_number} must parse to a mapping.")
    return parsed


def read_patient_id_filter(path: str | Path | None) -> set[str] | None:
    if path is None:
        return None
    patient_ids = {
        normalize_patient_id(line)
        for line in Path(path).read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    }
    return patient_ids


def slug_part(value: object) -> str:
    text = str(value).strip()
    return "".join(char if char.isalnum() else "-" for char in text) or "unknown"


if __name__ == "__main__":
    raise SystemExit(main())
