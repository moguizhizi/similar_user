"""Score saved direct entity-start paths.

This script reads Disease/Symptom/Unknown -> TaskInstanceSet -> Patient path
files from the direct entity path index and scores them against a normalized
profile input. It is intentionally separate from the patient-start
score_pattern_paths.py flow.

Examples:
    python scripts/score_direct_entity_paths.py --patient-id 20123188
    python scripts/score_direct_entity_paths.py --age 66 --education 本科 --gender 男 --disease-id AU_DIS_0029
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from config.settings import (  # noqa: E402
    DEFAULT_CONFIG_PATH,
    load_query_settings,
    load_user_cache_settings,
)
from similar_user.data_access.user_cache_index import (  # noqa: E402
    UserCacheEntry,
    UserCacheIndexStore,
)
from similar_user.data_access.kg_repository import KgRepository  # noqa: E402
from similar_user.data_access.neo4j_client import Neo4jClient  # noqa: E402
from similar_user.domain.graph_schema import PathPattern  # noqa: E402
from similar_user.services.direct_entity_scoring_input import (  # noqa: E402
    DirectEntityScoringInput,
    resolve_scoring_input,
)
from similar_user.services.path_scoring import PathScoringRules  # noqa: E402
from similar_user.utils.logger import get_logger  # noqa: E402
from similar_user.utils.pattern_storage import StoredPatternResult  # noqa: E402
from similar_user.utils.user_cache_paths import (  # noqa: E402
    files_root_from_sqlite_path,
    patient_cache_leaf_dir,
)


LOGGER = get_logger(__name__)
DEFAULT_SCORED_OUTPUT_DIR = Path("data/scored_pattern_paths")


@dataclass(frozen=True)
class DirectSourceRef:
    """One direct entity source to read from the index."""

    pattern: PathPattern
    source_id: str


@dataclass(frozen=True)
class DirectPathScore:
    """Score details for one direct entity path."""

    total_score: float
    education_score: float | None
    age_score: float | None
    gender_score: float | None
    used_weights: dict[str, float]
    details: dict[str, str]

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-serializable mapping."""
        return asdict(self)


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Score saved direct Disease/Symptom/Unknown path files."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="YAML config path.",
    )
    parser.add_argument("--patient-id", help="Optional patient ID.")
    parser.add_argument(
        "--base-date",
        default=date.today().isoformat(),
        help="Base date for KG profile lookup. Defaults to today.",
    )
    parser.add_argument("--age", help="Manual age when KG profile is unavailable.")
    parser.add_argument(
        "--education",
        help="Manual education when KG profile is unavailable.",
    )
    parser.add_argument("--gender", help="Manual gender when KG profile is unavailable.")
    parser.add_argument(
        "--disease-id",
        action="append",
        nargs="+",
        default=[],
        help="Disease ID to score. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--symptom-id",
        action="append",
        nargs="+",
        default=[],
        help="Symptom ID to score. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--unknown-id",
        action="append",
        nargs="+",
        default=[],
        help="Unknown ID to score. Can be supplied multiple times.",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        help="Override query.score_pattern_paths.top_k.",
    )
    parser.add_argument(
        "--output",
        help="Optional extra JSON output path.",
    )
    parser.add_argument(
        "--scored-paths-dir",
        default=str(DEFAULT_SCORED_OUTPUT_DIR),
        help="Directory used to store scored direct entity path files.",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save detail/summary files; only log the JSON result.",
    )
    return parser.parse_args()


def score_direct_entity_paths(
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    patient_id: str | None = None,
    base_date: str | None = None,
    age: int | str | None = None,
    education: str | None = None,
    gender: str | None = None,
    disease_ids: list[str] | None = None,
    symptom_ids: list[str] | None = None,
    unknown_ids: list[str] | None = None,
    top_k: int | None = None,
    kg_repository: KgRepository | None = None,
    force_manual_input: bool = False,
) -> dict[str, Any]:
    """Resolve scoring input, load saved direct paths, and score them."""
    resolved_config_path = Path(config_path)
    query_settings = load_query_settings(resolved_config_path)
    resolved_base_date = base_date or date.today().isoformat()
    resolved_top_k = _resolve_top_k(top_k, query_settings.score_pattern_paths.top_k)

    if patient_id is not None and kg_repository is None and not force_manual_input:
        with Neo4jClient.from_config(resolved_config_path) as client:
            return score_direct_entity_paths(
                config_path=resolved_config_path,
                patient_id=patient_id,
                base_date=resolved_base_date,
                age=age,
                education=education,
                gender=gender,
                disease_ids=disease_ids,
                symptom_ids=symptom_ids,
                unknown_ids=unknown_ids,
                top_k=resolved_top_k,
                kg_repository=KgRepository(
                    client=client,
                    config_path=resolved_config_path,
                ),
            )

    resolution = resolve_scoring_input(
        kg_repository=kg_repository,
        patient_id=patient_id,
        base_date=resolved_base_date,
        age=age,
        education=education,
        gender=gender,
        disease_ids=disease_ids or [],
        symptom_ids=symptom_ids or [],
        unknown_ids=unknown_ids or [],
        use_when_patient_exists=(
            query_settings.direct_entity_path_scoring.use_when_patient_exists
        ),
        force_manual_input=force_manual_input,
    )
    if not resolution.should_score:
        return {
            "should_score": False,
            "reason": resolution.reason,
            "scoring_input": None,
            "scores": [],
            "path_count": 0,
            "scored_path_count": 0,
            "top_k": resolved_top_k,
        }
    if resolution.scoring_input is None:
        raise ValueError("scoring_input is required when should_score is true.")

    index_path = Path(query_settings.direct_entity_path.index_path)
    loaded_paths = _load_direct_paths_from_index(
        resolution.scoring_input,
        index_path=index_path,
    )
    scores = _score_loaded_paths(resolution.scoring_input, loaded_paths["paths"])
    scores = _limit_scores_by_pattern(scores, resolved_top_k)

    result = {
        "should_score": True,
        "reason": resolution.reason,
        "base_date": resolved_base_date,
        "index_path": str(index_path),
        "scoring_input": resolution.scoring_input.to_dict(),
        "source_count": loaded_paths["source_count"],
        "missing_sources": loaded_paths["missing_sources"],
        "path_count": loaded_paths["path_count"],
        "scored_path_count": len(scores),
        "top_k": resolved_top_k,
        "scores": scores,
    }
    result["cache_context"] = build_direct_entity_scored_cache_context(
        base_date=resolved_base_date,
        source_entries=loaded_paths["source_entries"],
        top_k=resolved_top_k,
    )
    result["source_id"] = _scored_source_id(resolution.scoring_input)
    result["source_parameter"] = (
        "patient_id"
        if resolution.scoring_input.patient_id
        and not resolution.scoring_input.source.startswith("manual_")
        else "manual_profile"
    )
    result["pattern"] = "DIRECT_ENTITY_PATHS"
    return result


def _load_direct_paths_from_index(
    scoring_input: DirectEntityScoringInput,
    *,
    index_path: Path,
) -> dict[str, Any]:
    index_payload = _read_index(index_path)
    entries = {
        (str(entry.get("pattern")), str(entry.get("source_id"))): entry
        for entry in index_payload.get("entries", [])
        if isinstance(entry, dict)
    }
    paths: list[dict[str, Any]] = []
    missing_sources: list[dict[str, str]] = []
    source_entries: list[dict[str, Any]] = []

    for source_ref in _source_refs_from_input(scoring_input):
        entry = entries.get((source_ref.pattern.value, source_ref.source_id))
        if entry is None:
            missing_sources.append(
                {"pattern": source_ref.pattern.value, "source_id": source_ref.source_id}
            )
            continue
        output_path = Path(str(entry.get("output_path") or ""))
        if not output_path.exists():
            missing_sources.append(
                {"pattern": source_ref.pattern.value, "source_id": source_ref.source_id}
            )
            continue
        source_entries.append(
            {
                "pattern": source_ref.pattern.value,
                "source_id": source_ref.source_id,
                "base_date": entry.get("base_date"),
                "window_days": entry.get("window_days"),
                "path_key": entry.get("path_key"),
                "direct_path_limit": entry.get("direct_path_limit"),
            }
        )
        stored_result = _load_stored_result(output_path)
        for path_index, path in enumerate(stored_result.paths):
            paths.append(
                {
                    "pattern": stored_result.pattern,
                    "source_id": stored_result.source_id,
                    "source_parameter": stored_result.source_parameter,
                    "path_index": path_index,
                    "path": path,
                }
            )

    return {
        "source_count": len(_source_refs_from_input(scoring_input)),
        "missing_sources": missing_sources,
        "source_entries": source_entries,
        "path_count": len(paths),
        "paths": paths,
    }


def _score_loaded_paths(
    scoring_input: DirectEntityScoringInput,
    loaded_paths: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    scored = []
    for item in loaded_paths:
        row = _path_row(item["path"])
        score = _score_one_path(scoring_input, row)
        scored.append(
            {
                "pattern": item["pattern"],
                "source_parameter": item["source_parameter"],
                "source_id": item["source_id"],
                "path_index": item["path_index"],
                "patient_id": _optional_text(row.get("p", {}).get("id")),
                "taskset_id": _optional_text(row.get("s", {}).get("id")),
                "training_date": _optional_text(row.get("s", {}).get("训练日期")),
                "score": score.to_dict(),
                "path": item["path"],
            }
        )
    return sorted(
        scored,
        key=lambda item: (
            -float(item["score"]["total_score"]),
            str(item.get("patient_id") or ""),
            str(item.get("source_id") or ""),
            int(item.get("path_index") or 0),
        ),
    )


def _limit_scores_by_pattern(
    scores: list[dict[str, Any]],
    top_k: int | None,
) -> list[dict[str, Any]]:
    if top_k is None:
        return scores

    grouped = _group_scores_by_pattern(scores)
    limited: list[dict[str, Any]] = []
    for pattern in sorted(grouped):
        limited.extend(grouped[pattern][:top_k])
    return sorted(
        limited,
        key=lambda item: (
            str(item.get("pattern") or ""),
            -float(item["score"]["total_score"]),
            str(item.get("patient_id") or ""),
            str(item.get("source_id") or ""),
            int(item.get("path_index") or 0),
        ),
    )


def _score_one_path(
    scoring_input: DirectEntityScoringInput,
    row: dict[str, Any],
) -> DirectPathScore:
    taskset = row.get("s") if isinstance(row.get("s"), dict) else {}
    patient = row.get("p") if isinstance(row.get("p"), dict) else {}
    rules = PathScoringRules()
    education_score, education_detail = _score_education(
        rules,
        scoring_input.education,
        taskset.get("执行学历"),
    )
    age_score, age_detail = _score_age(
        rules,
        scoring_input.age,
        taskset.get("执行年龄"),
    )
    gender_score, gender_detail = _score_gender(
        scoring_input.gender,
        patient.get("性别"),
    )
    scores = {
        "education": education_score,
        "age": age_score,
        "gender": gender_score,
    }
    weights = {"education": 0.4, "age": 0.4, "gender": 0.2}
    active_weights = {
        key: value for key, value in weights.items() if scores[key] is not None
    }
    weight_sum = sum(active_weights.values())
    used_weights = (
        {key: round(value / weight_sum, 4) for key, value in active_weights.items()}
        if weight_sum > 0
        else {}
    )
    total_score = round(
        sum((scores[key] or 0.0) * used_weights[key] for key in used_weights),
        2,
    )
    return DirectPathScore(
        total_score=total_score,
        education_score=education_score,
        age_score=age_score,
        gender_score=gender_score,
        used_weights=used_weights,
        details={
            "education": education_detail,
            "age": age_detail,
            "gender": gender_detail,
        },
    )


def _score_education(
    rules: PathScoringRules,
    source_education: object,
    target_education: object,
) -> tuple[float | None, str]:
    left = rules._map_education_rank(_optional_text(source_education))
    right = rules._map_education_rank(_optional_text(target_education))
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
    rules: PathScoringRules,
    source_age: object,
    target_age: object,
) -> tuple[float | None, str]:
    left = rules._parse_int(_optional_text(source_age))
    right = rules._parse_int(_optional_text(target_age))
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


def _score_gender(
    source_gender: object,
    target_gender: object,
) -> tuple[float | None, str]:
    left = _optional_text(source_gender)
    right = _optional_text(target_gender)
    if left is None or right is None:
        return None, "性别缺失，跳过该项"
    if left == right:
        return 100.0, "性别一致"
    return 0.0, "性别不一致"


def _source_refs_from_input(
    scoring_input: DirectEntityScoringInput,
) -> list[DirectSourceRef]:
    refs = []
    refs.extend(
        DirectSourceRef(PathPattern.DISEASE_TASKSET_PATIENT, source_id)
        for source_id in scoring_input.disease_ids
    )
    refs.extend(
        DirectSourceRef(PathPattern.SYMPTOM_TASKSET_PATIENT, source_id)
        for source_id in scoring_input.symptom_ids
    )
    refs.extend(
        DirectSourceRef(PathPattern.UNKNOWN_TASKSET_PATIENT, source_id)
        for source_id in scoring_input.unknown_ids
    )
    return refs


def _read_index(index_path: Path) -> dict[str, Any]:
    if not index_path.exists():
        raise FileNotFoundError(f"direct entity path index does not exist: {index_path}")
    with index_path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        raise ValueError(f"direct entity path index must be a mapping: {index_path}")
    return data


def save_scored_direct_entity_result(
    result: dict[str, Any],
    output_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> list[dict[str, Path]]:
    """Save full direct-entity score details and compact summary files."""
    output_paths = []
    for pattern, scores in _group_scores_by_pattern(result.get("scores")).items():
        pattern_result = _build_pattern_scored_result(result, pattern, scores)
        pattern_result["user_cache_context"] = build_scored_direct_entity_user_cache_context(
            pattern_result,
            config_path=config_path,
        )
        detail_path, summary_path = get_scored_direct_entity_output_paths(
            pattern_result,
            output_dir,
        )
        _write_json_atomic(detail_path, pattern_result)
        _write_json_atomic(summary_path, build_scored_direct_entity_summary(pattern_result))
        _register_scored_direct_entity_user_cache(
            pattern_result,
            detail_path,
            summary_path,
            config_path=config_path,
        )
        LOGGER.info(
            "Saved scored direct entity result: source_id=%s, pattern=%s, detail_path=%s, summary_path=%s",
            result.get("source_id"),
            pattern,
            detail_path,
            summary_path,
        )
        output_paths.append({"detail": detail_path, "summary": summary_path})
    return output_paths


def get_scored_direct_entity_output_paths(
    result: dict[str, Any],
    output_dir: str | Path = DEFAULT_SCORED_OUTPUT_DIR,
) -> tuple[Path, Path]:
    """Return detail and summary output paths for one direct entity score result."""
    source_id = _normalize_required_text(result.get("source_id"), "source_id")
    cache_context = result.get("cache_context")
    if not isinstance(cache_context, dict):
        raise ValueError("cache_context must be present before saving.")
    scored_key = _normalize_required_text(cache_context.get("scored_key"), "scored_key")
    pattern = _normalize_required_text(result.get("pattern"), "pattern")
    source_key = _normalize_required_text(
        result.get("direct_path_source_key"),
        "direct_path_source_key",
    )
    user_cache_context = result.get("user_cache_context")
    if isinstance(user_cache_context, dict) and user_cache_context.get("enabled"):
        output_base = patient_cache_leaf_dir(
            files_root_from_sqlite_path(
                _normalize_required_text(
                    user_cache_context.get("sqlite_path"),
                    "sqlite_path",
                )
            ),
            patient_id=user_cache_context.get("patient_id") or source_id,
            cache_type="scored_paths",
            query_family=user_cache_context.get("query_family"),
            window_days=user_cache_context.get("window_days"),
            config_hash=user_cache_context.get("config_hash"),
            cached_base_date=user_cache_context.get("cached_base_date"),
        )
        file_stem = f"{_slug_part(pattern)}__{_slug_part(source_key)}"
        return (
            output_base / f"{file_stem}.detail.json",
            output_base / f"{file_stem}.summary.json",
        )
    bucket = source_id[:2] or "unknown"
    output_base = Path(output_dir) / scored_key / pattern / source_key / bucket
    return (
        output_base / f"{source_id}.detail.json",
        output_base / f"{source_id}.summary.json",
    )


def build_scored_direct_entity_summary(result: dict[str, Any]) -> dict[str, Any]:
    """Build a compact direct-entity score summary without full path rows."""
    summary_scores = []
    raw_scores = result.get("scores")
    scores = raw_scores if isinstance(raw_scores, list) else []
    for rank, item in enumerate(scores, start=1):
        if not isinstance(item, dict):
            continue
        score = item.get("score")
        summary_scores.append(
            {
                "rank": rank,
                "pattern": item.get("pattern"),
                "source_id": item.get("source_id"),
                "path_index": item.get("path_index"),
                "patient_id": item.get("patient_id"),
                "taskset_id": item.get("taskset_id"),
                "training_date": item.get("training_date"),
                "total_score": score.get("total_score") if isinstance(score, dict) else None,
                "score": score if isinstance(score, dict) else {},
            }
        )
    return {
        "source_id": result.get("source_id"),
        "source_parameter": result.get("source_parameter"),
        "pattern": result.get("pattern"),
        "should_score": result.get("should_score"),
        "reason": result.get("reason"),
        "base_date": result.get("base_date"),
        "scoring_input": result.get("scoring_input"),
        "source_count": result.get("source_count"),
        "missing_sources": result.get("missing_sources"),
        "path_count": result.get("path_count"),
        "scored_path_count": result.get("scored_path_count"),
        "top_k": result.get("top_k"),
        "cache_context": result.get("cache_context"),
        "scores": summary_scores,
    }


def build_direct_entity_scored_cache_context(
    *,
    base_date: str,
    source_entries: list[dict[str, Any]],
    top_k: int | None,
) -> dict[str, Any]:
    """Build cache metadata for scored direct entity path results."""
    scored_key = (
        f"base_{_slug_part(base_date)}"
        f"_qf_direct_entity"
        f"_scoretopk_{top_k if top_k is not None else 'all'}"
    )
    pattern_source_keys = {
        pattern: _build_direct_path_source_key(entries)
        for pattern, entries in _group_entries_by_pattern(source_entries).items()
    }
    return {
        "cache_type": "scored_direct_entity_paths",
        "scored_key": scored_key,
        "base_date": base_date,
        "query_family": "direct_entity",
        "score_top_k": top_k,
        "pattern_source_keys": pattern_source_keys,
        "source_entries": source_entries,
    }


def _build_pattern_scored_result(
    result: dict[str, Any],
    pattern: str,
    scores: list[dict[str, Any]],
) -> dict[str, Any]:
    cache_context = result.get("cache_context")
    if not isinstance(cache_context, dict):
        raise ValueError("cache_context must be present before saving.")
    source_entries = [
        entry
        for entry in cache_context.get("source_entries", [])
        if isinstance(entry, dict) and entry.get("pattern") == pattern
    ]
    source_key = _build_direct_path_source_key(source_entries)
    pattern_cache_context = dict(cache_context)
    pattern_cache_context["direct_path_pattern"] = pattern
    pattern_cache_context["direct_path_source_key"] = source_key
    pattern_cache_context["source_entries"] = source_entries
    pattern_result = dict(result)
    pattern_result["pattern"] = pattern
    pattern_result["direct_path_source_key"] = source_key
    pattern_result["path_count"] = len(scores)
    pattern_result["scored_path_count"] = len(scores)
    pattern_result["cache_context"] = pattern_cache_context
    pattern_result["scores"] = scores
    return pattern_result


def build_scored_direct_entity_user_cache_context(
    result: dict[str, Any],
    *,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    """Build source-centered cache metadata for one direct-entity scored result."""
    settings = load_user_cache_settings(config_path)
    if not settings.enabled:
        return {"enabled": False, "cache_type": "scored_direct_entity_paths"}
    cache_context = result.get("cache_context")
    if not isinstance(cache_context, dict):
        raise ValueError("cache_context must be present before user-cache registration.")
    query_settings = load_query_settings(config_path)
    source_id = _normalize_required_text(result.get("source_id"), "source_id")
    source_key = _normalize_required_text(
        result.get("direct_path_source_key"),
        "direct_path_source_key",
    )
    scoring_input = result.get("scoring_input")
    profile_signature = _direct_scoring_profile_signature(scoring_input)
    scored_key = _normalize_required_text(cache_context.get("scored_key"), "scored_key")
    pattern = _normalize_required_text(result.get("pattern"), "pattern")
    return {
        "enabled": True,
        "cache_type": "scored_direct_entity_paths",
        "sqlite_path": settings.sqlite_path,
        "source_type": "direct_entity_profile",
        "source_id": source_id,
        "patient_id": source_id,
        "query_family": "direct_entity",
        "window_days": query_settings.direct_entity_path.window_days,
        "config_hash": _short_hash(
            {
                "cache_type": "scored_direct_entity_paths",
                "pattern": pattern,
                "direct_path_source_key": source_key,
                "score_top_k": cache_context.get("score_top_k"),
                "profile_signature": profile_signature,
            }
        ),
        "cached_base_date": _normalize_required_text(
            result.get("base_date"),
            "base_date",
        ),
        "valid_days": settings.direct_scored_paths_valid_days,
        "scored_key": scored_key,
        "direct_path_source_key": source_key,
        "pattern": pattern,
        "score_top_k": cache_context.get("score_top_k"),
        "profile_signature": profile_signature,
    }


def _register_scored_direct_entity_user_cache(
    result: dict[str, Any],
    detail_path: Path,
    summary_path: Path,
    *,
    config_path: str | Path,
) -> None:
    user_cache_context = build_scored_direct_entity_user_cache_context(
        result,
        config_path=config_path,
    )
    if not user_cache_context.get("enabled"):
        return
    store = UserCacheIndexStore(
        _normalize_required_text(user_cache_context.get("sqlite_path"), "sqlite_path")
    )
    entry = UserCacheEntry(
        cache_type="scored_direct_entity_paths",
        patient_id=_normalize_required_text(
            user_cache_context.get("patient_id"),
            "patient_id",
        ),
        query_family=_normalize_required_text(
            user_cache_context.get("query_family"),
            "query_family",
        ),
        window_days=_normalize_positive_int(
            user_cache_context.get("window_days"),
            "window_days",
        ),
        config_hash=_normalize_required_text(
            user_cache_context.get("config_hash"),
            "config_hash",
        ),
        cached_base_date=_normalize_required_text(
            user_cache_context.get("cached_base_date"),
            "cached_base_date",
        ),
        valid_days=_normalize_non_negative_int(
            user_cache_context.get("valid_days"),
            "valid_days",
        ),
        data_path=str(detail_path),
        payload={
            "scored_key": user_cache_context.get("scored_key"),
            "pattern": user_cache_context.get("pattern"),
            "direct_path_source_key": user_cache_context.get("direct_path_source_key"),
            "score_top_k": user_cache_context.get("score_top_k"),
            "profile_signature": user_cache_context.get("profile_signature"),
            "summary_path": str(summary_path),
        },
        source_type=_normalize_required_text(
            user_cache_context.get("source_type"),
            "source_type",
        ),
        source_id=_normalize_required_text(
            user_cache_context.get("source_id"),
            "source_id",
        ),
    )
    store.upsert_entry(entry)
    LOGGER.info(
        "Registered scored direct entity paths in user cache: source_type=%s, source_id=%s, pattern=%s, cached_base_date=%s, data_path=%s",
        entry.source_type,
        entry.source_id,
        result.get("pattern"),
        entry.cached_base_date,
        entry.data_path,
    )


def _build_direct_path_source_key(entries: list[dict[str, Any]]) -> str:
    entitybase = _collapse_metadata_value(entries, "base_date", "none")
    entitywindow = _collapse_metadata_value(entries, "window_days", "none")
    pathcfg = _collapse_path_config(entries)
    return (
        f"entitybase_{_slug_part(entitybase)}"
        f"_entitywindow_{_slug_part(entitywindow)}"
        f"_pathcfg_{_slug_part(pathcfg)}"
    )


def _group_entries_by_pattern(
    entries: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for entry in entries:
        pattern = _optional_text(entry.get("pattern"))
        if pattern is None:
            continue
        grouped.setdefault(pattern, []).append(entry)
    return grouped


def _group_scores_by_pattern(scores: object) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    if not isinstance(scores, list):
        return grouped
    for item in scores:
        if not isinstance(item, dict):
            continue
        pattern = _optional_text(item.get("pattern"))
        if pattern is None:
            continue
        grouped.setdefault(pattern, []).append(item)
    return grouped


def _collapse_metadata_value(
    entries: list[dict[str, Any]],
    field_name: str,
    fallback: str,
) -> str:
    values = sorted(
        {
            str(entry[field_name]).strip()
            for entry in entries
            if entry.get(field_name) is not None and str(entry[field_name]).strip()
        }
    )
    if not values:
        return fallback
    if len(values) == 1:
        return values[0]
    return f"mixed-{_short_hash(values)}"


def _collapse_path_config(entries: list[dict[str, Any]]) -> str:
    direct_hashes = []
    for entry in entries:
        raw_path_key = entry.get("path_key")
        if not isinstance(raw_path_key, str):
            continue
        marker = "_directcfg_"
        if marker in raw_path_key:
            direct_hashes.append(raw_path_key.rsplit(marker, 1)[-1].strip())
    direct_hashes = sorted({value for value in direct_hashes if value})
    if len(direct_hashes) == 1:
        return direct_hashes[0]
    if direct_hashes:
        return f"mixed-{_short_hash(direct_hashes)}"
    return _short_hash(
        [
            {
                "direct_path_limit": entry.get("direct_path_limit"),
                "window_days": entry.get("window_days"),
            }
            for entry in entries
        ]
    )


def _scored_source_id(scoring_input: DirectEntityScoringInput) -> str:
    if scoring_input.patient_id:
        return scoring_input.patient_id
    return f"manual_{_short_hash(scoring_input.to_dict())}"


def _load_stored_result(path: Path) -> StoredPatternResult:
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    return StoredPatternResult.from_dict(data)


def _path_row(path: object) -> dict[str, Any]:
    if not isinstance(path, dict):
        return {}
    row = path.get("row")
    return row if isinstance(row, dict) else path


def _resolve_top_k(
    cli_top_k: int | None,
    config_top_k: int | None,
) -> int | None:
    top_k = cli_top_k if cli_top_k is not None else config_top_k
    if top_k is not None and top_k <= 0:
        raise ValueError("top_k must be a positive integer.")
    return top_k


def _direct_scoring_profile_signature(scoring_input: object) -> str:
    if isinstance(scoring_input, dict):
        payload = {
            "age": scoring_input.get("age"),
            "education": scoring_input.get("education"),
            "gender": scoring_input.get("gender"),
            "disease_ids": scoring_input.get("disease_ids"),
            "symptom_ids": scoring_input.get("symptom_ids"),
            "unknown_ids": scoring_input.get("unknown_ids"),
        }
    else:
        payload = {}
    return _short_hash(payload)


def _normalize_positive_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{field_name} must be a positive integer.")
    return value


def _normalize_non_negative_int(value: object, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{field_name} must be a non-negative integer.")
    return value


def _flatten_ids(values: list[list[str]]) -> list[str]:
    ids: list[str] = []
    for group in values:
        for value in group:
            normalized = _optional_text(value)
            if normalized is not None:
                ids.append(normalized)
    return ids


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_required_text(value: object, field_name: str) -> str:
    normalized = _optional_text(value)
    if normalized is None:
        raise ValueError(f"{field_name} must be a non-empty string.")
    return normalized


def _short_hash(payload: object) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:8]


def _slug_part(value: object) -> str:
    text = str(value).strip().lower()
    slug = []
    for char in text:
        if char.isalnum():
            slug.append(char)
        elif char in ("-", "_"):
            slug.append(char)
        else:
            slug.append("-")
    return "".join(slug).strip("-") or "none"


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )


def _write_json_atomic(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=f"{path.stem}.",
        suffix=".tmp",
        delete=False,
    ) as temp_file:
        temp_file.write(serialized)
        temp_path = Path(temp_file.name)
    os.replace(temp_path, path)


def main() -> int:
    """Score direct entity paths and emit JSON."""
    args = parse_args()
    try:
        result = score_direct_entity_paths(
            config_path=args.config,
            patient_id=args.patient_id,
            base_date=args.base_date,
            age=args.age,
            education=args.education,
            gender=args.gender,
            disease_ids=_flatten_ids(args.disease_id),
            symptom_ids=_flatten_ids(args.symptom_id),
            unknown_ids=_flatten_ids(args.unknown_id),
            top_k=args.top_k,
        )
        if not args.no_save and result.get("should_score") is True:
            output_paths = save_scored_direct_entity_result(
                result,
                output_dir=args.scored_paths_dir,
                config_path=args.config,
            )
            result["output_paths"] = [
                {
                    "detail": str(paths["detail"]),
                    "summary": str(paths["summary"]),
                }
                for paths in output_paths
            ]
        if args.output:
            _write_json(Path(args.output), result)
    except Exception as exc:
        LOGGER.exception("Score direct entity paths failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
