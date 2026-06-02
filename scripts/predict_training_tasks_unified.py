"""Route training-task prediction to patient or direct-entity workflow."""

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

from similar_user.data_access.kg_repository import KgRepository  # noqa: E402
from similar_user.data_access.neo4j_client import Neo4jClient  # noqa: E402
from similar_user.domain.graph_schema import (  # noqa: E402
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
)
from similar_user.services.task_prediction import DEFAULT_TASK_TOP_K  # noqa: E402
from similar_user.utils.logger import get_logger  # noqa: E402
from config.settings import load_query_settings  # noqa: E402

from scripts.predict_training_tasks import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    run_end_to_end_training_task_prediction,
    summarize_prediction_result as summarize_patient_prediction_result,
    write_prompt_to_file,
)
from scripts.predict_training_tasks_from_direct_entity import (  # noqa: E402
    predict_training_tasks_from_direct_entity,
    summarize_prediction_result as summarize_direct_entity_prediction_result,
)


LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for unified patient/direct-entity prediction."""
    parser = argparse.ArgumentParser(
        description="Route training-task prediction by patient existence."
    )
    parser.add_argument("--patient-id", required=True, help="Prediction target ID.")
    parser.add_argument("--base-date", required=True, help="Prediction base date.")
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    parser.add_argument(
        "--pattern",
        default=PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        help="Patient-path pattern used when the patient exists.",
    )
    parser.add_argument(
        "--query-family",
        default=None,
        help="Patient-path query family used when the patient exists.",
    )
    parser.add_argument(
        "--skip-path-build",
        action="store_true",
        help="Patient path only: use existing saved raw paths.",
    )
    parser.add_argument(
        "--skip-path-scoring",
        action="store_true",
        help="Patient path only: use existing scored paths.",
    )
    parser.add_argument("--age", help="Direct entity path only: target age.")
    parser.add_argument("--education", help="Direct entity path only: target education.")
    parser.add_argument("--gender", help="Direct entity path only: target gender.")
    parser.add_argument(
        "--disease-id",
        action="append",
        nargs="+",
        default=[],
        help="Direct entity path only: disease IDs.",
    )
    parser.add_argument(
        "--disease-name",
        action="append",
        nargs="+",
        default=[],
        help="Direct entity path only: disease/entity names resolved from KG.",
    )
    parser.add_argument(
        "--symptom-id",
        action="append",
        nargs="+",
        default=[],
        help="Direct entity path only: symptom IDs.",
    )
    parser.add_argument(
        "--unknown-id",
        action="append",
        nargs="+",
        default=[],
        help="Direct entity path only: unknown entity IDs.",
    )
    parser.add_argument(
        "--task-top-k",
        type=int,
        default=DEFAULT_TASK_TOP_K,
        help="Number of predicted training tasks to return.",
    )
    parser.add_argument(
        "--output-level",
        choices=("ids", "scores", "full"),
        default="ids",
        help="Output detail level.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Skip the LLM call and return deterministic candidate-task predictions.",
    )
    parser.add_argument(
        "--include-prompt",
        action="store_true",
        help="Include the generated LLM prompt in full output.",
    )
    parser.add_argument("--output", help="Optional JSON output path.")
    return parser.parse_args()


def predict_training_tasks_unified(
    *,
    patient_id: str,
    base_date: str,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    pattern: str = PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    query_family: str | None = None,
    skip_path_build: bool = False,
    skip_path_scoring: bool = False,
    age: int | str | None = None,
    education: str | None = None,
    gender: str | None = None,
    disease_ids: list[str] | None = None,
    disease_names: list[str] | None = None,
    symptom_ids: list[str] | None = None,
    unknown_ids: list[str] | None = None,
    task_top_k: int = DEFAULT_TASK_TOP_K,
    use_llm: bool = True,
    include_prompt: bool = False,
) -> dict[str, Any]:
    """Route prediction by whether patient_id exists in KG."""
    normalized_patient_id = _normalize_required_text(patient_id, "patient_id")
    resolved_config_path = Path(config_path)
    patient_exists = _patient_exists(
        normalized_patient_id,
        config_path=resolved_config_path,
    )
    if patient_exists:
        LOGGER.info(
            "Routing unified prediction to patient path: patient_id=%s",
            normalized_patient_id,
        )
        result = run_end_to_end_training_task_prediction(
            normalized_patient_id,
            base_date=base_date,
            pattern=pattern,
            config_path=resolved_config_path,
            skip_path_build=skip_path_build,
            skip_path_scoring=skip_path_scoring,
            query_family=query_family,
            task_top_k=task_top_k,
            use_llm=use_llm,
            include_prompt=include_prompt,
        )
        return {
            "route": "patient_path",
            "patient_exists": True,
            "result": result,
        }

    _validate_direct_entity_inputs(
        age=age,
        education=education,
        gender=gender,
        disease_ids=disease_ids or [],
        disease_names=disease_names or [],
        symptom_ids=symptom_ids or [],
        unknown_ids=unknown_ids or [],
    )
    LOGGER.info(
        "Routing unified prediction to direct entity path: patient_id=%s",
        normalized_patient_id,
    )
    result = predict_training_tasks_from_direct_entity(
        patient_id=normalized_patient_id,
        base_date=base_date,
        age=age,
        education=str(education),
        gender=str(gender),
        disease_ids=disease_ids or [],
        disease_names=disease_names or [],
        symptom_ids=symptom_ids or [],
        unknown_ids=unknown_ids or [],
        config_path=resolved_config_path,
        use_llm=use_llm,
        include_prompt=include_prompt,
        task_top_k=task_top_k,
    )
    return {
        "route": "direct_entity_path",
        "patient_exists": False,
        "result": result,
    }


def summarize_unified_prediction_result(
    result: dict[str, Any],
    *,
    output_level: str,
) -> dict[str, Any]:
    """Summarize the routed prediction result."""
    route = result.get("route")
    inner = result.get("result")
    if not isinstance(inner, dict):
        inner = {}
    if output_level == "full":
        return result
    if route == "patient_path":
        summary = summarize_patient_prediction_result(inner, output_level=output_level)
        return _with_route_summary(
            summary,
            route="patient_path",
            patient_exists=True,
        )
    if route == "direct_entity_path":
        summary = summarize_direct_entity_prediction_result(
            inner,
            output_level=output_level,
        )
        return _with_route_summary(
            summary,
            route="direct_entity_path",
            patient_exists=False,
        )
    raise ValueError(f"Unsupported prediction route: {route}.")


def _with_route_summary(
    summary: dict[str, Any],
    *,
    route: str,
    patient_exists: bool,
) -> dict[str, Any]:
    if not isinstance(summary, dict):
        raise ValueError("Unified prediction summary must be a JSON object.")
    routed_summary = dict(summary)
    routed_summary["route"] = route
    routed_summary["patient_exists"] = patient_exists
    return routed_summary


def _patient_exists(patient_id: str, *, config_path: str | Path) -> bool:
    with Neo4jClient.from_config(config_path) as client:
        repository = KgRepository(client=client, config_path=Path(config_path))
        return bool(repository.patient_exists(patient_id))


def _validate_direct_entity_inputs(
    *,
    age: object,
    education: object,
    gender: object,
    disease_ids: list[str],
    disease_names: list[str],
    symptom_ids: list[str],
    unknown_ids: list[str],
) -> None:
    missing_fields = [
        name
        for name, value in (
            ("age", age),
            ("education", education),
            ("gender", gender),
        )
        if _normalize_optional_text(value) is None
    ]
    if missing_fields:
        raise ValueError(
            "Non-patient direct entity prediction requires: "
            + ", ".join(missing_fields)
        )
    if not (
        _dedupe_texts(disease_ids)
        or _dedupe_texts(disease_names)
        or _dedupe_texts(symptom_ids)
        or _dedupe_texts(unknown_ids)
    ):
        raise ValueError(
            "Non-patient direct entity prediction requires at least one disease, "
            "symptom, unknown entity ID, or disease name."
        )


def _flatten(values: list[list[str]] | None) -> list[str]:
    flattened: list[str] = []
    for group in values or []:
        for item in group:
            text = _normalize_optional_text(item)
            if text is not None:
                flattened.append(text)
    return flattened


def _dedupe_texts(values: list[str]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = _normalize_optional_text(value)
        if text is None or text in seen:
            continue
        deduped.append(text)
        seen.add(text)
    return deduped


def _normalize_required_text(value: object, field_name: str) -> str:
    text = _normalize_optional_text(value)
    if text is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return text


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_file.write(serialized)
        temp_path = Path(temp_file.name)
    os.replace(temp_path, path)


def main() -> int:
    """Run unified training-task prediction."""
    args = parse_args()
    try:
        query_settings = load_query_settings(args.config)
        save_prompt = query_settings.training_task_prediction.save_prompt_enabled
        result = predict_training_tasks_unified(
            patient_id=args.patient_id,
            base_date=args.base_date,
            config_path=args.config,
            pattern=args.pattern,
            query_family=args.query_family,
            skip_path_build=args.skip_path_build,
            skip_path_scoring=args.skip_path_scoring,
            age=args.age,
            education=args.education,
            gender=args.gender,
            disease_ids=_flatten(args.disease_id),
            disease_names=_flatten(args.disease_name),
            symptom_ids=_flatten(args.symptom_id),
            unknown_ids=_flatten(args.unknown_id),
            task_top_k=args.task_top_k,
            use_llm=not args.dry_run,
            include_prompt=args.include_prompt or save_prompt,
        )
        output = summarize_unified_prediction_result(
            result,
            output_level=args.output_level,
        )
        if args.output:
            _write_json_atomic(Path(args.output), result)
        prompt_path = None
        if save_prompt:
            inner_result = result.get("result")
            if isinstance(inner_result, dict):
                prompt_path = write_prompt_to_file(
                    inner_result,
                    base_date=args.base_date,
                )
        LOGGER.info(json.dumps(output, ensure_ascii=False, indent=2, default=str))
        if prompt_path is not None:
            LOGGER.info("Saved training-task prediction prompt to %s", prompt_path)
    except Exception as exc:
        LOGGER.exception("Unified training task prediction failed: %s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
