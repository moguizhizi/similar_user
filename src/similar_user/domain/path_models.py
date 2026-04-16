"""Pattern-specific graph path models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .graph_schema import PathPattern
from .item import (
    TASK_INSTANCE_EXCLUSIVE_TYPE_VALUES,
    TASK_INSTANCE_ACTIVITY_VALUES,
    TASK_INSTANCE_RESULT_VALUES,
    DiseaseNode,
    SymptomNode,
    TaskActivityValue,
    EducationValue,
    TASK_INSTANCE_SET_EDUCATION_VALUES,
    GameNode,
    TaskExclusiveTypeValue,
    TaskResultValue,
    TaskInstanceNode,
    TaskInstanceSetNode,
)
from .user import PatientNode


@dataclass(frozen=True)
class PatientTasksetTaskGameTaskTasksetPatientPath:
    """The P-S-I-G-I-S-P fixed graph path model."""

    pattern: PathPattern
    p: PatientNode
    s1: TaskInstanceSetNode
    i1: TaskInstanceNode
    g: GameNode
    i2: TaskInstanceNode
    s2: TaskInstanceSetNode
    p2: PatientNode

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> PatientTasksetTaskGameTaskTasksetPatientPath:
        """Build a typed path from a stored path row."""
        row = data.get("row") if isinstance(data.get("row"), dict) else data
        if not isinstance(row, dict):
            raise ValueError("path data must contain a mapping row.")

        return cls(
            pattern=_coerce_path_pattern(data.get("pattern")),
            p=_build_patient_node(row.get("p"), "p"),
            s1=_build_task_instance_set_node(row.get("s1"), "s1"),
            i1=_build_task_instance_node(row.get("i1"), "i1"),
            g=_build_game_node(row.get("g"), "g"),
            i2=_build_task_instance_node(row.get("i2"), "i2"),
            s2=_build_task_instance_set_node(row.get("s2"), "s2"),
            p2=_build_patient_node(row.get("p2"), "p2"),
        )


@dataclass(frozen=True)
class PatientTasksetDiseaseTasksetPatientPath:
    """The P-S-D-S-P fixed graph path model."""

    pattern: PathPattern
    p: PatientNode
    s1: TaskInstanceSetNode
    dis: DiseaseNode
    s2: TaskInstanceSetNode
    p2: PatientNode

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> PatientTasksetDiseaseTasksetPatientPath:
        """Build a typed path from a stored path row."""
        row = data.get("row") if isinstance(data.get("row"), dict) else data
        if not isinstance(row, dict):
            raise ValueError("path data must contain a mapping row.")

        return cls(
            pattern=_coerce_path_pattern(data.get("pattern")),
            p=_build_patient_node(row.get("p"), "p"),
            s1=_build_task_instance_set_node(row.get("s1"), "s1"),
            dis=_build_disease_node(row.get("dis"), "dis"),
            s2=_build_task_instance_set_node(row.get("s2"), "s2"),
            p2=_build_patient_node(row.get("p2"), "p2"),
        )


@dataclass(frozen=True)
class PatientTasksetSymptomTasksetPatientPath:
    """The P-S-SYM-S-P fixed graph path model."""

    pattern: PathPattern
    p: PatientNode
    s1: TaskInstanceSetNode
    sym: SymptomNode
    s2: TaskInstanceSetNode
    p2: PatientNode

    @classmethod
    def from_dict(
        cls,
        data: dict[str, Any],
    ) -> PatientTasksetSymptomTasksetPatientPath:
        """Build a typed path from a stored path row."""
        row = data.get("row") if isinstance(data.get("row"), dict) else data
        if not isinstance(row, dict):
            raise ValueError("path data must contain a mapping row.")

        return cls(
            pattern=_coerce_path_pattern(data.get("pattern")),
            p=_build_patient_node(row.get("p"), "p"),
            s1=_build_task_instance_set_node(row.get("s1"), "s1"),
            sym=_build_symptom_node(row.get("sym"), "sym"),
            s2=_build_task_instance_set_node(row.get("s2"), "s2"),
            p2=_build_patient_node(row.get("p2"), "p2"),
        )


@dataclass(frozen=True)
class PatternPathResult:
    """A patient-scoped collection of paths for one fixed pattern."""

    patient_id: str
    pattern: PathPattern
    paths: list[
        PatientTasksetTaskGameTaskTasksetPatientPath
        | PatientTasksetDiseaseTasksetPatientPath
        | PatientTasksetSymptomTasksetPatientPath
    ]


def _coerce_path_pattern(value: object) -> PathPattern:
    """Normalize a raw pattern value to the supported enum."""
    if isinstance(value, PathPattern):
        return value
    if isinstance(value, str) and value.strip():
        return PathPattern(value.strip())
    raise ValueError("pattern must be a non-empty supported path pattern string.")


def _build_patient_node(value: object, field_name: str) -> PatientNode:
    """Build a patient node from raw JSON content."""
    data = _require_mapping(value, field_name)
    return PatientNode(
        id=_require_string(data.get("id"), f"{field_name}.id"),
        name=_optional_string(data.get("name")),
        性别=_optional_string(data.get("性别")),
    )


def _build_task_instance_set_node(
    value: object,
    field_name: str,
) -> TaskInstanceSetNode:
    """Build a task-instance-set node from raw JSON content."""
    data = _require_mapping(value, field_name)
    return TaskInstanceSetNode(
        id=_require_string(data.get("id"), f"{field_name}.id"),
        name=_optional_string(data.get("name")),
        训练日期=_optional_string(data.get("训练日期")),
        执行年龄=_optional_string(data.get("执行年龄")),
        执行学历=_optional_education_value(data.get("执行学历"), f"{field_name}.执行学历"),
    )


def _build_task_instance_node(value: object, field_name: str) -> TaskInstanceNode:
    """Build a task-instance node from raw JSON content."""
    data = _require_mapping(value, field_name)
    return TaskInstanceNode(
        id=_require_string(data.get("id"), f"{field_name}.id"),
        name=_optional_string(data.get("name")),
        得分=_optional_string(data.get("得分")),
        常模分=_optional_string(data.get("常模分")),
        结果=_optional_result_value(data.get("结果"), f"{field_name}.结果"),
        活跃=_optional_activity_value(data.get("活跃"), f"{field_name}.活跃"),
        任务类型=_optional_exclusive_type_value(data.get("任务类型"), f"{field_name}.任务类型"),
        状态=_optional_string(data.get("状态")),
    )


def _build_game_node(value: object, field_name: str) -> GameNode:
    """Build a game node from raw JSON content."""
    data = _require_mapping(value, field_name)
    return GameNode.from_dict(data)


def _build_disease_node(value: object, field_name: str) -> DiseaseNode:
    """Build a disease node from raw JSON content."""
    data = _require_mapping(value, field_name)
    return DiseaseNode.from_dict(data)


def _build_symptom_node(value: object, field_name: str) -> SymptomNode:
    """Build a symptom node from raw JSON content."""
    data = _require_mapping(value, field_name)
    return SymptomNode.from_dict(data)


def _require_mapping(value: object, field_name: str) -> dict[str, Any]:
    """Validate that the given value is a mapping."""
    if not isinstance(value, dict):
        raise ValueError(f"{field_name} must be a mapping.")
    return value


def _require_string(value: object, field_name: str) -> str:
    """Validate and normalize a required string value."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string.")
    return value.strip()


def _optional_string(value: object) -> str | None:
    """Normalize an optional string value."""
    if value is None:
        return None
    if not isinstance(value, str):
        return str(value)
    return value


def _optional_education_value(value: object, field_name: str) -> EducationValue | None:
    """Normalize and validate TaskInstanceSet.执行学历."""
    normalized = _optional_string(value)
    if normalized is None:
        return None
    normalized = normalized.strip()
    if not normalized:
        return None
    if normalized not in TASK_INSTANCE_SET_EDUCATION_VALUES:
        raise ValueError(
            f"{field_name} has unsupported value {normalized!r}; "
            "expected one of the observed TaskInstanceSet.执行学历 values."
        )
    return normalized


def _optional_result_value(value: object, field_name: str) -> TaskResultValue | None:
    """Normalize and validate TaskInstance.结果."""
    normalized = _optional_string(value)
    if normalized is None:
        return None
    normalized = normalized.strip()
    if not normalized:
        return None
    if normalized not in TASK_INSTANCE_RESULT_VALUES:
        raise ValueError(
            f"{field_name} has unsupported value {normalized!r}; "
            "expected one of the supported TaskInstance.结果 values."
        )
    return normalized


def _optional_activity_value(value: object, field_name: str) -> TaskActivityValue | None:
    """Normalize and validate TaskInstance.活跃."""
    normalized = _optional_string(value)
    if normalized is None:
        return None
    normalized = normalized.strip()
    if not normalized:
        return None
    if normalized not in TASK_INSTANCE_ACTIVITY_VALUES:
        raise ValueError(
            f"{field_name} has unsupported value {normalized!r}; "
            "expected one of the supported TaskInstance.活跃 values."
        )
    return normalized


def _optional_exclusive_type_value(
    value: object, field_name: str
) -> TaskExclusiveTypeValue | None:
    """Normalize and validate TaskInstance.任务类型."""
    normalized = _optional_string(value)
    if normalized is None:
        return None
    normalized = normalized.strip()
    if not normalized:
        return None
    if normalized not in TASK_INSTANCE_EXCLUSIVE_TYPE_VALUES:
        raise ValueError(
            f"{field_name} has unsupported value {normalized!r}; "
            "expected one of the supported TaskInstance.任务类型 values."
        )
    return normalized
