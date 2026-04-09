"""Item or behavior node structure."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskInstanceSetNode:
    """TaskInstanceSet node data used in graph path results."""

    id: str
    name: str | None = None
    训练日期: str | None = None
    执行年龄: str | None = None
    执行学历: str | None = None


@dataclass(frozen=True)
class TaskInstanceNode:
    """TaskInstance node data used in graph path results."""

    id: str
    name: str | None = None
    得分: str | None = None
    常模分: str | None = None
    结果: str | None = None
    活跃: str | None = None
    任务类型: str | None = None
    状态: str | None = None


@dataclass(frozen=True)
class GameNode:
    """Game node data used in graph path results."""

    id: str
    name: str | None = None
