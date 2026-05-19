"""Candidate-user aggregation and ranking service."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import Any

from config.settings import CandidateScoringSettings, SetSameScoringSettings

from ...domain.graph_schema import PathPattern
from ...domain.path_models import (
    PatientTasksetDiseaseTasksetPatientPath,
    PatientTasksetSymptomTasksetPatientPath,
    PatientTasksetTaskGameTaskTasksetPatientPath,
    PatientTasksetUnknownTasksetPatientPath,
)
from ...utils.logger import get_logger
from ..user_service import UserService
from .utils import (
    calculate_common_game_score_similarity,
    calculate_game_similarity_with_diversity_score,
    calculate_secondary_ability_relative_distance,
    calculate_set_same_score,
)


LOGGER = get_logger(__name__)


@dataclass(frozen=True)
class ScoredDomainPath:
    """One scored raw path paired with its typed domain path."""

    path_index: int | None
    total_score: float | None
    pattern: PathPattern
    path: Any


@dataclass
class SimilarUserCandidateService:
    """Build and rank similar-user candidates using shared user-service reads."""

    user_service: UserService | None = None

    def aggregate_candidates_from_scored_paths(
        self,
        scored_result: dict[str, Any],
        *,
        candidate_top_k: int,
        scoring_settings: CandidateScoringSettings | None = None,
        disease_course_window_days: int | None = None,
    ) -> dict[str, Any]:
        """Deduplicate candidate users from typed scored paths and rank by candidate_score."""
        return self.aggregate_candidates_from_multiple_scored_results(
            [scored_result],
            candidate_top_k=candidate_top_k,
            scoring_settings=scoring_settings,
            disease_course_window_days=disease_course_window_days,
        )

    def aggregate_candidates_from_multiple_scored_results(
        self,
        scored_results: list[dict[str, Any]],
        *,
        candidate_top_k: int,
        scoring_settings: CandidateScoringSettings | None = None,
        disease_course_window_days: int | None = None,
    ) -> dict[str, Any]:
        """Deduplicate candidate users across multiple scored pattern results."""
        if candidate_top_k <= 0:
            raise ValueError(
                f"candidate_top_k must be greater than 0, got {candidate_top_k}."
            )
        if not scored_results:
            raise ValueError("scored_results must contain at least one result.")
        resolved_scoring_settings = scoring_settings or CandidateScoringSettings()

        scored_domain_paths: list[ScoredDomainPath] = []
        for scored_result in scored_results:
            scored_domain_paths.extend(_build_scored_domain_paths(scored_result))

        first_result = scored_results[0]
        score_end_date = _extract_score_end_date(first_result)
        path_window = _extract_path_window(first_result)
        source_id = first_result.get("source_id")
        source_parameter = first_result.get("source_parameter")
        source_patient_id = (
            source_id
            if source_parameter == "patient_id" and isinstance(source_id, str)
            else None
        )
        patterns = [
            result.get("pattern")
            for result in scored_results
            if isinstance(result.get("pattern"), str)
        ]
        LOGGER.debug(
            "Aggregating similar-user candidates: source_id=%s, source_parameter=%s, patterns=%s, scored_path_count=%s, candidate_top_k=%s, score_end_date=%s",
            source_id,
            source_parameter,
            patterns,
            len(scored_domain_paths),
            candidate_top_k,
            score_end_date,
        )

        candidate_buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {
                "patient_id": None,
                "match_count": 0,
                "best_score": None,
                "avg_score": 0.0,
                "pattern_breakdown": {},
                "candidate_score": None,
                "score_details": {},
                "_score_sum": 0.0,
            }
        )

        for scored_path in scored_domain_paths:
            candidate_id = scored_path.path.p2.id
            pattern_key = scored_path.pattern.value
            bucket = candidate_buckets[candidate_id]
            bucket["patient_id"] = candidate_id
            bucket["match_count"] += 1
            if scored_path.total_score is not None:
                bucket["_score_sum"] += scored_path.total_score
                if (
                    bucket["best_score"] is None
                    or scored_path.total_score > bucket["best_score"]
                ):
                    bucket["best_score"] = scored_path.total_score
            pattern_breakdown = bucket["pattern_breakdown"].setdefault(
                pattern_key,
                {
                    "match_count": 0,
                    "path_indices": [],
                    "best_score": None,
                    "avg_score": 0.0,
                    "_score_sum": 0.0,
                },
            )
            pattern_breakdown["match_count"] += 1
            if isinstance(scored_path.path_index, int):
                pattern_breakdown["path_indices"].append(scored_path.path_index)
            if scored_path.total_score is not None:
                pattern_breakdown["_score_sum"] += scored_path.total_score
                if (
                    pattern_breakdown["best_score"] is None
                    or scored_path.total_score > pattern_breakdown["best_score"]
                ):
                    pattern_breakdown["best_score"] = scored_path.total_score

        candidates: list[dict[str, Any]] = []
        for bucket in candidate_buckets.values():
            match_count = bucket["match_count"]
            score_sum = bucket.pop("_score_sum")
            bucket["avg_score"] = round(score_sum / match_count, 2) if match_count else 0.0
            if bucket["best_score"] is not None:
                bucket["best_score"] = round(bucket["best_score"], 2)
            for pattern_bucket in bucket["pattern_breakdown"].values():
                pattern_match_count = pattern_bucket["match_count"]
                pattern_score_sum = pattern_bucket.pop("_score_sum")
                pattern_bucket["path_indices"] = sorted(set(pattern_bucket["path_indices"]))
                pattern_bucket["avg_score"] = (
                    round(pattern_score_sum / pattern_match_count, 2)
                    if pattern_match_count
                    else 0.0
                )
                if pattern_bucket["best_score"] is not None:
                    pattern_bucket["best_score"] = round(pattern_bucket["best_score"], 2)
                    
            candidate_score, score_details = self.calculate_candidate_score(
                primary_patient_id=source_patient_id,
                candidate_patient_id=bucket["patient_id"],
                end_date=score_end_date,
                scoring_settings=resolved_scoring_settings,
                disease_course_window_days=disease_course_window_days,
            )
            bucket["candidate_score"] = candidate_score
            bucket["score_details"] = score_details
            candidates.append(bucket)

        candidates.sort(
            key=lambda item: _candidate_score_sort_value(item.get("candidate_score")),
            reverse=True,
        )
        candidates = candidates[:candidate_top_k]
        LOGGER.info(
            "Aggregated similar-user candidates: source_id=%s, source_parameter=%s, candidate_count=%s",
            source_id,
            source_parameter,
            len(candidates),
        )

        return {
            "source_id": source_id,
            "source_parameter": source_parameter,
            "pattern": patterns[0] if len(patterns) == 1 else None,
            "patterns": patterns,
            "candidate_top_k": candidate_top_k,
            "path_count": sum(_extract_int(result.get("path_count")) for result in scored_results),
            "scored_path_count": sum(
                _extract_int(result.get("scored_path_count")) for result in scored_results
            ),
            "retrieval_context": {
                "base_date": _extract_base_date(first_result),
                "path_window": path_window,
                "score_end_date": score_end_date,
                "candidate_scope": _build_candidate_scope(
                    path_window,
                    score_end_date,
                    candidate_top_k,
                ),
                "candidate_scoring": _build_candidate_scoring_context(
                    resolved_scoring_settings
                ),
            },
            "candidate_count": len(candidates),
            "candidates": candidates,
        }

    def calculate_candidate_score(
        self,
        *,
        primary_patient_id: object,
        candidate_patient_id: object,
        end_date: str | None,
        candidate_base_date: str | None = None,
        scoring_settings: CandidateScoringSettings | None = None,
        disease_course_window_days: int | None = None,
    ) -> tuple[float | None, dict[str, Any]]:
        """Calculate candidate score from similarity, set sameness, and game diversity."""
        resolved_scoring_settings = scoring_settings or CandidateScoringSettings()
        if (
            self.user_service is None
            or not isinstance(primary_patient_id, str)
            or not primary_patient_id.strip()
            or not isinstance(candidate_patient_id, str)
            or not candidate_patient_id.strip()
            or end_date is None
        ):
            LOGGER.warning(
                "Skipped candidate score calculation because required context is missing: primary_patient_id=%s, candidate_patient_id=%s, end_date=%s, has_user_service=%s",
                primary_patient_id,
                candidate_patient_id,
                end_date,
                self.user_service is not None,
            )
            return None, {
                "scoring_components": _build_candidate_scoring_context(
                    resolved_scoring_settings
                ),
                "reason": "missing user_service or score_end_date",
            }

        common_game_score_similarity, similarity_score = (
            self._calculate_common_game_score_similarity(
                enabled=resolved_scoring_settings.common_game_score_similarity,
                primary_patient_id=primary_patient_id.strip(),
                candidate_patient_id=candidate_patient_id.strip(),
                end_date=end_date,
            )
        )
        game_similarity_with_diversity_score, game_similarity_score = (
            self._calculate_game_similarity_with_diversity_score(
                enabled=(
                    resolved_scoring_settings.game_similarity_with_diversity_score
                ),
                primary_patient_id=primary_patient_id.strip(),
                candidate_patient_id=candidate_patient_id.strip(),
                end_date=end_date,
            )
        )
        set_same_scores, set_same_score = self._calculate_set_same_score_component(
            primary_patient_id=primary_patient_id.strip(),
            candidate_patient_id=candidate_patient_id.strip(),
            end_date=end_date,
            scoring_settings=resolved_scoring_settings.set_same,
        )
        resolved_candidate_base_date = candidate_base_date
        if resolved_candidate_base_date is None:
            resolved_candidate_base_date = self.get_candidate_disease_course_base_date(
                primary_patient_id=primary_patient_id.strip(),
                candidate_patient_id=candidate_patient_id.strip(),
                primary_base_date=end_date,
            )
        disease_course_secondary_ability, disease_course_score = (
            self._calculate_disease_course_secondary_ability_score(
                enabled=(
                    resolved_scoring_settings.disease_course_secondary_ability
                ),
                primary_patient_id=primary_patient_id.strip(),
                candidate_patient_id=candidate_patient_id.strip(),
                primary_base_date=end_date,
                candidate_base_date=resolved_candidate_base_date,
                disease_course_window_days=disease_course_window_days,
            )
        )
        candidate_score = _sum_enabled_scores(
            similarity_score,
            game_similarity_score,
            disease_course_score,
            set_same_score
            if _has_enabled_set_same_component(resolved_scoring_settings.set_same)
            else None,
        )
        LOGGER.debug(
            "Calculated candidate score: primary_patient_id=%s, candidate_patient_id=%s, end_date=%s, similarity=%s, game_similarity=%s, set_same=%s, candidate_score=%s",
            primary_patient_id.strip(),
            candidate_patient_id.strip(),
            end_date,
            similarity_score,
            game_similarity_score,
            set_same_score,
            candidate_score,
        )
        return candidate_score, {
            "scoring_components": _build_candidate_scoring_context(
                resolved_scoring_settings
            ),
            "common_game_score_similarity": common_game_score_similarity,
            "game_similarity_with_diversity_score": game_similarity_with_diversity_score,
            "disease_course_secondary_ability": disease_course_secondary_ability,
            "set_same_scores": set_same_scores,
        }

    def _calculate_common_game_score_similarity(
        self,
        *,
        enabled: bool,
        primary_patient_id: str,
        candidate_patient_id: str,
        end_date: str,
    ) -> tuple[dict[str, Any] | None, float | None]:
        if not enabled:
            return None, None

        records = self.user_service.get_patient_game_norm_score_series_comparison_by_end_date(
            primary_patient_id,
            candidate_patient_id,
            end_date,
        )
        score_details = calculate_common_game_score_similarity(records)
        similarity = score_details.get("similarity")
        similarity_score = (
            round(float(similarity), 3)
            if isinstance(similarity, (int, float))
            else None
        )
        return {**score_details, "similarity": similarity_score}, similarity_score

    def _calculate_game_similarity_with_diversity_score(
        self,
        *,
        enabled: bool,
        primary_patient_id: str,
        candidate_patient_id: str,
        end_date: str,
    ) -> tuple[dict[str, Any] | None, float | None]:
        if not enabled:
            return None, None

        game_rows = self.user_service.get_patient_game_set_comparison_by_end_date(
            primary_patient_id,
            candidate_patient_id,
            end_date,
        )
        source_games, candidate_games = _extract_node_comparison_keys(
            game_rows,
            "games1",
            "games2",
        )
        score_details = _round_numeric_values(
            calculate_game_similarity_with_diversity_score(
                source_games,
                candidate_games,
            )
        )
        score = _coerce_optional_float(score_details.get("score"))
        return score_details, score

    def _calculate_set_same_score_component(
        self,
        *,
        primary_patient_id: str,
        candidate_patient_id: str,
        end_date: str,
        scoring_settings: SetSameScoringSettings,
    ) -> tuple[dict[str, object], float | None]:
        score_details = self._calculate_set_same_scores(
            primary_patient_id=primary_patient_id,
            candidate_patient_id=candidate_patient_id,
            end_date=end_date,
            scoring_settings=scoring_settings,
        )
        return score_details, _coerce_optional_float(score_details.get("score"))

    def _calculate_disease_course_secondary_ability_score(
        self,
        *,
        enabled: bool,
        primary_patient_id: str,
        candidate_patient_id: str,
        primary_base_date: str,
        candidate_base_date: str | None,
        disease_course_window_days: int | None,
    ) -> tuple[dict[str, object] | None, float | None]:
        if not enabled:
            return None, None
        if disease_course_window_days is None:
            return {
                "enabled": True,
                "score": None,
                "reason": "missing disease_course_window_days",
            }, None

        primary_rows = (
            self.user_service.get_patient_secondary_ability_scores_by_disease_course_window(
                primary_patient_id,
                primary_base_date,
                disease_course_window_days,
            )
        )
        resolved_candidate_base_date = candidate_base_date or primary_base_date
        candidate_rows = (
            self.user_service.get_patient_secondary_ability_scores_by_disease_course_window(
                candidate_patient_id,
                resolved_candidate_base_date,
                disease_course_window_days,
            )
        )
        distance_details = calculate_secondary_ability_relative_distance(
            primary_rows,
            candidate_rows,
        )
        distance = _coerce_optional_float(distance_details.get("distance"))
        score = _calculate_disease_course_secondary_ability_score_from_distance(
            distance
        )
        return {
            "enabled": True,
            "score": score,
            "primary_base_date": primary_base_date,
            "candidate_base_date": resolved_candidate_base_date,
            **distance_details,
        }, score

    def get_candidate_disease_course_base_date(
        self,
        *,
        primary_patient_id: str,
        candidate_patient_id: str,
        primary_base_date: str,
    ) -> str | None:
        """Return candidate-specific disease-course base date when available."""
        return None

    def _calculate_set_same_scores(
        self,
        *,
        primary_patient_id: str,
        candidate_patient_id: str,
        end_date: str,
        scoring_settings: SetSameScoringSettings | None = None,
    ) -> dict[str, object]:
        """Calculate disease, symptom, and unknown set-same scores."""
        resolved_settings = scoring_settings or SetSameScoringSettings()
        set_same_scores = {
            "disease": self._calculate_one_set_same_score(
                enabled=resolved_settings.disease,
                query_fn=self.user_service.get_patient_disease_set_comparison_by_end_date,
                primary_patient_id=primary_patient_id,
                candidate_patient_id=candidate_patient_id,
                end_date=end_date,
                source_key="diseases1",
                candidate_key="diseases2",
            ),
            "symptom": self._calculate_one_set_same_score(
                enabled=resolved_settings.symptom,
                query_fn=self.user_service.get_patient_symptom_set_comparison_by_end_date,
                primary_patient_id=primary_patient_id,
                candidate_patient_id=candidate_patient_id,
                end_date=end_date,
                source_key="symptoms1",
                candidate_key="symptoms2",
            ),
            "unknown": self._calculate_one_set_same_score(
                enabled=resolved_settings.unknown,
                query_fn=self.user_service.get_patient_unknown_set_comparison_by_end_date,
                primary_patient_id=primary_patient_id,
                candidate_patient_id=candidate_patient_id,
                end_date=end_date,
                source_key="unknowns1",
                candidate_key="unknowns2",
            ),
        }
        set_same_scores["score"] = round(
            sum(
                score_detail["score"]
                for score_detail in set_same_scores.values()
                if (
                    isinstance(score_detail, dict)
                    and isinstance(score_detail.get("score"), (int, float))
                )
            ),
            3,
        )
        return set_same_scores

    def _calculate_one_set_same_score(
        self,
        *,
        enabled: bool,
        query_fn: Any,
        primary_patient_id: str,
        candidate_patient_id: str,
        end_date: str,
        source_key: str,
        candidate_key: str,
    ) -> dict[str, object]:
        if not enabled:
            return {"enabled": False, "score": None, "reason": "disabled"}

        rows = query_fn(primary_patient_id, candidate_patient_id, end_date)
        source_values, candidate_values = _extract_node_comparison_keys(
            rows,
            source_key,
            candidate_key,
        )
        return {
            "enabled": True,
            **_round_numeric_values(
                calculate_set_same_score(source_values, candidate_values)
            ),
        }


def _build_scored_domain_paths(scored_result: dict[str, Any]) -> list[ScoredDomainPath]:
    """Convert scored raw path payloads to typed scored domain paths."""
    pattern = _coerce_supported_candidate_pattern(scored_result.get("pattern"))
    scored_domain_paths: list[ScoredDomainPath] = []

    for scored_path in scored_result.get("scores", []):
        if not isinstance(scored_path, dict):
            continue
        domain_path = _build_domain_path_from_scored_path(scored_path, pattern)
        if domain_path is None:
            continue
        scored_domain_paths.append(
            ScoredDomainPath(
                path_index=_extract_path_index(scored_path),
                total_score=_extract_total_score(scored_path),
                pattern=pattern,
                path=domain_path,
            )
        )

    return scored_domain_paths


def _build_candidate_scoring_context(
    scoring_settings: CandidateScoringSettings,
) -> dict[str, Any]:
    return {
        "common_game_score_similarity": scoring_settings.common_game_score_similarity,
        "game_similarity_with_diversity_score": (
            scoring_settings.game_similarity_with_diversity_score
        ),
        "disease_course_secondary_ability": (
            scoring_settings.disease_course_secondary_ability
        ),
        "set_same": {
            "disease": scoring_settings.set_same.disease,
            "symptom": scoring_settings.set_same.symptom,
            "unknown": scoring_settings.set_same.unknown,
        },
    }


def _has_enabled_set_same_component(settings: SetSameScoringSettings) -> bool:
    return settings.disease or settings.symptom or settings.unknown


def _sum_enabled_scores(*scores: float | None) -> float | None:
    enabled_scores = [score for score in scores if score is not None]
    return round(sum(enabled_scores), 3) if enabled_scores else None


def _coerce_optional_float(value: object) -> float | None:
    return float(value) if isinstance(value, (int, float)) else None


def _calculate_disease_course_secondary_ability_score_from_distance(
    distance: float | None,
) -> float | None:
    if distance is None:
        return None
    return round(1 / (1 + distance), 3)


def _extract_base_date(scored_result: dict[str, Any]) -> str | None:
    """Extract base date from scored-result retrieval context."""
    retrieval_context = scored_result.get("retrieval_context")
    if not isinstance(retrieval_context, dict):
        return None
    raw_base_date = retrieval_context.get("base_date")
    if isinstance(raw_base_date, str) and raw_base_date.strip():
        return raw_base_date.strip()
    return None


def _extract_path_window(scored_result: dict[str, Any]) -> dict[str, Any] | None:
    """Extract path window from scored-result retrieval context."""
    retrieval_context = scored_result.get("retrieval_context")
    if not isinstance(retrieval_context, dict):
        return None
    path_window = retrieval_context.get("path_window")
    return path_window if isinstance(path_window, dict) else None


def _extract_score_end_date(scored_result: dict[str, Any]) -> str | None:
    """Extract the exclusive end date used for candidate scoring."""
    retrieval_context = scored_result.get("retrieval_context")
    if isinstance(retrieval_context, dict):
        raw_score_end_date = retrieval_context.get("score_end_date")
        if isinstance(raw_score_end_date, str) and raw_score_end_date.strip():
            return raw_score_end_date.strip()

    path_window = _extract_path_window(scored_result)
    if isinstance(path_window, dict):
        raw_end_date = path_window.get("end_date")
        if isinstance(raw_end_date, str) and raw_end_date.strip():
            return raw_end_date.strip()

    if not isinstance(retrieval_context, dict):
        return None
    raw_split_training_date = retrieval_context.get("split_training_date")
    if isinstance(raw_split_training_date, str) and raw_split_training_date.strip():
        return raw_split_training_date.strip()
    return None


def _build_candidate_scope(
    path_window: dict[str, Any] | None,
    score_end_date: str | None,
    candidate_top_k: int,
) -> str:
    """Build a concise candidate source description."""
    if isinstance(path_window, dict):
        start_date = path_window.get("start_date")
        end_date = path_window.get("end_date")
        if start_date is not None and end_date is not None:
            return (
                "候选相似用户来自训练日期 "
                f">= {start_date} 且 < {end_date} 的已保存评分 path 去重结果，"
                f"最终返回 top-{candidate_top_k} 候选用户"
            )
    if score_end_date is not None:
        return (
            "候选相似用户来自训练日期 "
            f"< {score_end_date} 的已保存评分 path 去重结果，"
            f"最终返回 top-{candidate_top_k} 候选用户"
        )
    return (
        f"候选相似用户来自已保存评分 path 去重结果，最终返回 top-{candidate_top_k} 候选用户"
    )


def _coerce_supported_candidate_pattern(value: object) -> PathPattern:
    """Validate and normalize the candidate-supported path pattern."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("scored_result.pattern must be a non-empty string.")

    try:
        pattern = PathPattern(value.strip())
    except ValueError as exc:
        raise ValueError(
            f"Unsupported pattern for candidate aggregation: {value.strip()}"
        ) from exc
    if pattern not in {
        PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT,
        PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT,
        PathPattern.PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT,
    }:
        raise ValueError(f"Unsupported pattern for candidate aggregation: {pattern.value}")
    return pattern


def _build_domain_path_from_scored_path(
    scored_path: dict[str, Any],
    pattern: PathPattern,
) -> Any:
    """Build one typed domain path from a scored raw path payload."""
    raw_path = scored_path.get("path")
    if not isinstance(raw_path, dict):
        return None

    path_payload = {**raw_path, "pattern": pattern.value}
    try:
        if pattern == PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT:
            return PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(path_payload)
        if pattern == PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT:
            return PatientTasksetDiseaseTasksetPatientPath.from_dict(path_payload)
        if pattern == PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT:
            return PatientTasksetSymptomTasksetPatientPath.from_dict(path_payload)
        if pattern == PathPattern.PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT:
            return PatientTasksetUnknownTasksetPatientPath.from_dict(path_payload)
    except ValueError:
        return None
    raise ValueError(f"Unsupported pattern for candidate aggregation: {pattern.value}")


def _extract_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


def _candidate_score_sort_value(value: object) -> float:
    """Return the only value used for candidate sorting."""
    return float(value) if isinstance(value, (int, float)) else float("-inf")


def _extract_game_keys(rows: list[dict[str, object]]) -> list[str]:
    """Extract stable game keys from distinct-game query rows."""
    return _extract_node_keys(rows, "g")


def _extract_node_keys(rows: object, node_key: str) -> list[str]:
    """Extract stable node keys from distinct-node query rows."""
    node_keys: list[str] = []
    if not isinstance(rows, list):
        return node_keys
    for row in rows:
        if not isinstance(row, dict):
            continue
        node = row.get(node_key)
        if not isinstance(node, dict):
            continue
        for key in ("id", "name"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                node_keys.append(value.strip())
                break
    return node_keys


def _extract_node_comparison_keys(
    rows: object,
    source_key: str,
    candidate_key: str,
) -> tuple[list[str], list[str]]:
    """Extract stable node keys from one paired node-set comparison row."""
    if not isinstance(rows, list) or not rows:
        return [], []
    first_row = rows[0]
    if not isinstance(first_row, dict):
        return [], []
    return (
        _extract_node_list_keys(first_row.get(source_key)),
        _extract_node_list_keys(first_row.get(candidate_key)),
    )


def _extract_node_list_keys(nodes: object) -> list[str]:
    """Extract stable node keys from a collected node list."""
    node_keys: list[str] = []
    if not isinstance(nodes, list):
        return node_keys
    for node in nodes:
        if not isinstance(node, dict):
            continue
        for key in ("id", "name"):
            value = node.get(key)
            if isinstance(value, str) and value.strip():
                node_keys.append(value.strip())
                break
    return node_keys


def _round_numeric_values(value: object) -> object:
    """Round float values in nested score details for compact output."""
    if isinstance(value, float):
        return round(value, 3)
    if isinstance(value, dict):
        return {key: _round_numeric_values(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_round_numeric_values(item) for item in value]
    return value


def _extract_total_score(scored_path: dict[str, Any]) -> float | None:
    """Extract total score from one scored raw path payload."""
    score = scored_path.get("score")
    if not isinstance(score, dict):
        return None
    raw_total_score = score.get("total_score")
    if not isinstance(raw_total_score, (int, float)):
        return None
    return float(raw_total_score)


def _extract_path_index(scored_path: dict[str, Any]) -> int | None:
    """Extract path index from one scored raw path payload."""
    path_index = scored_path.get("path_index")
    return path_index if isinstance(path_index, int) else None
