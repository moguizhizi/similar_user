"""Training-task prediction helpers driven by similar-user candidates."""

from __future__ import annotations

import ast
import csv
import json
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

from .llm_client import LlmClient
from .user_service import UserService
from ..utils.logger import get_logger


LOGGER = get_logger(__name__)
DEFAULT_TASK_TOP_K = 7
PROMPT_OVERALL_TOP_N = 30
PROMPT_HIGH_SCORE_USER_COUNT = 5
PROMPT_PER_HIGH_SCORE_USER_TOP_K = 5
PROMPT_MAX_CANDIDATES = 50

SYSTEM_PROMPT = """
你是训练任务预测助手。你只能基于输入中的目标用户历史、相似用户历史和候选训练任务进行预测。
不要做医学诊断，不要输出候选任务之外的任务。请返回合法 JSON。
""".strip()

TASK_PREDICTION_PROMPT_TEMPLATE_V1 = (
    "请根据以下 JSON 数据预测目标用户下一阶段更可能适合的训练任务。"
    "字段含义：candidate_training_tasks 是唯一允许选择的候选任务池；"
    "similar_user_game_counts 是相似用户时间窗口内各任务出现的总次数；"
    "candidate_score 越大表示该候选用户与目标用户越相似。"
    "请结合相似用户任务总次数和候选任务池进行排序。"
    "只允许从 candidate_training_tasks 中选择，返回 JSON 对象，不要添加 Markdown。\n\n"
)

TASK_PREDICTION_PROMPT_TEMPLATE_V2 = (
    "请根据以下 JSON 数据预测目标用户下一阶段更可能适合的训练任务。"
    "字段含义：candidate_training_tasks 是唯一允许选择的候选任务池；"
    "similar_user_game_counts 是相似用户时间窗口内各任务出现的总次数；"
    "similar_user_candidates 是候选相似用户及其相似度分数；"
    "similar_user_task_evidence 是按候选相似用户拆分的任务证据；"
    "candidate_score 越大表示该候选用户与目标用户越相似。"
    "请综合总体出现次数和高相似用户证据，不要只按 similar_user_game_counts 的总次数排名选择。"
    "如果某任务总体次数中等，但由 candidate_score 较高的相似用户反复支持，也应考虑推荐。"
    "推荐结果应兼顾高频任务和中等频次但证据质量高的任务。"
    "只允许从 candidate_training_tasks 中选择，不要重复 game_id。"
    "必须返回 output_requirement.top_k 个任务；如果候选任务不足 top_k，则返回全部候选任务。"
    "返回 JSON 对象，不要添加 Markdown。\n\n"
)

TASK_PREDICTION_PROMPT_TEMPLATE_V3 = (
    "请根据以下 JSON 数据预测目标用户下一阶段更可能适合的训练任务。"
    "字段含义：candidate_training_tasks 是唯一允许选择的候选任务池；"
    "similar_user_game_counts 是相似用户时间窗口内各任务出现的汇总证据，"
    "其中 count 是原始出现次数；"
    "weighted_count 是按相似用户分数归一权重加权后的出现强度，"
    "最高相似用户一次出现贡献 1.0，低相似用户按比例折扣；"
    "supporting_user_count 是做过该任务的不同相似用户人数；"
    "avg_support_score 是支持该任务的相似用户平均归一权重；"
    "max_support_score 是支持该任务的相似用户最高归一权重。"
    "candidate_score 越大表示该候选用户与目标用户越相似。"
    "推荐时不要只看 count；如果 count 高但 weighted_count 明显偏低，说明主要由低相似用户贡献，应降低优先级。"
    "如果 count 中等但 weighted_count、avg_support_score 或 max_support_score 较高，说明该任务有高质量相似用户证据，可以优先考虑。"
    "推荐结果应兼顾高频任务和中等频次但证据质量高的任务。"
    "只允许从 candidate_training_tasks 中选择，不要重复 game_id。"
    "必须返回 output_requirement.top_k 个任务；如果候选任务不足 top_k，则返回全部候选任务。"
    "返回 JSON 对象，不要添加 Markdown。\n\n"
)

TASK_PREDICTION_PROMPT_TEMPLATE_DIRECT_ENTITY_V1 = (
    "请根据以下 JSON 数据，为一个不一定存在于知识图谱中的目标用户预测下一阶段更可能适合的训练任务。"
    "字段含义：target_profile 是目标用户画像；target_entities 是目标用户输入的疾病、症状、未知实体；"
    "candidate_training_tasks 是唯一允许选择的候选任务池；"
    "similar_user_candidates 是通过 direct entity paths 匹配出的候选相似用户及其相似度分数；"
    "similar_user_game_counts 是这些候选相似用户在时间窗口内的训练任务汇总；"
    "similar_user_task_evidence 是按候选相似用户拆分的任务证据；"
    "candidate_score 越大表示该候选用户与目标画像和实体越相似。"
    "目标用户可能不是 KG 中已有患者，不要假设存在目标用户历史训练记录。"
    "请综合总体出现次数和高相似用户证据，不要只按 similar_user_game_counts 的总次数排名选择。"
    "只允许从 candidate_training_tasks 中选择，不要重复 game_id。"
    "必须返回 output_requirement.top_k 个任务；如果候选任务不足 top_k，则返回全部候选任务。"
    "返回 JSON 对象，不要添加 Markdown。\n\n"
)

CURRENT_TASK_PREDICTION_PROMPT_TEMPLATE_NAME = "TASK_PREDICTION_PROMPT_TEMPLATE_V2"
CURRENT_TASK_PREDICTION_PROMPT_TEMPLATE = TASK_PREDICTION_PROMPT_TEMPLATE_V2
TASK_PREDICTION_PROMPT_TEMPLATES = {
    "TASK_PREDICTION_PROMPT_TEMPLATE_V1": TASK_PREDICTION_PROMPT_TEMPLATE_V1,
    "TASK_PREDICTION_PROMPT_TEMPLATE_V2": TASK_PREDICTION_PROMPT_TEMPLATE_V2,
    "TASK_PREDICTION_PROMPT_TEMPLATE_V3": TASK_PREDICTION_PROMPT_TEMPLATE_V3,
    "TASK_PREDICTION_PROMPT_TEMPLATE_DIRECT_ENTITY_V1": (
        TASK_PREDICTION_PROMPT_TEMPLATE_DIRECT_ENTITY_V1
    ),
}
WEIGHTED_GAME_COUNTS_PROMPT_TEMPLATE_NAME = "TASK_PREDICTION_PROMPT_TEMPLATE_V3"


@dataclass(frozen=True)
class SimilarUserCandidate:
    """Similar-user candidate parsed from run_similar_user_pipeline.py output."""

    patient_id: str
    candidate_score: float | None = None
    candidate_base_date: str | None = None

    @property
    def weight(self) -> float:
        if self.candidate_score is None or self.candidate_score <= 0:
            return 1.0
        return self.candidate_score


@dataclass
class TrainingTaskPredictionService:
    """Build task-prediction context and optionally ask an LLM to rank tasks."""

    user_service: UserService
    llm_client: LlmClient | None = None
    prompt_candidate_compression_enabled: bool = True
    prompt_template_name: str = CURRENT_TASK_PREDICTION_PROMPT_TEMPLATE_NAME
    profile_candidate_training_window_days: int | None = None
    unlock_train_candidate_tasks_enabled: bool = False
    algorithm_request_results_csv: str | None = None
    similar_user_game_counts_weighting_enabled: bool = False
    similar_user_game_counts_weighted_sort_enabled: bool = False

    def __post_init__(self) -> None:
        validate_prompt_weighting_compatibility(
            self.prompt_template_name,
            self.similar_user_game_counts_weighting_enabled,
        )

    def predict_from_pipeline_result(
        self,
        pipeline_result: dict[str, Any],
        *,
        base_date: str,
        window_days: int,
        task_top_k: int = DEFAULT_TASK_TOP_K,
        use_llm: bool = True,
        include_prompt: bool = False,
    ) -> dict[str, Any]:
        """Predict next training tasks from a similar-user pipeline result."""
        resolved_patient_id = self._resolve_patient_id(pipeline_result)
        target_task_window = build_target_task_window(base_date)
        candidates = extract_similar_user_candidates(pipeline_result)
        if not candidates:
            raise ValueError("similar user pipeline output does not contain candidates.")

        target_history = self.user_service.get_patient_training_task_history_by_date_window(
            resolved_patient_id,
            target_task_window["start_date"],
            target_task_window["end_date"],
        )
        candidate_task_windows = {
            candidate.patient_id: build_candidate_task_window(
                candidate.candidate_base_date or base_date,
                window_days,
            )
            for candidate in candidates
        }
        similar_user_histories = {
            candidate.patient_id: self.user_service.get_patient_exclusive_training_task_history_by_date_window(
                candidate.patient_id,
                candidate_task_windows[candidate.patient_id]["start_date"],
                candidate_task_windows[candidate.patient_id]["end_date"],
            )
            for candidate in candidates
        }

        candidate_source_type = "patient_profile_entities"
        candidate_tasks = self._build_unlock_train_candidate_tasks(
            resolved_patient_id
        )
        if candidate_tasks:
            candidate_source_type = "unlock_train"
        else:
            profile_candidate_game_rows = (
                self.user_service.get_patient_profile_candidate_training_games(
                    resolved_patient_id,
                    target_task_window["base_date"],
                    profile_candidate_training_window_days=(
                        self.profile_candidate_training_window_days
                    ),
                )
            )
            if not isinstance(profile_candidate_game_rows, list):
                profile_candidate_game_rows = []
            candidate_tasks = build_candidate_training_tasks_from_distinct_games(
                profile_candidate_game_rows
            )
        if not candidate_tasks:
            profile_candidate_game_rows = self.user_service.get_distinct_training_games()
            candidate_source_type = "distinct_training_games_fallback"
            candidate_tasks = build_candidate_training_tasks_from_distinct_games(
                profile_candidate_game_rows
            )

        repeated_target_game_ids = find_consecutive_target_game_ids(target_history)
        allowed_candidate_game_ids = _extract_candidate_task_game_ids(candidate_tasks)
        similar_user_game_counts = build_similar_user_game_counts(
            candidates,
            similar_user_histories,
            weighting_enabled=self.similar_user_game_counts_weighting_enabled,
            weighted_sort_enabled=self.similar_user_game_counts_weighted_sort_enabled,
        )
        similar_user_game_counts = filter_game_counts_by_ids(
            similar_user_game_counts,
            repeated_target_game_ids,
        )
        similar_user_game_counts = filter_game_counts_to_ids(
            similar_user_game_counts,
            allowed_candidate_game_ids,
        )

        similar_user_task_evidence = build_similar_user_task_evidence(
            candidates,
            similar_user_histories,
            excluded_game_ids=repeated_target_game_ids,
        )
        similar_user_task_evidence = filter_task_evidence_to_ids(
            similar_user_task_evidence,
            allowed_candidate_game_ids,
        )
        if self.prompt_candidate_compression_enabled:
            prompt_candidate_game_ids = select_prompt_candidate_game_ids(
                similar_user_game_counts,
                similar_user_task_evidence,
                overall_top_n=PROMPT_OVERALL_TOP_N,
                high_score_user_count=PROMPT_HIGH_SCORE_USER_COUNT,
                per_high_score_user_top_k=PROMPT_PER_HIGH_SCORE_USER_TOP_K,
                max_prompt_candidates=PROMPT_MAX_CANDIDATES,
            )
            prompt_similar_user_game_counts = filter_game_counts_to_ids(
                similar_user_game_counts,
                prompt_candidate_game_ids,
            )
            prompt_similar_user_task_evidence = filter_task_evidence_to_ids(
                similar_user_task_evidence,
                prompt_candidate_game_ids,
            )
            prompt_candidate_tasks = filter_candidate_tasks_to_ids(
                candidate_tasks,
                prompt_candidate_game_ids,
            )
            if not prompt_candidate_tasks and candidate_tasks:
                prompt_candidate_game_ids = set(allowed_candidate_game_ids)
                prompt_similar_user_game_counts = similar_user_game_counts
                prompt_similar_user_task_evidence = similar_user_task_evidence
                prompt_candidate_tasks = candidate_tasks
        else:
            prompt_candidate_game_ids = set(allowed_candidate_game_ids)
            prompt_similar_user_game_counts = similar_user_game_counts
            prompt_similar_user_task_evidence = similar_user_task_evidence
            prompt_candidate_tasks = candidate_tasks
        prompt_candidate_selection = {
            "enabled": self.prompt_candidate_compression_enabled,
            "overall_top_n": PROMPT_OVERALL_TOP_N,
            "high_score_user_count": PROMPT_HIGH_SCORE_USER_COUNT,
            "per_high_score_user_top_k": PROMPT_PER_HIGH_SCORE_USER_TOP_K,
            "max_prompt_candidates": PROMPT_MAX_CANDIDATES,
            "selected_candidate_count": len(prompt_candidate_game_ids),
            "source_similar_user_game_count": len(similar_user_game_counts),
            "source_candidate_task_count": len(candidate_tasks),
            "similar_user_game_counts_weighting_enabled": (
                self.similar_user_game_counts_weighting_enabled
            ),
            "similar_user_game_counts_weighted_sort_enabled": (
                self.similar_user_game_counts_weighted_sort_enabled
            ),
        }

        rule_based_tasks = build_rule_based_predictions(
            prompt_candidate_tasks,
            top_k=task_top_k,
        )
        prompt = build_task_prediction_prompt(
            patient_id=resolved_patient_id,
            similar_user_candidates=build_prompt_similar_user_candidates(candidates),
            similar_user_task_evidence=prompt_similar_user_task_evidence,
            similar_user_game_counts=prompt_similar_user_game_counts,
            candidate_training_tasks=prompt_candidate_tasks,
            task_top_k=task_top_k,
            prompt_template_name=self.prompt_template_name,
        )

        llm_prediction: dict[str, Any] | None = None
        raw_llm_output: str | None = None
        if use_llm:
            if self.llm_client is None:
                raise ValueError("llm_client is required when use_llm is true.")
            try:
                raw_llm_output = self.llm_client.chat(
                    prompt,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=0.2,
                )
                llm_prediction = parse_json_object_from_text(raw_llm_output)
            except Exception as exc:
                setattr(exc, "llm_prompt", prompt)
                setattr(exc, "patient_id", resolved_patient_id)
                raise

        result: dict[str, Any] = {
            "patient_id": resolved_patient_id,
            "candidate_source": {
                "source": "run_similar_user_pipeline.py",
                "candidate_count": len(candidates),
                "candidate_ids": [candidate.patient_id for candidate in candidates],
                "has_candidate_scores": any(
                    candidate.candidate_score is not None for candidate in candidates
                ),
                "candidate_task_windows": candidate_task_windows,
                "candidate_task_source": candidate_source_type,
            },
            "prompt_candidate_selection": prompt_candidate_selection,
            "similar_user_game_counts": prompt_similar_user_game_counts,
            "similar_user_task_evidence": prompt_similar_user_task_evidence,
            "candidate_training_tasks": prompt_candidate_tasks,
            "prompt_template": self.prompt_template_name,
            "predicted_training_tasks": _resolve_predicted_tasks(
                llm_prediction,
                rule_based_tasks,
            ),
            "llm_prediction": llm_prediction,
        }
        if include_prompt:
            result["llm_prompt"] = prompt
        if raw_llm_output is not None:
            result["raw_llm_output"] = raw_llm_output

        LOGGER.info(
            "Built training-task prediction: patient_id=%s, candidate_count=%s, predicted_task_count=%s, used_llm=%s",
            resolved_patient_id,
            len(candidates),
            len(result["predicted_training_tasks"]),
            use_llm,
        )
        return result

    def _build_unlock_train_candidate_tasks(self, patient_id: str) -> list[dict[str, Any]]:
        """Build candidate tasks from algorithm CSV unlock_train keys when enabled."""
        if not self.unlock_train_candidate_tasks_enabled:
            return []
        csv_path = (
            self.algorithm_request_results_csv.strip()
            if isinstance(self.algorithm_request_results_csv, str)
            else ""
        )
        if not csv_path:
            LOGGER.warning(
                "Skipped unlock_train candidate tasks because CSV path is empty: patient_id=%s",
                patient_id,
            )
            return []
        try:
            return load_unlock_train_candidate_tasks(csv_path, patient_id)
        except Exception as exc:
            LOGGER.warning(
                "Failed to load unlock_train candidate tasks: patient_id=%s, csv_path=%s, error=%s",
                patient_id,
                csv_path,
                exc,
            )
            return []

    def predict_from_direct_entity_candidates(
        self,
        *,
        patient_id: str,
        candidate_result: dict[str, Any],
        base_date: str,
        window_days: int,
        target_profile: dict[str, Any] | None = None,
        target_entities: dict[str, Any] | None = None,
        task_top_k: int = DEFAULT_TASK_TOP_K,
        use_llm: bool = True,
        include_prompt: bool = False,
    ) -> dict[str, Any]:
        """Predict tasks from direct-entity candidate users without source-patient history."""
        resolved_patient_id = str(patient_id or "").strip()
        if not resolved_patient_id:
            raise ValueError("patient_id is required for direct entity task prediction.")
        candidates = _extract_direct_entity_candidates(candidate_result)
        if not candidates:
            raise ValueError("direct entity candidate result does not contain candidates.")

        candidate_task_windows = {
            candidate.patient_id: build_candidate_task_window(base_date, window_days)
            for candidate in candidates
        }
        similar_user_histories = {
            candidate.patient_id: self.user_service.get_patient_exclusive_training_task_history_by_date_window(
                candidate.patient_id,
                candidate_task_windows[candidate.patient_id]["start_date"],
                candidate_task_windows[candidate.patient_id]["end_date"],
            )
            for candidate in candidates
        }
        LOGGER.info(
            "Loaded direct entity candidate histories: patient_id=%s, candidate_count=%s, history_row_count=%s, window_days=%s",
            resolved_patient_id,
            len(candidates),
            sum(len(rows) for rows in similar_user_histories.values()),
            window_days,
        )
        candidate_tasks = build_candidate_training_tasks(
            candidates,
            similar_user_histories,
            top_k=max(task_top_k, PROMPT_MAX_CANDIDATES),
        )
        LOGGER.info(
            "Built direct entity task evidence: patient_id=%s, candidate_task_count=%s, task_top_k=%s",
            resolved_patient_id,
            len(candidate_tasks),
            task_top_k,
        )
        allowed_candidate_game_ids = _extract_candidate_task_game_ids(candidate_tasks)
        similar_user_game_counts = build_similar_user_game_counts(
            candidates,
            similar_user_histories,
            weighting_enabled=self.similar_user_game_counts_weighting_enabled,
            weighted_sort_enabled=self.similar_user_game_counts_weighted_sort_enabled,
        )
        similar_user_game_counts = filter_game_counts_to_ids(
            similar_user_game_counts,
            allowed_candidate_game_ids,
        )
        similar_user_task_evidence = build_similar_user_task_evidence(
            candidates,
            similar_user_histories,
        )
        similar_user_task_evidence = filter_task_evidence_to_ids(
            similar_user_task_evidence,
            allowed_candidate_game_ids,
        )
        if self.prompt_candidate_compression_enabled:
            prompt_candidate_game_ids = select_prompt_candidate_game_ids(
                similar_user_game_counts,
                similar_user_task_evidence,
                overall_top_n=PROMPT_OVERALL_TOP_N,
                high_score_user_count=PROMPT_HIGH_SCORE_USER_COUNT,
                per_high_score_user_top_k=PROMPT_PER_HIGH_SCORE_USER_TOP_K,
                max_prompt_candidates=PROMPT_MAX_CANDIDATES,
            )
            prompt_similar_user_game_counts = filter_game_counts_to_ids(
                similar_user_game_counts,
                prompt_candidate_game_ids,
            )
            prompt_similar_user_task_evidence = filter_task_evidence_to_ids(
                similar_user_task_evidence,
                prompt_candidate_game_ids,
            )
            prompt_candidate_tasks = filter_candidate_tasks_to_ids(
                candidate_tasks,
                prompt_candidate_game_ids,
            )
            if not prompt_candidate_tasks and candidate_tasks:
                prompt_candidate_game_ids = set(allowed_candidate_game_ids)
                prompt_similar_user_game_counts = similar_user_game_counts
                prompt_similar_user_task_evidence = similar_user_task_evidence
                prompt_candidate_tasks = candidate_tasks
        else:
            prompt_candidate_game_ids = set(allowed_candidate_game_ids)
            prompt_similar_user_game_counts = similar_user_game_counts
            prompt_similar_user_task_evidence = similar_user_task_evidence
            prompt_candidate_tasks = candidate_tasks

        rule_based_tasks = build_rule_based_predictions(
            prompt_candidate_tasks,
            top_k=task_top_k,
        )
        prompt = build_task_prediction_prompt(
            patient_id=resolved_patient_id,
            target_profile=target_profile,
            target_entities=target_entities,
            candidate_source="direct_entity_paths",
            similar_user_candidates=build_prompt_similar_user_candidates(candidates),
            similar_user_task_evidence=prompt_similar_user_task_evidence,
            similar_user_game_counts=prompt_similar_user_game_counts,
            candidate_training_tasks=prompt_candidate_tasks,
            task_top_k=task_top_k,
            prompt_template_name=self.prompt_template_name,
        )

        llm_prediction: dict[str, Any] | None = None
        raw_llm_output: str | None = None
        if use_llm:
            if self.llm_client is None:
                raise ValueError("llm_client is required when use_llm is true.")
            try:
                raw_llm_output = self.llm_client.chat(
                    prompt,
                    system_prompt=SYSTEM_PROMPT,
                    temperature=0.2,
                )
                llm_prediction = parse_json_object_from_text(raw_llm_output)
            except Exception as exc:
                setattr(exc, "llm_prompt", prompt)
                setattr(exc, "patient_id", resolved_patient_id)
                raise

        result: dict[str, Any] = {
            "patient_id": resolved_patient_id,
            "candidate_source": {
                "source": "direct_entity_paths",
                "candidate_count": len(candidates),
                "candidate_ids": [candidate.patient_id for candidate in candidates],
                "candidate_task_windows": candidate_task_windows,
            },
            "target_profile": target_profile or {},
            "target_entities": target_entities or {},
            "prompt_candidate_selection": {
                "enabled": self.prompt_candidate_compression_enabled,
                "selected_candidate_count": len(prompt_candidate_game_ids),
                "source_similar_user_game_count": len(similar_user_game_counts),
                "source_candidate_task_count": len(candidate_tasks),
                "similar_user_game_counts_weighting_enabled": (
                    self.similar_user_game_counts_weighting_enabled
                ),
                "similar_user_game_counts_weighted_sort_enabled": (
                    self.similar_user_game_counts_weighted_sort_enabled
                ),
            },
            "similar_user_game_counts": prompt_similar_user_game_counts,
            "similar_user_task_evidence": prompt_similar_user_task_evidence,
            "candidate_training_tasks": prompt_candidate_tasks,
            "prompt_template": self.prompt_template_name,
            "predicted_training_tasks": _resolve_predicted_tasks(
                llm_prediction,
                rule_based_tasks,
            ),
            "llm_prediction": llm_prediction,
        }
        if include_prompt:
            result["llm_prompt"] = prompt
        if raw_llm_output is not None:
            result["raw_llm_output"] = raw_llm_output
        LOGGER.info(
            "Built direct entity training-task prediction: patient_id=%s, candidate_count=%s, predicted_task_count=%s, used_llm=%s",
            resolved_patient_id,
            len(candidates),
            len(result["predicted_training_tasks"]),
            use_llm,
        )
        return result

    @staticmethod
    def _resolve_patient_id(pipeline_result: dict[str, Any]) -> str:
        raw_patient_id = pipeline_result.get("patient_id")
        if raw_patient_id is None:
            candidate_result = pipeline_result.get("candidate_result")
            if isinstance(candidate_result, dict):
                raw_patient_id = candidate_result.get("patient_id")
        if raw_patient_id is None:
            candidate_summary = pipeline_result.get("candidate_summary")
            if isinstance(candidate_summary, dict):
                raw_patient_id = candidate_summary.get("patient_id")

        resolved_patient_id = str(raw_patient_id or "").strip()
        if not resolved_patient_id:
            raise ValueError(
                "patient_id is required in run_similar_user_pipeline.py output."
            )
        return resolved_patient_id


def extract_similar_user_candidates(
    pipeline_result: dict[str, Any],
) -> list[SimilarUserCandidate]:
    """Extract candidate users from ids, scores, or full pipeline output."""
    raw_candidates = _find_raw_candidate_items(pipeline_result)
    candidates: list[SimilarUserCandidate] = []
    seen_patient_ids: set[str] = set()
    for raw_candidate in raw_candidates:
        candidate = _parse_candidate(raw_candidate)
        if candidate is None or candidate.patient_id in seen_patient_ids:
            continue
        candidates.append(candidate)
        seen_patient_ids.add(candidate.patient_id)
    return candidates


def _extract_direct_entity_candidates(
    candidate_result: dict[str, Any],
) -> list[SimilarUserCandidate]:
    raw_candidates = candidate_result.get("candidates")
    if not isinstance(raw_candidates, list):
        return []
    candidates: list[SimilarUserCandidate] = []
    seen_patient_ids: set[str] = set()
    for raw_candidate in raw_candidates:
        candidate = _parse_candidate(raw_candidate)
        if candidate is None or candidate.patient_id in seen_patient_ids:
            continue
        candidates.append(candidate)
        seen_patient_ids.add(candidate.patient_id)
    return candidates


def parse_json_object_from_text(text: str) -> dict[str, Any]:
    """Parse a JSON object from plain JSON or logger-prefixed output."""
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text must be a non-empty string.")
    stripped = text.strip()
    try:
        value = json.loads(stripped)
    except json.JSONDecodeError:
        value = _parse_first_valid_json_object(stripped)
    if not isinstance(value, dict):
        raise ValueError("JSON payload must be an object.")
    return value


def build_target_task_window(base_date: str) -> dict[str, Any]:
    """Build the target task window: [base_date - 2 days, base_date)."""
    parsed_base_date = parse_date_value(base_date, "base_date")
    start_date = parsed_base_date - timedelta(days=2)
    return {
        "base_date": parsed_base_date.isoformat(),
        "start_date": start_date.isoformat(),
        "end_date": parsed_base_date.isoformat(),
        "includes_base_date": False,
        "range_semantics": "[start_date, end_date)",
    }


def build_candidate_task_window(base_date: str, window_days: int) -> dict[str, Any]:
    """Build the candidate task window: [base_date - window_days, base_date)."""
    parsed_base_date = parse_date_value(base_date, "base_date")
    if (
        not isinstance(window_days, int)
        or isinstance(window_days, bool)
        or window_days <= 0
    ):
        raise ValueError(f"window_days must be a positive integer, got {window_days}.")
    start_date = parsed_base_date - timedelta(days=window_days)
    return {
        "base_date": parsed_base_date.isoformat(),
        "start_date": start_date.isoformat(),
        "end_date": parsed_base_date.isoformat(),
        "window_days": window_days,
        "includes_base_date": False,
        "range_semantics": "[start_date, end_date)",
    }


def parse_date_value(value: str, field_name: str) -> date:
    """Parse yyyy-mm-dd or yyyy-m-d style dates."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty date string.")
    parts = value.strip().split("-")
    if len(parts) != 3:
        raise ValueError(f"{field_name} must use yyyy-mm-dd format.")
    try:
        year, month, day = (int(part) for part in parts)
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid date.") from exc


def summarize_training_history(
    patient_id: str,
    history_rows: list[dict[str, Any]],
    *,
    top_k: int = 5,
    task_window: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a compact task-history summary suitable for prompt input."""
    normalized_patient_id = patient_id.strip()
    game_counts: dict[str, dict[str, Any]] = {}
    ordered_dates: list[str] = []
    recent_games: list[dict[str, Any]] = []

    for row in history_rows:
        training_date = _normalize_text(row.get("trainingDate"))
        if training_date is not None:
            ordered_dates.append(training_date)
        game = _normalize_node(row.get("g"))
        game_id = _normalize_text(game.get("id")) or _normalize_text(game.get("name"))
        if game_id is None:
            continue
        entry = game_counts.setdefault(
            game_id,
            {
                "game_id": game_id,
                "game_name": _normalize_text(game.get("name")),
                "task_type": _normalize_text(game.get("任务类型")),
                "count": 0,
            },
        )
        entry["count"] += 1
        recent_games.append(
            {
                "training_date": training_date,
                "game_id": game_id,
                "game_name": entry["game_name"],
                "task_type": entry["task_type"],
            }
        )

    frequent_games = sorted(
        game_counts.values(),
        key=lambda item: (-int(item["count"]), str(item["game_id"])),
    )[:top_k]

    summary = {
        "patient_id": normalized_patient_id,
        "row_count": len(history_rows),
        "training_date_count": len(set(ordered_dates)),
        "first_training_date": min(ordered_dates) if ordered_dates else None,
        "last_training_date": max(ordered_dates) if ordered_dates else None,
        "frequent_games": frequent_games,
        "recent_games": _dedupe_recent_games(recent_games, top_k=top_k),
    }
    if task_window is not None:
        summary["task_window"] = task_window
    return summary


def build_candidate_training_tasks(
    candidates: list[SimilarUserCandidate],
    similar_user_histories: dict[str, list[dict[str, Any]]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    """Aggregate weighted task candidates from similar-user histories."""
    task_index: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        rows = similar_user_histories.get(candidate.patient_id, [])
        for row in rows:
            game = _normalize_node(row.get("g"))
            game_id = _normalize_text(game.get("id")) or _normalize_text(
                game.get("name")
            )
            if game_id is None:
                continue
            item = task_index.setdefault(
                game_id,
                {
                    "game_id": game_id,
                    "game_name": _normalize_text(game.get("name")),
                    "task_type": _normalize_text(game.get("任务类型")),
                    "appearance_count": 0,
                    "weighted_score": 0.0,
                    "supporting_candidate_ids": [],
                },
            )
            item["appearance_count"] += 1
            item["weighted_score"] += candidate.weight
            if candidate.patient_id not in item["supporting_candidate_ids"]:
                item["supporting_candidate_ids"].append(candidate.patient_id)

    tasks = sorted(
        task_index.values(),
        key=lambda item: (
            -float(item["weighted_score"]),
            -int(item["appearance_count"]),
            str(item["game_id"]),
        ),
    )[:top_k]
    for task in tasks:
        task["weighted_score"] = round(float(task["weighted_score"]), 4)
    return tasks


def build_candidate_training_tasks_from_distinct_games(
    game_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build the full candidate task pool from distinct training games."""
    tasks: list[dict[str, Any]] = []
    seen_game_ids: set[str] = set()
    for row in game_rows:
        game = _normalize_node(row.get("g"))
        game_id = _normalize_text(game.get("id")) or _normalize_text(game.get("name"))
        if game_id is None or game_id in seen_game_ids:
            continue
        tasks.append(
            {
                "game_id": game_id,
                "game_name": _normalize_text(game.get("name")),
            }
        )
        seen_game_ids.add(game_id)
    return sorted(tasks, key=lambda item: str(item["game_id"]))


def load_unlock_train_candidate_tasks(
    csv_path: str | Path,
    patient_id: str,
) -> list[dict[str, Any]]:
    """Build candidate task rows from ai_params.unlock_train keys in request CSV."""
    unlock_train = _load_unlock_train_by_patient(csv_path).get(
        _normalize_csv_patient_id(patient_id),
        {},
    )
    tasks: list[dict[str, Any]] = []
    seen_game_ids: set[str] = set()
    for raw_task_id in unlock_train:
        game_id = _normalize_text(raw_task_id)
        if game_id is None or game_id in seen_game_ids:
            continue
        tasks.append({"game_id": game_id, "game_name": None})
        seen_game_ids.add(game_id)
    return tasks


@lru_cache(maxsize=8)
def _load_unlock_train_by_patient(csv_path: str | Path) -> dict[str, dict[str, Any]]:
    """Load patient_id -> unlock_train mapping from algorithm request CSV."""
    resolved_path = Path(csv_path)
    if not resolved_path.exists():
        raise FileNotFoundError(f"algorithm request CSV not found: {resolved_path}")

    rows_by_patient: dict[str, dict[str, Any]] = {}
    with resolved_path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            try:
                ai_params = _parse_csv_object(row.get("ai_params"))
            except (SyntaxError, ValueError) as exc:
                LOGGER.warning("Skipped malformed ai_params row in CSV: error=%s", exc)
                continue
            if not isinstance(ai_params, dict):
                continue
            normalized_patient_id = _normalize_csv_patient_id(ai_params.get("user_id"))
            if normalized_patient_id is None:
                continue
            unlock_train = ai_params.get("unlock_train")
            if isinstance(unlock_train, dict):
                rows_by_patient[normalized_patient_id] = unlock_train
    return rows_by_patient


def _parse_csv_object(value: object) -> object:
    """Parse object-like CSV fields that may be quoted Python literals."""
    parsed: object = value
    for _ in range(2):
        if not isinstance(parsed, str):
            break
        stripped = parsed.strip()
        if not stripped:
            return None
        parsed = ast.literal_eval(stripped)
    return parsed


def _normalize_csv_patient_id(value: object) -> str | None:
    """Normalize CSV user_id such as 20123188_old to patient_id 20123188."""
    text = _normalize_text(value)
    if text is None:
        return None
    if text.endswith("_old"):
        text = text[: -len("_old")]
    return text or None


def build_similar_user_game_counts(
    candidates: list[SimilarUserCandidate],
    similar_user_histories: dict[str, list[dict[str, Any]]],
    *,
    weighting_enabled: bool = False,
    weighted_sort_enabled: bool = False,
) -> list[dict[str, Any]]:
    """Aggregate simple game counts from similar-user histories for prompt input."""
    if not weighting_enabled:
        rows: list[dict[str, Any]] = []
        for candidate in candidates:
            rows.extend(similar_user_histories.get(candidate.patient_id, []))
        return build_game_counts_from_history(rows)

    candidate_weights = _normalize_candidate_weights(candidates)
    game_index: dict[str, dict[str, Any]] = {}
    for candidate in candidates:
        candidate_weight = candidate_weights.get(candidate.patient_id, 1.0)
        seen_game_ids_for_candidate: set[str] = set()
        for row in similar_user_histories.get(candidate.patient_id, []):
            game = _normalize_node(row.get("g"))
            game_id = _normalize_text(game.get("id")) or _normalize_text(
                game.get("name")
            )
            if game_id is None:
                continue
            item = game_index.setdefault(
                game_id,
                {
                    "game_id": game_id,
                    "game_name": _normalize_text(game.get("name")),
                    "count": 0,
                    "weighted_count": 0.0,
                    "supporting_candidate_ids": [],
                    "_support_scores": [],
                },
            )
            item["count"] += 1
            item["weighted_count"] += candidate_weight
            if game_id not in seen_game_ids_for_candidate:
                item["supporting_candidate_ids"].append(candidate.patient_id)
                item["_support_scores"].append(candidate_weight)
                seen_game_ids_for_candidate.add(game_id)

    game_counts: list[dict[str, Any]] = []
    for item in game_index.values():
        support_scores = item.pop("_support_scores")
        supporting_user_count = len(support_scores)
        item["weighted_count"] = round(float(item["weighted_count"]), 4)
        item["supporting_user_count"] = supporting_user_count
        item["avg_support_score"] = round(
            sum(float(score) for score in support_scores) / supporting_user_count,
            4,
        )
        item["max_support_score"] = round(
            max(float(score) for score in support_scores),
            4,
        )
        game_counts.append(item)

    if weighted_sort_enabled:
        return sorted(
            game_counts,
            key=lambda item: (
                -float(item["weighted_count"]),
                -int(item["supporting_user_count"]),
                -int(item["count"]),
                str(item["game_id"]),
            ),
        )
    return sorted(
        game_counts,
        key=lambda item: (
            -int(item["count"]),
            str(item["game_id"]),
        ),
    )


def _normalize_candidate_weights(
    candidates: list[SimilarUserCandidate],
) -> dict[str, float]:
    """Normalize candidate weights within one target user's candidate set."""
    raw_weights = {
        candidate.patient_id: candidate.weight
        for candidate in candidates
    }
    max_weight = max(raw_weights.values(), default=1.0)
    if max_weight <= 0:
        max_weight = 1.0
    return {
        patient_id: round(float(weight) / max_weight, 4)
        for patient_id, weight in raw_weights.items()
    }


def build_similar_user_task_evidence(
    candidates: list[SimilarUserCandidate],
    similar_user_histories: dict[str, list[dict[str, Any]]],
    *,
    excluded_game_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Build per-candidate task counts with candidate similarity scores."""
    evidence: list[dict[str, Any]] = []
    for candidate in candidates:
        tasks = build_game_counts_from_history(
            similar_user_histories.get(candidate.patient_id, []),
            excluded_game_ids=excluded_game_ids,
        )
        evidence.append(
            {
                "patient_id": candidate.patient_id,
                "candidate_score": candidate.candidate_score,
                "tasks": tasks,
            }
        )
    return evidence


def build_prompt_similar_user_candidates(
    candidates: list[SimilarUserCandidate],
) -> list[dict[str, Any]]:
    """Build compact candidate-score context for the LLM prompt."""
    prompt_candidates: list[dict[str, Any]] = []
    for candidate in candidates:
        item: dict[str, Any] = {
            "patient_id": candidate.patient_id,
            "candidate_score": candidate.candidate_score,
        }
        if candidate.candidate_base_date is not None:
            item["candidate_base_date"] = candidate.candidate_base_date
        prompt_candidates.append(item)
    return prompt_candidates


def build_game_counts_from_history(
    history_rows: list[dict[str, Any]],
    *,
    excluded_game_ids: set[str] | None = None,
) -> list[dict[str, Any]]:
    """Aggregate simple game counts from task-history rows."""
    normalized_excluded_game_ids = excluded_game_ids or set()
    game_index: dict[str, dict[str, Any]] = {}
    for row in history_rows:
        game = _normalize_node(row.get("g"))
        game_id = _normalize_text(game.get("id")) or _normalize_text(game.get("name"))
        if game_id is None or game_id in normalized_excluded_game_ids:
            continue
        item = game_index.setdefault(
            game_id,
            {
                "game_id": game_id,
                "game_name": _normalize_text(game.get("name")),
                "count": 0,
            },
        )
        item["count"] += 1
    game_counts = sorted(
        game_index.values(),
        key=lambda item: (
            -int(item["count"]),
            str(item["game_id"]),
        ),
    )
    return game_counts


def filter_recent_target_repeated_games(
    game_counts: list[dict[str, Any]],
    target_history: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Remove games that appear on consecutive target-history dates."""
    return filter_game_counts_by_ids(
        game_counts,
        find_consecutive_target_game_ids(target_history),
    )


def filter_game_counts_by_ids(
    game_counts: list[dict[str, Any]],
    excluded_game_ids: set[str],
) -> list[dict[str, Any]]:
    """Remove game-count rows with IDs in the excluded set."""
    if not excluded_game_ids:
        return game_counts
    return [
        game_count
        for game_count in game_counts
        if _normalize_text(game_count.get("game_id")) not in excluded_game_ids
    ]


def filter_game_counts_to_ids(
    game_counts: list[dict[str, Any]],
    allowed_game_ids: set[str],
) -> list[dict[str, Any]]:
    """Keep only game-count rows whose IDs are in the allowed candidate task set."""
    if not allowed_game_ids:
        return []
    return [
        game_count
        for game_count in game_counts
        if _normalize_text(game_count.get("game_id")) in allowed_game_ids
    ]


def filter_task_evidence_to_ids(
    task_evidence: list[dict[str, Any]],
    allowed_game_ids: set[str],
) -> list[dict[str, Any]]:
    """Keep only per-candidate evidence tasks in the allowed candidate task set."""
    if not allowed_game_ids:
        return []

    filtered_evidence: list[dict[str, Any]] = []
    for evidence in task_evidence:
        tasks = evidence.get("tasks")
        if not isinstance(tasks, list):
            continue
        filtered_tasks = [
            task
            for task in tasks
            if isinstance(task, dict)
            and _normalize_text(task.get("game_id")) in allowed_game_ids
        ]
        if not filtered_tasks:
            continue
        filtered_item = dict(evidence)
        filtered_item["tasks"] = filtered_tasks
        filtered_evidence.append(filtered_item)
    return filtered_evidence


def filter_candidate_tasks_to_ids(
    candidate_tasks: list[dict[str, Any]],
    allowed_game_ids: set[str],
) -> list[dict[str, Any]]:
    """Keep only candidate tasks whose IDs are in the selected prompt set."""
    if not allowed_game_ids:
        return []
    return [
        task
        for task in candidate_tasks
        if _normalize_text(task.get("game_id")) in allowed_game_ids
    ]


def select_prompt_candidate_game_ids(
    similar_user_game_counts: list[dict[str, Any]],
    similar_user_task_evidence: list[dict[str, Any]],
    *,
    overall_top_n: int,
    high_score_user_count: int,
    per_high_score_user_top_k: int,
    max_prompt_candidates: int,
) -> set[str]:
    """Select a compact prompt candidate set from global and high-score evidence."""
    selected_game_ids: list[str] = []
    seen_game_ids: set[str] = set()

    def add_game_id(raw_game_id: Any) -> None:
        game_id = _normalize_text(raw_game_id)
        if game_id is None or game_id in seen_game_ids:
            return
        selected_game_ids.append(game_id)
        seen_game_ids.add(game_id)

    for game_count in similar_user_game_counts[: max(0, overall_top_n)]:
        add_game_id(game_count.get("game_id"))

    scored_evidence = sorted(
        similar_user_task_evidence,
        key=lambda item: (
            -float(item.get("candidate_score") or 0.0)
            if isinstance(item, dict)
            else 0.0,
            str(item.get("patient_id") or "") if isinstance(item, dict) else "",
        ),
    )
    for evidence in scored_evidence[: max(0, high_score_user_count)]:
        tasks = evidence.get("tasks")
        if not isinstance(tasks, list):
            continue
        for task in tasks[: max(0, per_high_score_user_top_k)]:
            if isinstance(task, dict):
                add_game_id(task.get("game_id"))

    if max_prompt_candidates <= 0:
        return set()
    return set(selected_game_ids[:max_prompt_candidates])


def find_consecutive_target_game_ids(
    target_history: list[dict[str, Any]],
) -> set[str]:
    """Return game IDs that appear on two consecutive target-history dates."""
    dates_by_game_id: dict[str, set[date]] = {}
    for row in target_history:
        training_date_text = _normalize_text(row.get("trainingDate"))
        if training_date_text is None:
            continue
        try:
            training_date = parse_date_value(training_date_text, "trainingDate")
        except ValueError:
            continue
        game = _normalize_node(row.get("g"))
        game_id = _normalize_text(game.get("id")) or _normalize_text(game.get("name"))
        if game_id is None:
            continue
        dates_by_game_id.setdefault(game_id, set()).add(training_date)

    repeated_game_ids: set[str] = set()
    for game_id, training_dates in dates_by_game_id.items():
        if any(
            training_date + timedelta(days=1) in training_dates
            for training_date in training_dates
        ):
            repeated_game_ids.add(game_id)
    return repeated_game_ids


def build_rule_based_predictions(
    candidate_training_tasks: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    """Build deterministic fallback predictions from candidate task scores."""
    if not candidate_training_tasks:
        return []
    max_score = max(float(task.get("weighted_score") or 0.0) for task in candidate_training_tasks)
    predictions: list[dict[str, Any]] = []
    for index, task in enumerate(candidate_training_tasks[:top_k], start=1):
        weighted_score = float(task.get("weighted_score") or 0.0)
        predictions.append(
            {
                "rank": index,
                "game_id": task.get("game_id"),
                "game_name": task.get("game_name"),
                "task_type": task.get("task_type"),
                "confidence": round(weighted_score / max_score, 4)
                if max_score > 0
                else 0.0,
                "reason": "相似用户历史中该训练任务的加权出现次数较高。",
                "supporting_candidate_ids": task.get("supporting_candidate_ids", []),
            }
        )
    return predictions


def build_task_prediction_prompt(
    *,
    patient_id: str,
    similar_user_game_counts: list[dict[str, Any]],
    candidate_training_tasks: list[dict[str, Any]],
    task_top_k: int,
    target_profile: dict[str, Any] | None = None,
    target_entities: dict[str, Any] | None = None,
    candidate_source: str | None = None,
    similar_user_candidates: list[dict[str, Any]] | None = None,
    similar_user_task_evidence: list[dict[str, Any]] | None = None,
    prompt_template_name: str = CURRENT_TASK_PREDICTION_PROMPT_TEMPLATE_NAME,
) -> str:
    """构建用于 LLM 训练任务预测的 JSON 优先提示词。

    参数说明：
    patient_id：目标用户 ID，用于标识当前要预测训练任务的患者。
    similar_user_game_counts：相似用户在预测任务时间窗口内的任务出现次数汇总，
        用于提供“哪些任务在相似用户中更常见”的整体证据。
    candidate_training_tasks：允许 LLM 选择的候选训练任务池；最终输出的 game_id
        和 game_name 必须来自这里，避免生成库外任务。
    task_top_k：要求 LLM 返回的推荐任务数量上限。
    """
    payload = {
        "patient_id": patient_id,
        "similar_user_game_counts": similar_user_game_counts,
        "candidate_training_tasks": candidate_training_tasks,
        "output_requirement": {
            "top_k": task_top_k,
            "format": {
                "patient_id": patient_id,
                "predicted_training_tasks": [
                    {
                        "rank": 1,
                        "game_id": "只能来自 candidate_training_tasks",
                        "game_name": "只能来自 candidate_training_tasks",
                        "confidence": 0.0,
                        "reason": "简短说明目标用户和相似用户证据",
                        "supporting_candidate_ids": ["候选用户id"],
                    }
                ],
            },
        },
    }
    normalized_prompt_template_name = prompt_template_name.strip()
    if candidate_source is not None:
        payload["candidate_source"] = candidate_source
    if normalized_prompt_template_name == "TASK_PREDICTION_PROMPT_TEMPLATE_DIRECT_ENTITY_V1":
        payload["target_profile"] = target_profile or {}
        payload["target_entities"] = target_entities or {}
        payload["similar_user_candidates"] = similar_user_candidates or []
        payload["similar_user_task_evidence"] = similar_user_task_evidence or []
    elif normalized_prompt_template_name == "TASK_PREDICTION_PROMPT_TEMPLATE_V2":
        payload["similar_user_candidates"] = similar_user_candidates or []
        payload["similar_user_task_evidence"] = similar_user_task_evidence or []
    prompt_template = get_task_prediction_prompt_template(normalized_prompt_template_name)
    return prompt_template + f"{json.dumps(payload, ensure_ascii=False, indent=2, default=str)}"


def get_task_prediction_prompt_template(prompt_template_name: str) -> str:
    """Return a named prompt template or raise a clear config error."""
    if not isinstance(prompt_template_name, str) or not prompt_template_name.strip():
        raise ValueError("prompt_template_name must be a non-empty string.")
    normalized_name = prompt_template_name.strip()
    prompt_template = TASK_PREDICTION_PROMPT_TEMPLATES.get(normalized_name)
    if prompt_template is None:
        available_names = ", ".join(sorted(TASK_PREDICTION_PROMPT_TEMPLATES))
        raise ValueError(
            f"Unknown prompt_template_name: {normalized_name}. "
            f"Available templates: {available_names}."
        )
    return prompt_template


def validate_prompt_weighting_compatibility(
    prompt_template_name: str,
    similar_user_game_counts_weighting_enabled: bool,
) -> None:
    """Raise when a weighted-count prompt is used without weighted inputs."""
    normalized_name = (
        prompt_template_name.strip()
        if isinstance(prompt_template_name, str)
        else ""
    )
    if (
        normalized_name == WEIGHTED_GAME_COUNTS_PROMPT_TEMPLATE_NAME
        and not similar_user_game_counts_weighting_enabled
    ):
        raise ValueError(
            "TASK_PREDICTION_PROMPT_TEMPLATE_V3 requires "
            "similar_user_game_counts_weighting_enabled=true."
        )


def _resolve_predicted_tasks(
    llm_prediction: dict[str, Any] | None,
    rule_based_tasks: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if isinstance(llm_prediction, dict):
        predicted_tasks = llm_prediction.get("predicted_training_tasks")
        if isinstance(predicted_tasks, list):
            return predicted_tasks
        predicted_tasks = llm_prediction.get("predicted_tasks")
        if isinstance(predicted_tasks, list):
            return predicted_tasks
    return rule_based_tasks


def _find_raw_candidate_items(pipeline_result: dict[str, Any]) -> list[Any]:
    candidate_result = pipeline_result.get("candidate_result")
    if isinstance(candidate_result, dict):
        candidates = candidate_result.get("candidates")
        if isinstance(candidates, list):
            return candidates

    candidate_summary = pipeline_result.get("candidate_summary")
    if isinstance(candidate_summary, dict):
        candidates = candidate_summary.get("candidates")
        if isinstance(candidates, list):
            return candidates
        candidate_ids = candidate_summary.get("candidate_ids")
        if isinstance(candidate_ids, list):
            return candidate_ids

    candidates = pipeline_result.get("candidates")
    if isinstance(candidates, list):
        return candidates
    candidate_ids = pipeline_result.get("candidate_ids")
    if isinstance(candidate_ids, list):
        return candidate_ids
    return []


def _parse_candidate(raw_candidate: Any) -> SimilarUserCandidate | None:
    if isinstance(raw_candidate, str) or isinstance(raw_candidate, int):
        patient_id = str(raw_candidate).strip()
        return SimilarUserCandidate(patient_id) if patient_id else None
    if not isinstance(raw_candidate, dict):
        return None
    raw_patient_id = (
        raw_candidate.get("patient_id")
        or raw_candidate.get("candidate_patient_id")
        or raw_candidate.get("id")
    )
    patient_id = str(raw_patient_id or "").strip()
    if not patient_id:
        return None
    return SimilarUserCandidate(
        patient_id=patient_id,
        candidate_score=_normalize_float(raw_candidate.get("candidate_score")),
        candidate_base_date=_extract_candidate_base_date(raw_candidate),
    )


def _parse_first_valid_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    while start >= 0:
        try:
            value = json.loads(_extract_json_object_from(text, start))
        except (json.JSONDecodeError, ValueError):
            start = text.find("{", start + 1)
            continue
        if isinstance(value, dict):
            return value
        start = text.find("{", start + 1)
    raise ValueError("text does not contain a valid JSON object.")


def _extract_json_object_from(text: str, start: int) -> str:
    depth = 0
    in_string = False
    escape_next = False
    for index in range(start, len(text)):
        char = text[index]
        if escape_next:
            escape_next = False
            continue
        if char == "\\":
            escape_next = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    raise ValueError("text contains an incomplete JSON object.")


def _normalize_node(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    try:
        return dict(value)
    except (TypeError, ValueError):
        return {}


def _normalize_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _normalize_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_candidate_base_date(raw_candidate: dict[str, Any]) -> str | None:
    """Extract candidate disease-course base date from full or summarized scores."""
    score_details = raw_candidate.get("score_details")
    if isinstance(score_details, dict):
        disease_course_details = score_details.get("disease_course_secondary_ability")
        if isinstance(disease_course_details, dict):
            candidate_base_date = _normalize_text(
                disease_course_details.get("candidate_base_date")
            )
            if candidate_base_date is not None:
                return candidate_base_date

    score_summary = raw_candidate.get("score_summary")
    if isinstance(score_summary, dict):
        disease_course_summary = score_summary.get("disease_course_secondary_ability")
        if isinstance(disease_course_summary, dict):
            return _normalize_text(disease_course_summary.get("candidate_base_date"))
    return None


def _extract_candidate_task_game_ids(candidate_tasks: list[dict[str, Any]]) -> set[str]:
    """Extract selectable game IDs from candidate task rows."""
    game_ids: set[str] = set()
    for task in candidate_tasks:
        game_id = _normalize_text(task.get("game_id"))
        if game_id is not None:
            game_ids.add(game_id)
    return game_ids


def _dedupe_recent_games(
    recent_games: list[dict[str, Any]],
    *,
    top_k: int,
) -> list[dict[str, Any]]:
    seen_game_ids: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for game in reversed(recent_games):
        game_id = _normalize_text(game.get("game_id"))
        if game_id is None or game_id in seen_game_ids:
            continue
        deduped.append(game)
        seen_game_ids.add(game_id)
        if len(deduped) >= top_k:
            break
    return deduped
