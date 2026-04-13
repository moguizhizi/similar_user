"""Pattern-specific graph path models."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
class PatternPathResult:
    """A patient-scoped collection of paths for one fixed pattern."""

    patient_id: str
    pattern: PathPattern
    paths: list[PatientTasksetTaskGameTaskTasksetPatientPath]


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
        执行学历=_optional_string(data.get("执行学历")),
    )


def _build_task_instance_node(value: object, field_name: str) -> TaskInstanceNode:
    """Build a task-instance node from raw JSON content."""
    data = _require_mapping(value, field_name)
    return TaskInstanceNode(
        id=_require_string(data.get("id"), f"{field_name}.id"),
        name=_optional_string(data.get("name")),
        得分=_optional_string(data.get("得分")),
        常模分=_optional_string(data.get("常模分")),
        结果=_optional_string(data.get("结果")),
        活跃=_optional_string(data.get("活跃")),
        任务类型=_optional_string(data.get("任务类型")),
        状态=_optional_string(data.get("状态")),
    )


def _build_game_node(value: object, field_name: str) -> GameNode:
    """Build a game node from raw JSON content."""
    data = _require_mapping(value, field_name)
    return GameNode(
        id=_require_string(data.get("id"), f"{field_name}.id"),
        name=_optional_string(data.get("name")),
        UI边框样式=_optional_string(data.get("UI边框样式")),
        主要颜色=_optional_string(data.get("主要颜色")),
        交互对象=_optional_string(data.get("交互对象")),
        交互按钮类型=_optional_string(data.get("交互按钮类型")),
        任务动机=_optional_string(data.get("任务动机")),
        任务类型=_optional_string(data.get("任务类型")),
        任务阶段划分=_optional_string(data.get("任务阶段划分")),
        体验情景=_optional_string(data.get("体验情景")),
        信息复杂度=_optional_string(data.get("信息复杂度")),
        元素大小=_optional_string(data.get("元素大小")),
        元素密度=_optional_string(data.get("元素密度")),
        内部负荷=_optional_string(data.get("内部负荷")),
        出题方式=_optional_string(data.get("出题方式")),
        叙事性强度=_optional_string(data.get("叙事性强度")),
        同屏spine数量上限=_optional_float(data.get("同屏spine数量上限")),
        图像细节丰富度=_optional_string(data.get("图像细节丰富度")),
        图形符号化程度=_optional_string(data.get("图形符号化程度")),
        地域=_optional_string(data.get("地域")),
        场景拟真度=_optional_string(data.get("场景拟真度")),
        外部负荷=_optional_string(data.get("外部负荷")),
        宏观题材分类=_optional_string(data.get("宏观题材分类")),
        年代=_optional_string(data.get("年代")),
        思维类型=_optional_string(data.get("思维类型")),
        情感氛围=_optional_string(data.get("情感氛围")),
        情绪色彩倾向=_optional_string(data.get("情绪色彩倾向")),
        感知类型=_optional_string(data.get("感知类型")),
        指示明确性=_optional_string(data.get("指示明确性")),
        操作方式=_optional_string(data.get("操作方式")),
        操作频率=_optional_string(data.get("操作频率")),
        整体环境风格=_optional_string(data.get("整体环境风格")),
        是否含拟人化元素=_optional_string(data.get("是否含拟人化元素")),
        是否有渐变色=_optional_string(data.get("是否有渐变色")),
        核心内容=_optional_string(data.get("核心内容")),
        核心内容动态=_optional_string(data.get("核心内容动态")),
        核心内容引申含义=_optional_string(data.get("核心内容引申含义")),
        核心内容形状=_optional_string(data.get("核心内容形状")),
        核心内容类别=_optional_string(data.get("核心内容类别")),
        核心内容颜色=_optional_string(data.get("核心内容颜色")),
        注意力类型=_optional_string(data.get("注意力类型")),
        深度表现=_optional_string(data.get("深度表现")),
        物理引擎=_optional_string(data.get("物理引擎")),
        玩法类型=_optional_string(data.get("玩法类型")),
        环境内容=_optional_string(data.get("环境内容")),
        画面结构=_optional_string(data.get("画面结构")),
        碰撞检测=_optional_string(data.get("碰撞检测")),
        答案唯一性=_optional_string(data.get("答案唯一性")),
        答题反馈=_optional_string(data.get("答题反馈")),
        答题模式=_optional_string(data.get("答题模式")),
        背景时间=_optional_string(data.get("背景时间")),
        背景景别=_optional_string(data.get("背景景别")),
        背景环境=_optional_string(data.get("背景环境")),
        色彩搭配=_optional_string(data.get("色彩搭配")),
        色彩数量控制=_optional_int(data.get("色彩数量控制")),
        色调冷暖=_optional_string(data.get("色调冷暖")),
        艺术风格=_optional_string(data.get("艺术风格")),
        节奏=_optional_string(data.get("节奏")),
        规则理解难度=_optional_int(data.get("规则理解难度")),
        视角=_optional_string(data.get("视角")),
        认知加工深度=_optional_string(data.get("认知加工深度")),
        认知负荷水平=_optional_string(data.get("认知负荷水平")),
        训练所需语言能力=_optional_string(data.get("训练所需语言能力")),
        辅助颜色=_optional_string(data.get("辅助颜色")),
        配色对比度=_optional_string(data.get("配色对比度")),
        错误指导=_optional_string(data.get("错误指导")),
        难度星级=_optional_int(data.get("难度星级")),
        题目包含挑战性语言=_optional_string(data.get("题目包含挑战性语言")),
        题目呈现位置=_optional_string(data.get("题目呈现位置")),
        题目呈现形式=_optional_string(data.get("题目呈现形式")),
        题目复杂度=_optional_string(data.get("题目复杂度")),
        题目是否语音播放=_optional_string(data.get("题目是否语音播放")),
        题目限时=_optional_string(data.get("题目限时")),
        饱和度=_optional_string(data.get("饱和度")),
    )


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


def _optional_int(value: object) -> int | None:
    """Normalize an optional integer value."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value.strip())
        except ValueError:
            return None
    return None


def _optional_float(value: object) -> float | None:
    """Normalize an optional float value."""
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None
