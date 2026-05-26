"""Resolve inputs needed before direct entity path scoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class DirectEntityScoringInput:
    """Normalized input consumed by a future direct-entity path scorer."""

    patient_id: str | None
    age: int
    education: str
    gender: str
    disease_ids: tuple[str, ...] = field(default_factory=tuple)
    symptom_ids: tuple[str, ...] = field(default_factory=tuple)
    unknown_ids: tuple[str, ...] = field(default_factory=tuple)
    source: str = "manual_cli"
    effective_date: str | None = None
    profile_age: int | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable mapping."""
        return {
            "patient_id": self.patient_id,
            "age": self.age,
            "education": self.education,
            "gender": self.gender,
            "disease_ids": list(self.disease_ids),
            "symptom_ids": list(self.symptom_ids),
            "unknown_ids": list(self.unknown_ids),
            "source": self.source,
            "effective_date": self.effective_date,
            "profile_age": self.profile_age,
        }


@dataclass(frozen=True)
class DirectEntityScoringInputResolution:
    """Decision result for whether direct-entity path scoring should run."""

    should_score: bool
    reason: str
    scoring_input: DirectEntityScoringInput | None = None

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable mapping."""
        return {
            "should_score": self.should_score,
            "reason": self.reason,
            "scoring_input": (
                self.scoring_input.to_dict() if self.scoring_input is not None else None
            ),
        }


def resolve_scoring_input(
    *,
    kg_repository: Any,
    patient_id: str | None = None,
    base_date: str | None = None,
    age: int | str | None = None,
    education: str | None = None,
    gender: str | None = None,
    disease_ids: list[str] | tuple[str, ...] | None = None,
    symptom_ids: list[str] | tuple[str, ...] | None = None,
    unknown_ids: list[str] | tuple[str, ...] | None = None,
    use_when_patient_exists: bool = False,
) -> DirectEntityScoringInputResolution:
    """Resolve KG-derived or manual CLI input for direct-entity path scoring."""
    normalized_patient_id = _normalize_optional_text(patient_id)
    if normalized_patient_id is None:
        return DirectEntityScoringInputResolution(
            should_score=True,
            reason="manual_input_without_patient_id",
            scoring_input=_build_manual_input(
                patient_id=None,
                age=age,
                education=education,
                gender=gender,
                disease_ids=disease_ids,
                symptom_ids=symptom_ids,
                unknown_ids=unknown_ids,
                source="manual_cli",
            ),
        )

    if kg_repository.patient_exists(normalized_patient_id):
        if not use_when_patient_exists:
            return DirectEntityScoringInputResolution(
                should_score=False,
                reason="patient_exists_direct_entity_path_disabled",
                scoring_input=None,
            )

        scoring_input = load_profile_from_kg(
            kg_repository=kg_repository,
            patient_id=normalized_patient_id,
            base_date=base_date,
        )
        if scoring_input is None:
            raise ValueError(
                "patient exists in KG, but no usable direct entity scoring profile "
                f"was found for patient_id={normalized_patient_id}."
            )
        _require_entity_ids(scoring_input)
        return DirectEntityScoringInputResolution(
            should_score=True,
            reason="kg_profile",
            scoring_input=scoring_input,
        )

    try:
        scoring_input = _build_manual_input(
            patient_id=normalized_patient_id,
            age=age,
            education=education,
            gender=gender,
            disease_ids=disease_ids,
            symptom_ids=symptom_ids,
            unknown_ids=unknown_ids,
            source="manual_cli_patient_not_in_kg",
        )
    except ValueError as exc:
        raise ValueError(
            f"patient_id={normalized_patient_id} does not exist in KG; "
            "please provide --age, --education, --gender, and at least one of "
            "--disease-id, --symptom-id, or --unknown-id."
        ) from exc

    return DirectEntityScoringInputResolution(
        should_score=True,
        reason="manual_input_patient_not_in_kg",
        scoring_input=scoring_input,
    )


def load_profile_from_kg(
    *,
    kg_repository: Any,
    patient_id: str,
    base_date: str | None,
) -> DirectEntityScoringInput | None:
    """Load a patient's direct-entity scoring profile from KG."""
    normalized_patient_id = _normalize_required_text(patient_id, "patient_id")
    normalized_base_date = _normalize_required_text(base_date, "base_date")
    rows = kg_repository.get_patient_direct_entity_scoring_profile(
        normalized_patient_id,
        normalized_base_date,
    )
    if not rows:
        return None

    row = rows[0]
    return DirectEntityScoringInput(
        patient_id=_normalize_optional_text(row.get("patient_id"))
        or normalized_patient_id,
        age=_parse_required_int(row.get("age_at_base_date"), "age_at_base_date"),
        education=_normalize_required_text(row.get("education"), "education"),
        gender=_normalize_required_text(row.get("gender"), "gender"),
        disease_ids=_normalize_id_list(row.get("disease_ids")),
        symptom_ids=_normalize_id_list(row.get("symptom_ids")),
        unknown_ids=_normalize_id_list(row.get("unknown_ids")),
        source="kg_profile",
        effective_date=_normalize_optional_text(row.get("effective_date")),
        profile_age=_parse_optional_int(row.get("profile_age"), "profile_age"),
    )


def _build_manual_input(
    *,
    patient_id: str | None,
    age: int | str | None,
    education: str | None,
    gender: str | None,
    disease_ids: list[str] | tuple[str, ...] | None,
    symptom_ids: list[str] | tuple[str, ...] | None,
    unknown_ids: list[str] | tuple[str, ...] | None,
    source: str,
) -> DirectEntityScoringInput:
    scoring_input = DirectEntityScoringInput(
        patient_id=patient_id,
        age=_parse_required_int(age, "age"),
        education=_normalize_required_text(education, "education"),
        gender=_normalize_required_text(gender, "gender"),
        disease_ids=_normalize_id_list(disease_ids),
        symptom_ids=_normalize_id_list(symptom_ids),
        unknown_ids=_normalize_id_list(unknown_ids),
        source=source,
    )
    _require_entity_ids(scoring_input)
    return scoring_input


def _require_entity_ids(scoring_input: DirectEntityScoringInput) -> None:
    if (
        not scoring_input.disease_ids
        and not scoring_input.symptom_ids
        and not scoring_input.unknown_ids
    ):
        raise ValueError(
            "At least one of disease_ids, symptom_ids, or unknown_ids must be provided."
        )


def _normalize_id_list(value: object) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, (list, tuple)):
        raise ValueError("entity id lists must be lists or tuples.")
    normalized: list[str] = []
    seen: set[str] = set()
    for item in value:
        text = _normalize_optional_text(item)
        if text is None or text in seen:
            continue
        normalized.append(text)
        seen.add(text)
    return tuple(normalized)


def _normalize_required_text(value: object, field_name: str) -> str:
    normalized = _normalize_optional_text(value)
    if normalized is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return normalized


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _parse_required_int(value: object, field_name: str) -> int:
    parsed = _parse_optional_int(value, field_name)
    if parsed is None:
        raise ValueError(f"{field_name} must be an integer.")
    if parsed < 0:
        raise ValueError(f"{field_name} must be non-negative.")
    return parsed


def _parse_optional_int(value: object, field_name: str) -> int | None:
    if value is None:
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError as exc:
        raise ValueError(f"{field_name} must be an integer.") from exc
