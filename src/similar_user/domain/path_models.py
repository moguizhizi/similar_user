"""Pattern-specific graph path models."""

from __future__ import annotations

from dataclasses import dataclass

from .graph_schema import PathPattern
from .item import GameNode, TaskInstanceNode, TaskInstanceSetNode
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


@dataclass(frozen=True)
class PatternPathResult:
    """A patient-scoped collection of paths for one fixed pattern."""

    patient_id: str
    pattern: PathPattern
    paths: list[PatientTasksetTaskGameTaskTasksetPatientPath]
