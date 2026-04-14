"""Rule-based scoring for patient graph paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..domain.path_models import PatientTasksetTaskGameTaskTasksetPatientPath


@dataclass(frozen=True)
class PathScoreBreakdown:
    """Detailed scoring output for one patient path."""

    total_score: float
    education_score: float | None
    age_score: float | None
    completion_score: float | None
    activity_score: float | None
    task_relevance_score: float | None
    used_weights: dict[str, float] = field(default_factory=dict)
    details: dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable mapping for the score breakdown."""
        return {
            "total_score": self.total_score,
            "education_score": self.education_score,
            "age_score": self.age_score,
            "completion_score": self.completion_score,
            "activity_score": self.activity_score,
            "task_relevance_score": self.task_relevance_score,
            "used_weights": self.used_weights,
            "details": self.details,
        }


@dataclass
class PathScorer:
    """Score one patient path using explainable rule-based heuristics."""

    education_weight: float = 0.15
    age_weight: float = 0.20
    completion_weight: float = 0.25
    activity_weight: float = 0.15
    task_relevance_weight: float = 0.25

    EDUCATION_NORMALIZATION = {
        "专科": "大专",
        "研究生": "硕士",
    }

    # 基于当前库中 TaskInstanceSet.执行学历 的实际取值写死排序；
    # 其中“高中以后”按介于“高中/中专”和“大专”之间处理。
    EDUCATION_RANKS = {
        "未上过学": 0,
        "幼儿园": 1,
        "小学1年级": 2,
        "小学2年级": 3,
        "小学3年级": 4,
        "小学4年级": 5,
        "小学5年级": 6,
        "小学6年级": 7,
        "小学": 7,
        "初中1年级": 8,
        "初中2年级": 9,
        "初中3年级": 10,
        "初中": 10,
        "高中": 11,
        "中专": 11,
        "高中以后": 12,
        "大专": 13,
        "本科": 14,
        "硕士": 15,
        "博士": 16,
        "博士后": 17,
    }

    TASK_TYPE_GROUPS = {
        "句子识别": "语言认知",
        "语义判断": "语言认知",
        "词语理解": "语言认知",
        "听觉注意": "注意功能",
        "视觉注意": "注意功能",
        "注意训练": "注意功能",
    }

    def score(
        self,
        path: PatientTasksetTaskGameTaskTasksetPatientPath,
    ) -> PathScoreBreakdown:
        """Score one typed path and return a detailed breakdown."""
        education_score, education_detail = self._score_education(path)
        age_score, age_detail = self._score_age(path)
        completion_score, completion_detail = self._score_completion(path)
        activity_score, activity_detail = self._score_activity(path)
        task_relevance_score, task_relevance_detail = self._score_task_relevance(path)

        scores = {
            "education": education_score,
            "age": age_score,
            "completion": completion_score,
            "activity": activity_score,
            "task_relevance": task_relevance_score,
        }
        weights = {
            "education": self.education_weight,
            "age": self.age_weight,
            "completion": self.completion_weight,
            "activity": self.activity_weight,
            "task_relevance": self.task_relevance_weight,
        }
        active_weights = {
            key: weight for key, weight in weights.items() if scores[key] is not None
        }
        weight_sum = sum(active_weights.values())
        normalized_weights = (
            {key: weight / weight_sum for key, weight in active_weights.items()}
            if weight_sum > 0
            else {}
        )
        total_score = round(
            sum((scores[key] or 0.0) * normalized_weights[key] for key in normalized_weights),
            2,
        )

        return PathScoreBreakdown(
            total_score=total_score,
            education_score=education_score,
            age_score=age_score,
            completion_score=completion_score,
            activity_score=activity_score,
            task_relevance_score=task_relevance_score,
            used_weights={key: round(value, 4) for key, value in normalized_weights.items()},
            details={
                "education": education_detail,
                "age": age_detail,
                "completion": completion_detail,
                "activity": activity_detail,
                "task_relevance": task_relevance_detail,
            },
        )

    def _score_education(
        self,
        path: PatientTasksetTaskGameTaskTasksetPatientPath,
    ) -> tuple[float | None, str]:
        left = self._map_education_rank(path.s1.执行学历)
        right = self._map_education_rank(path.s2.执行学历)
        if left is None or right is None:
            return None, "学历缺失，跳过该项"

        diff = abs(left - right)
        if diff == 0:
            return 100.0, "学历一致"
        if diff == 1:
            return 85.0, "学历相差1级"
        if diff == 2:
            return 65.0, "学历相差2级"
        if diff == 3:
            return 40.0, "学历相差3级"
        return 20.0, "学历差异较大"

    def _score_age(
        self,
        path: PatientTasksetTaskGameTaskTasksetPatientPath,
    ) -> tuple[float | None, str]:
        left = self._parse_int(path.s1.执行年龄)
        right = self._parse_int(path.s2.执行年龄)
        if left is None or right is None:
            return None, "年龄缺失，跳过该项"

        diff = abs(left - right)
        if diff <= 2:
            return 100.0, f"年龄差{diff}岁"
        if diff <= 5:
            return 85.0, f"年龄差{diff}岁"
        if diff <= 10:
            return 70.0, f"年龄差{diff}岁"
        if diff <= 15:
            return 50.0, f"年龄差{diff}岁"
        if diff <= 20:
            return 30.0, f"年龄差{diff}岁"
        return 10.0, f"年龄差{diff}岁"

    def _score_completion(
        self,
        path: PatientTasksetTaskGameTaskTasksetPatientPath,
    ) -> tuple[float | None, str]:
        left = self._normalize_text(path.i1.结果)
        right = self._normalize_text(path.i2.结果)
        if left is None or right is None:
            return None, "i1/i2 结果缺失，跳过该项"
        if left not in {"完成", "未完成"} or right not in {"完成", "未完成"}:
            return None, f"i1结果={left}, i2结果={right}，不在支持范围内，跳过该项"
        if left == right:
            return 100.0, f"i1结果={left}, i2结果={right}"
        return 20.0, f"i1结果={left}, i2结果={right}"

    def _score_activity(
        self,
        path: PatientTasksetTaskGameTaskTasksetPatientPath,
    ) -> tuple[float | None, str]:
        activity = self._normalize_text(path.i2.活跃)
        if activity is None:
            return None, "活跃度缺失，跳过该项"
        if activity == "是":
            return 100.0, f"活跃={activity}"
        if activity == "否":
            return 20.0, f"活跃={activity}"
        return None, f"活跃={activity}，不在支持范围内，跳过该项"

    def _score_task_relevance(
        self,
        path: PatientTasksetTaskGameTaskTasksetPatientPath,
    ) -> tuple[float | None, str]:
        task1 = self._normalize_text(path.i1.任务类型)
        task2 = self._normalize_text(path.i2.任务类型)
        game_task = self._normalize_text(path.g.任务类型)

        if task1 is None and task2 is None and game_task is None:
            return None, "任务类型缺失，跳过该项"
        if task1 is not None and task2 is not None and task1 == task2:
            return 100.0, f"任务类型一致: {task1}"
        if task1 is not None and game_task is not None and task1 == game_task:
            return 80.0, f"当前任务类型与游戏任务类型一致: {task1}"
        if task2 is not None and game_task is not None and task2 == game_task:
            return 80.0, f"相似任务类型与游戏任务类型一致: {task2}"

        group1 = self.TASK_TYPE_GROUPS.get(task1 or "")
        group2 = self.TASK_TYPE_GROUPS.get(task2 or "")
        if group1 is not None and group1 == group2:
            return 70.0, f"任务类型同属{group1}"
        if task1 is not None or task2 is not None or game_task is not None:
            return 30.0, "任务类型不完全匹配"
        return None, "任务类型缺失，跳过该项"

    def _map_education_rank(self, value: str | None) -> int | None:
        normalized = self._normalize_text(value)
        if normalized is None:
            return None
        if normalized == "保密":
            return None
        normalized = self.EDUCATION_NORMALIZATION.get(normalized, normalized)
        return self.EDUCATION_RANKS.get(normalized)

    @staticmethod
    def _normalize_text(value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _parse_int(value: str | None) -> int | None:
        if value is None:
            return None
        digits = "".join(char for char in value if char.isdigit())
        if not digits:
            return None
        return int(digits)

    @staticmethod
    def _parse_float(value: str | None) -> float | None:
        if value is None:
            return None
        try:
            return float(value.strip())
        except ValueError:
            return None

    @staticmethod
    def _clamp(value: float) -> float:
        return max(0.0, min(100.0, round(value, 2)))
