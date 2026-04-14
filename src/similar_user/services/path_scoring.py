"""Rule-based scoring for patient graph paths."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..domain.item import GameNode
from ..domain.path_models import PatientTasksetTaskGameTaskTasksetPatientPath


@dataclass(frozen=True)
class PathScoreBreakdown:
    """Detailed scoring output for one patient path."""

    total_score: float
    education_score: float | None
    age_score: float | None
    completion_score: float | None
    activity_score: float | None
    task_type_score: float | None
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
            "task_type_score": self.task_type_score,
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
    task_type_weight: float = 0.10
    task_relevance_weight: float = 0.15

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

    def score(
        self,
        path: PatientTasksetTaskGameTaskTasksetPatientPath,
    ) -> PathScoreBreakdown:
        """Score one typed path and return a detailed breakdown."""
        education_score, education_detail = self._score_education(path)
        age_score, age_detail = self._score_age(path)
        completion_score, completion_detail = self._score_completion(path)
        activity_score, activity_detail = self._score_activity(path)
        task_type_score, task_type_detail = self._score_task_type(path)
        task_relevance_score, task_relevance_detail = self._score_task_relevance(path)

        scores = {
            "education": education_score,
            "age": age_score,
            "completion": completion_score,
            "activity": activity_score,
            "task_type": task_type_score,
            "task_relevance": task_relevance_score,
        }
        weights = {
            "education": self.education_weight,
            "age": self.age_weight,
            "completion": self.completion_weight,
            "activity": self.activity_weight,
            "task_type": self.task_type_weight,
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
            task_type_score=task_type_score,
            task_relevance_score=task_relevance_score,
            used_weights={key: round(value, 4) for key, value in normalized_weights.items()},
            details={
                "education": education_detail,
                "age": age_detail,
                "completion": completion_detail,
                "activity": activity_detail,
                "task_type": task_type_detail,
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

    def _score_task_type(
        self,
        path: PatientTasksetTaskGameTaskTasksetPatientPath,
    ) -> tuple[float | None, str]:
        task1 = self._normalize_text(path.i1.任务类型)
        task2 = self._normalize_text(path.i2.任务类型)
        if task1 is None or task2 is None:
            return None, "任务类型缺失，跳过该项"
        if task1 == task2:
            return 100.0, f"专属类型一致: {task1}"
        return 30.0, f"专属类型不一致: {task1}/{task2}"

    def _score_task_relevance(
        self,
        path: PatientTasksetTaskGameTaskTasksetPatientPath,
    ) -> tuple[float | None, str]:
        games = self._extract_games_for_relevance(path)
        if len(games) < 2:
            return None, "当前path上不足两个g，无法计算两个g之间的相关度，跳过该项"

        left_game, right_game = games[0], games[1]
        left_task_type = self._normalize_text(left_game.任务类型)
        right_task_type = self._normalize_text(right_game.任务类型)
        if left_task_type is None or right_task_type is None:
            return None, "game任务类型缺失，无法计算两个g之间的相关度，跳过该项"
        if left_task_type == right_task_type:
            return 100.0, f"两个g的任务类型一致: {left_task_type}"
        return 30.0, f"两个g的任务类型不一致: {left_task_type}/{right_task_type}"

    @staticmethod
    def _extract_games_for_relevance(
        path: PatientTasksetTaskGameTaskTasksetPatientPath,
    ) -> list[GameNode]:
        games: list[GameNode] = []
        for attr_name in ("g1", "g2", "g"):
            value = getattr(path, attr_name, None)
            if isinstance(value, GameNode):
                games.append(value)
        return games

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
        normalized = value.strip()
        if not normalized:
            return None
        try:
            return int(float(normalized))
        except ValueError:
            return None

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
