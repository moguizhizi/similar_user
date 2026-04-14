"""Item or behavior node structure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, TypeAlias


EducationValue: TypeAlias = Literal[
    "专科",
    "中专",
    "保密",
    "初中",
    "初中1年级",
    "初中2年级",
    "初中3年级",
    "博士",
    "博士后",
    "大专",
    "小学",
    "小学1年级",
    "小学2年级",
    "小学3年级",
    "小学4年级",
    "小学5年级",
    "小学6年级",
    "幼儿园",
    "未上过学",
    "本科",
    "研究生",
    "高中",
    "高中以后",
]

TASK_INSTANCE_SET_EDUCATION_VALUES: tuple[EducationValue, ...] = (
    "专科",
    "中专",
    "保密",
    "初中",
    "初中1年级",
    "初中2年级",
    "初中3年级",
    "博士",
    "博士后",
    "大专",
    "小学",
    "小学1年级",
    "小学2年级",
    "小学3年级",
    "小学4年级",
    "小学5年级",
    "小学6年级",
    "幼儿园",
    "未上过学",
    "本科",
    "研究生",
    "高中",
    "高中以后",
)

TaskResultValue: TypeAlias = Literal["完成", "未完成"]

TASK_INSTANCE_RESULT_VALUES: tuple[TaskResultValue, ...] = ("完成", "未完成")

TaskActivityValue: TypeAlias = Literal["是", "否"]

TASK_INSTANCE_ACTIVITY_VALUES: tuple[TaskActivityValue, ...] = ("是", "否")

TaskExclusiveTypeValue: TypeAlias = Literal["专属", "自由"]

TASK_INSTANCE_EXCLUSIVE_TYPE_VALUES: tuple[TaskExclusiveTypeValue, ...] = ("专属", "自由")


@dataclass(frozen=True)
class TaskInstanceSetNode:
    """TaskInstanceSet node data used in graph path results."""

    id: str
    name: str | None = None
    训练日期: str | None = None
    执行年龄: str | None = None
    # 基于当前库中 TaskInstanceSet.执行学历 的实际取值收紧字段类型。
    执行学历: EducationValue | None = None


@dataclass(frozen=True)
class TaskInstanceNode:
    """TaskInstance node data used in graph path results."""

    id: str
    name: str | None = None
    得分: str | None = None
    常模分: str | None = None
    # 基于当前路径评分逻辑收紧为固定结果取值。
    结果: TaskResultValue | None = None
    # 基于当前业务约束收紧为固定活跃取值。
    活跃: TaskActivityValue | None = None
    # 当前仓库中的该字段用于表达“专属/自由”两类取值。
    任务类型: TaskExclusiveTypeValue | None = None
    状态: str | None = None


@dataclass(frozen=True)
class GameNode:
    """Game node data used in graph path results."""

    id: str
    name: str | None = None
    UI边框样式: str | None = None
    主要颜色: str | None = None
    交互对象: str | None = None
    交互按钮类型: str | None = None
    任务动机: str | None = None
    任务类型: str | None = None
    任务阶段划分: str | None = None
    体验情景: str | None = None
    信息复杂度: str | None = None
    元素大小: str | None = None
    元素密度: str | None = None
    内部负荷: str | None = None
    出题方式: str | None = None
    叙事性强度: str | None = None
    同屏spine数量上限: float | None = None
    图像细节丰富度: str | None = None
    图形符号化程度: str | None = None
    地域: str | None = None
    场景拟真度: str | None = None
    外部负荷: str | None = None
    宏观题材分类: str | None = None
    年代: str | None = None
    思维类型: str | None = None
    情感氛围: str | None = None
    情绪色彩倾向: str | None = None
    感知类型: str | None = None
    指示明确性: str | None = None
    操作方式: str | None = None
    操作频率: str | None = None
    整体环境风格: str | None = None
    是否含拟人化元素: str | None = None
    是否有渐变色: str | None = None
    核心内容: str | None = None
    核心内容动态: str | None = None
    核心内容引申含义: str | None = None
    核心内容形状: str | None = None
    核心内容类别: str | None = None
    核心内容颜色: str | None = None
    注意力类型: str | None = None
    深度表现: str | None = None
    物理引擎: str | None = None
    玩法类型: str | None = None
    环境内容: str | None = None
    画面结构: str | None = None
    碰撞检测: str | None = None
    答案唯一性: str | None = None
    答题反馈: str | None = None
    答题模式: str | None = None
    背景时间: str | None = None
    背景景别: str | None = None
    背景环境: str | None = None
    色彩搭配: str | None = None
    色彩数量控制: int | None = None
    色调冷暖: str | None = None
    艺术风格: str | None = None
    节奏: str | None = None
    规则理解难度: int | None = None
    视角: str | None = None
    认知加工深度: str | None = None
    认知负荷水平: str | None = None
    训练所需语言能力: str | None = None
    辅助颜色: str | None = None
    配色对比度: str | None = None
    错误指导: str | None = None
    难度星级: int | None = None
    题目包含挑战性语言: str | None = None
    题目呈现位置: str | None = None
    题目呈现形式: str | None = None
    题目复杂度: str | None = None
    题目是否语音播放: str | None = None
    题目限时: str | None = None
    饱和度: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameNode:
        """Build a game node from raw JSON content."""
        return cls(
            id=_require_string(data.get("id"), "g.id"),
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
