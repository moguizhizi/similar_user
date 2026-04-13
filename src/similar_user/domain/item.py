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
