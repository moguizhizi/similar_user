"""Source patient selection rules for batch similarity workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .user_service import UserService


SECONDARY_ABILITY_ANY_RULE = "secondary_ability_any"


@dataclass(frozen=True)
class SourcePatientSelectionRule:
    """Named, reproducible rule for selecting source patients."""

    name: str
    description: str
    criteria: dict[str, Any]


SOURCE_PATIENT_SELECTION_RULES: dict[str, SourcePatientSelectionRule] = {
    SECONDARY_ABILITY_ANY_RULE: SourcePatientSelectionRule(
        name=SECONDARY_ABILITY_ANY_RULE,
        description="训练记录中任意二级脑能力字段非空，且可连接到训练任务和游戏",
        criteria={
            "requires_training_date": True,
            "requires_game": True,
            "secondary_ability_rule": "any_non_null",
        },
    ),
}


def get_source_patient_selection_rule(name: str) -> SourcePatientSelectionRule:
    """Return a registered source patient selection rule."""
    normalized_name = name.strip() if isinstance(name, str) else ""
    try:
        return SOURCE_PATIENT_SELECTION_RULES[normalized_name]
    except KeyError as exc:
        supported = ", ".join(sorted(SOURCE_PATIENT_SELECTION_RULES)) or "none"
        raise ValueError(
            f"Unsupported source patient selection rule: {name}. "
            f"Supported rules: {supported}"
        ) from exc


@dataclass
class SourcePatientSelectionService:
    """Select source patient IDs using named business rules."""

    user_service: UserService

    def list_source_patient_ids(self, rule_name: str) -> list[str]:
        """Return source patient IDs matching a registered rule."""
        rule = get_source_patient_selection_rule(rule_name)
        if rule.name == SECONDARY_ABILITY_ANY_RULE:
            return (
                self.user_service.get_source_patient_ids_with_secondary_ability_scores()
            )
        raise ValueError(f"Unsupported source patient selection rule: {rule_name}.")

    def build_source_patient_payload(self, rule_name: str) -> dict[str, Any]:
        """Build a serializable source patient selection payload."""
        rule = get_source_patient_selection_rule(rule_name)
        patient_ids = self.list_source_patient_ids(rule.name)
        return {
            "rule": rule.name,
            "description": rule.description,
            "criteria": rule.criteria,
            "count": len(patient_ids),
            "patient_ids": patient_ids,
        }
