"""User-facing service orchestration."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from config.settings import (
    DEFAULT_CONFIG_PATH,
    load_query_settings,
    load_user_cache_settings,
)

from ..domain.graph_schema import PathPattern
from ..data_access.kg_repository import KgRepository, PatternQueryFamily
from ..data_access.user_cache_index import UserCacheEntry, UserCacheIndexStore
from ..data_access.pattern_registry import (
    PatternQueryMode,
    get_path_pattern_spec,
)
from .direct_path_provider import DirectPathProvider
from ..utils.logger import get_logger
from ..utils.user_cache_paths import files_root_from_sqlite_path, patient_cache_leaf_dir


LOGGER = get_logger(__name__)
PROFILE_CANDIDATE_TASKS_CACHE_TYPE = "profile_candidate_tasks"
PROFILE_CANDIDATE_TASKS_QUERY_NAME = (
    "patient_profile_gender_education_age_windowed_exclusive_task_game"
)
PROFILE_CANDIDATE_TASKS_QUERY_NAME_UNWINDOWED = (
    "patient_profile_gender_education_age_exclusive_task_game"
)


@dataclass
class UserService:
    """Application-facing helpers built on top of repository reads."""

    kg_repository: KgRepository

    def get_patient_ids(self) -> list[str]:
        """Return all patient IDs in the graph."""
        return self.kg_repository.get_patient_ids()

    def get_patient_ids_with_training_on_date(
        self,
        base_date: str,
        limit: int | None = None,
    ) -> list[str]:
        """Return patient IDs with training records on base_date."""
        return self.kg_repository.get_patient_ids_with_training_on_date(
            base_date,
            limit,
        )

    def get_source_patient_ids_with_secondary_ability_scores(self) -> list[str]:
        """Return source patient IDs with secondary ability training records."""
        return self.kg_repository.get_source_patient_ids_with_secondary_ability_scores()

    def get_distinct_training_games(self) -> list[dict[str, object]]:
        """Return distinct games that appear in training records."""
        return self.kg_repository.get_distinct_training_games()

    def get_patient_profile_entities_by_effective_date(
        self,
        patient_id: str,
        base_date: str,
    ) -> list[dict[str, object]]:
        """Return profile entities on the nearest effective date for a patient."""
        return self.kg_repository.get_patient_profile_entities_by_effective_date(
            patient_id,
            base_date,
        )

    def get_patient_direct_entity_scoring_profile(
        self,
        patient_id: str,
        base_date: str,
    ) -> list[dict[str, object]]:
        """Return profile fields used by fallback and direct-entity scoring."""
        return self.kg_repository.get_patient_direct_entity_scoring_profile(
            patient_id,
            base_date,
        )

    def get_patient_profile_gender_education_age_exclusive_task_games(
        self,
        patient_id: str,
        base_date: str,
        age_window: int,
    ) -> list[dict[str, object]]:
        """Return exclusive-task games matching patient profile and age window."""
        return self.kg_repository.get_patient_profile_gender_education_age_exclusive_task_games(
            patient_id,
            base_date,
            age_window,
        )

    def get_disease_education_age_exclusive_task_games(
        self,
        disease_id: str,
        education: str,
        min_age: int,
        max_age: int,
    ) -> list[dict[str, object]]:
        """Return exclusive-task games matching disease, education, and age range."""
        return self.kg_repository.get_disease_education_age_exclusive_task_games(
            disease_id,
            education,
            min_age,
            max_age,
        )

    def get_symptom_education_age_exclusive_task_games(
        self,
        symptom_id: str,
        education: str,
        min_age: int,
        max_age: int,
    ) -> list[dict[str, object]]:
        """Return exclusive-task games matching symptom, education, and age range."""
        return self.kg_repository.get_symptom_education_age_exclusive_task_games(
            symptom_id,
            education,
            min_age,
            max_age,
        )

    def get_unknown_education_age_exclusive_task_games(
        self,
        unknown_id: str,
        education: str,
        min_age: int,
        max_age: int,
    ) -> list[dict[str, object]]:
        """Return exclusive-task games matching unknown, education, and age range."""
        return self.kg_repository.get_unknown_education_age_exclusive_task_games(
            unknown_id,
            education,
            min_age,
            max_age,
        )

    def get_patient_profile_candidate_training_games(
        self,
        patient_id: str,
        base_date: str,
        age_window: int = 0,
        profile_candidate_training_window_days: int | None = None,
    ) -> list[dict[str, object]]:
        """Return exclusive-task games matching patient profile filters."""
        cached_rows = self._load_patient_profile_candidate_training_games_cache(
            patient_id=patient_id,
            base_date=base_date,
            age_window=age_window,
            profile_candidate_training_window_days=profile_candidate_training_window_days,
        )
        if cached_rows is not None:
            return cached_rows

        if profile_candidate_training_window_days is not None:
            rows = self.kg_repository.get_patient_profile_gender_education_age_windowed_exclusive_task_games(
                patient_id,
                base_date,
                age_window,
                profile_candidate_training_window_days,
            )
        else:
            rows = self.get_patient_profile_gender_education_age_exclusive_task_games(
                patient_id,
                base_date,
                age_window,
            )
        self._save_patient_profile_candidate_training_games_cache(
            rows,
            patient_id=patient_id,
            base_date=base_date,
            age_window=age_window,
            profile_candidate_training_window_days=profile_candidate_training_window_days,
        )
        return rows

    def _load_patient_profile_candidate_training_games_cache(
        self,
        *,
        patient_id: str,
        base_date: str,
        age_window: int,
        profile_candidate_training_window_days: int | None,
    ) -> list[dict[str, object]] | None:
        context = self._build_profile_candidate_tasks_cache_context(
            patient_id=patient_id,
            base_date=base_date,
            age_window=age_window,
            profile_candidate_training_window_days=profile_candidate_training_window_days,
        )
        if context is None:
            return None
        store = UserCacheIndexStore(context["sqlite_path"])
        entry = store.find_latest_valid_source_entry(
            cache_type=PROFILE_CANDIDATE_TASKS_CACHE_TYPE,
            source_type="patient",
            source_id=context["patient_id"],
            query_family=context["query_family"],
            window_days=context["window_days"],
            config_hash=context["config_hash"],
            request_base_date=context["cached_base_date"],
        )
        if entry is None:
            return None
        data_path = Path(entry.data_path)
        if not data_path.exists():
            store.delete_entry(entry)
            LOGGER.warning(
                "Deleted stale profile candidate task cache index entry because file is missing: patient_id=%s, data_path=%s",
                entry.patient_id,
                data_path,
            )
            return None
        with data_path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
        rows = payload.get("rows") if isinstance(payload, dict) else None
        if not isinstance(rows, list):
            store.delete_entry(entry)
            LOGGER.warning(
                "Deleted invalid profile candidate task cache index entry because rows are missing: patient_id=%s, data_path=%s",
                entry.patient_id,
                data_path,
            )
            return None
        LOGGER.info(
            "Profile candidate training games cache hit: patient_id=%s, base_date=%s, row_count=%s, data_path=%s",
            context["patient_id"],
            context["cached_base_date"],
            len(rows),
            data_path,
        )
        return [row for row in rows if isinstance(row, dict)]

    def _save_patient_profile_candidate_training_games_cache(
        self,
        rows: list[dict[str, object]],
        *,
        patient_id: str,
        base_date: str,
        age_window: int,
        profile_candidate_training_window_days: int | None,
    ) -> None:
        context = self._build_profile_candidate_tasks_cache_context(
            patient_id=patient_id,
            base_date=base_date,
            age_window=age_window,
            profile_candidate_training_window_days=profile_candidate_training_window_days,
        )
        if context is None:
            return
        safe_rows = [_json_safe(row) for row in rows]
        leaf_dir = patient_cache_leaf_dir(
            files_root_from_sqlite_path(context["sqlite_path"]),
            patient_id=context["patient_id"],
            cache_type=PROFILE_CANDIDATE_TASKS_CACHE_TYPE,
            query_family=context["query_family"],
            window_days=context["window_days"],
            config_hash=context["config_hash"],
            cached_base_date=context["cached_base_date"],
        )
        leaf_dir.mkdir(parents=True, exist_ok=True)
        data_path = leaf_dir / "games.json"
        payload = {
            "cache_type": PROFILE_CANDIDATE_TASKS_CACHE_TYPE,
            "query_name": context["query_family"],
            "patient_id": context["patient_id"],
            "base_date": context["cached_base_date"],
            "age_window": age_window,
            "profile_candidate_training_window_days": (
                profile_candidate_training_window_days
            ),
            "row_count": len(safe_rows),
            "rows": safe_rows,
        }
        data_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
            encoding="utf-8",
        )
        entry = UserCacheEntry(
            cache_type=PROFILE_CANDIDATE_TASKS_CACHE_TYPE,
            patient_id=context["patient_id"],
            query_family=context["query_family"],
            window_days=context["window_days"],
            config_hash=context["config_hash"],
            cached_base_date=context["cached_base_date"],
            valid_days=context["valid_days"],
            data_path=str(data_path),
            payload={
                "age_window": age_window,
                "profile_candidate_training_window_days": (
                    profile_candidate_training_window_days
                ),
                "row_count": len(safe_rows),
            },
            source_type="patient",
            source_id=context["patient_id"],
        )
        UserCacheIndexStore(context["sqlite_path"]).upsert_entry(entry)
        LOGGER.info(
            "Registered profile candidate training games in user cache: patient_id=%s, base_date=%s, row_count=%s, data_path=%s",
            context["patient_id"],
            context["cached_base_date"],
            len(safe_rows),
            data_path,
        )

    def _build_profile_candidate_tasks_cache_context(
        self,
        *,
        patient_id: str,
        base_date: str,
        age_window: int,
        profile_candidate_training_window_days: int | None,
    ) -> dict[str, Any] | None:
        settings = load_user_cache_settings(self.kg_repository.config_path)
        if not settings.enabled:
            return None
        normalized_patient_id = str(patient_id).strip()
        normalized_base_date = str(base_date).strip()
        if not normalized_patient_id or not normalized_base_date:
            return None
        query_family = (
            PROFILE_CANDIDATE_TASKS_QUERY_NAME
            if profile_candidate_training_window_days is not None
            else PROFILE_CANDIDATE_TASKS_QUERY_NAME_UNWINDOWED
        )
        window_days = _profile_candidate_cache_window_days(
            profile_candidate_training_window_days
        )
        config_hash = _short_hash(
            {
                "cache_type": PROFILE_CANDIDATE_TASKS_CACHE_TYPE,
                "patient_id": normalized_patient_id,
                "age_window": age_window,
                "profile_candidate_training_window_days": (
                    profile_candidate_training_window_days
                ),
                "query_name": query_family,
                "schema_version": 1,
            }
        )
        return {
            "sqlite_path": settings.sqlite_path,
            "patient_id": normalized_patient_id,
            "query_family": query_family,
            "window_days": window_days,
            "config_hash": config_hash,
            "cached_base_date": normalized_base_date,
            "valid_days": settings.profile_candidate_tasks_valid_days,
        }

    @staticmethod
    def _extend_profile_candidate_games(
        game_rows: list[dict[str, object]],
        seen_game_ids: set[str],
        expansion_rows: list[dict[str, object]],
    ) -> None:
        for expansion_row in expansion_rows:
            game = _extract_expansion_game(expansion_row)
            game_id = _node_identifier(game)
            if not game_id or game_id in seen_game_ids:
                continue
            game_rows.append({"g": game})
            seen_game_ids.add(game_id)

    def get_patient_training_date_games_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return training-date grouped games from the given start date."""
        return self.kg_repository.get_patient_training_date_games_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_distinct_games_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct games for one patient before an end date."""
        return self.kg_repository.get_patient_distinct_games_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_distinct_games_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct games for one patient from a start date."""
        return self.kg_repository.get_patient_distinct_games_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_distinct_games_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct games for one patient within a date range."""
        return self.kg_repository.get_patient_distinct_games_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_games_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game rows for one patient before an end date."""
        return self.kg_repository.get_patient_games_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_games_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return game rows for one patient from a start date."""
        return self.kg_repository.get_patient_games_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_games_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game rows for one patient within a date range."""
        return self.kg_repository.get_patient_games_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_game_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game sets for two patients before an end date."""
        return self.kg_repository.get_patient_game_set_comparison_by_end_date(
            primary_patient_id,
            comparison_patient_id,
            end_date,
        )

    def get_patient_game_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return game sets for two patients from a start date."""
        return self.kg_repository.get_patient_game_set_comparison_by_start_date(
            primary_patient_id,
            comparison_patient_id,
            start_date,
        )

    def get_patient_game_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game sets for two patients within a date range."""
        return self.kg_repository.get_patient_game_set_comparison_by_date_range(
            primary_patient_id,
            comparison_patient_id,
            start_date,
            end_date,
        )

    def get_patient_game_norm_score_series_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return game-level norm-score series for two patients before an end date."""
        return self.kg_repository.get_patient_game_norm_score_series_comparison_by_end_date(
            primary_patient_id,
            comparison_patient_id,
            end_date,
        )

    def get_patient_secondary_ability_scores_by_disease_course_window(
        self,
        patient_id: str,
        base_date: str,
        disease_course_window_days: int,
    ) -> list[dict[str, object]]:
        """Return secondary ability scores in a disease-course window."""
        return self.kg_repository.get_patient_secondary_ability_scores_by_disease_course_window(
            patient_id,
            base_date,
            disease_course_window_days,
        )

    def get_patient_total_scores_by_disease_course_window(
        self,
        patient_id: str,
        base_date: str,
        disease_course_window_days: int,
    ) -> list[dict[str, object]]:
        """Return total scores in a disease-course window."""
        return self.kg_repository.get_patient_total_scores_by_disease_course_window(
            patient_id,
            base_date,
            disease_course_window_days,
        )

    def get_patient_distinct_task_instances_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct task instances for one patient from a start date."""
        return self.kg_repository.get_patient_distinct_task_instances_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_distinct_task_instances_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct task instances for one patient before an end date."""
        return self.kg_repository.get_patient_distinct_task_instances_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_distinct_task_instances_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct task instances for one patient within a date range."""
        return self.kg_repository.get_patient_distinct_task_instances_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_distinct_symptoms_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct symptoms for one patient before an end date."""
        return self.kg_repository.get_patient_distinct_symptoms_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_symptom_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return symptom sets for two patients before an end date."""
        return self.kg_repository.get_patient_symptom_set_comparison_by_end_date(
            primary_patient_id,
            comparison_patient_id,
            end_date,
        )

    def get_patient_distinct_symptoms_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct symptoms for one patient from a start date."""
        return self.kg_repository.get_patient_distinct_symptoms_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_symptom_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return symptom sets for two patients from a start date."""
        return self.kg_repository.get_patient_symptom_set_comparison_by_start_date(
            primary_patient_id,
            comparison_patient_id,
            start_date,
        )

    def get_patient_distinct_symptoms_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct symptoms for one patient within a date range."""
        return self.kg_repository.get_patient_distinct_symptoms_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_symptom_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return symptom sets for two patients within a date range."""
        return self.kg_repository.get_patient_symptom_set_comparison_by_date_range(
            primary_patient_id,
            comparison_patient_id,
            start_date,
            end_date,
        )

    def get_patient_distinct_diseases_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct diseases for one patient before an end date."""
        return self.kg_repository.get_patient_distinct_diseases_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_disease_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return disease sets for two patients before an end date."""
        return self.kg_repository.get_patient_disease_set_comparison_by_end_date(
            primary_patient_id,
            comparison_patient_id,
            end_date,
        )

    def get_patient_disease_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return disease sets for two patients from a start date."""
        return self.kg_repository.get_patient_disease_set_comparison_by_start_date(
            primary_patient_id,
            comparison_patient_id,
            start_date,
        )

    def get_patient_disease_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return disease sets for two patients within a date range."""
        return self.kg_repository.get_patient_disease_set_comparison_by_date_range(
            primary_patient_id,
            comparison_patient_id,
            start_date,
            end_date,
        )

    def get_patient_distinct_diseases_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct diseases for one patient from a start date."""
        return self.kg_repository.get_patient_distinct_diseases_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_distinct_diseases_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct diseases for one patient within a date range."""
        return self.kg_repository.get_patient_distinct_diseases_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_distinct_unknowns_by_end_date(
        self,
        patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct unknown-category nodes for one patient before an end date."""
        return self.kg_repository.get_patient_distinct_unknowns_by_end_date(
            patient_id,
            end_date,
        )

    def get_patient_unknown_set_comparison_by_end_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return unknown-category sets for two patients before an end date."""
        return self.kg_repository.get_patient_unknown_set_comparison_by_end_date(
            primary_patient_id,
            comparison_patient_id,
            end_date,
        )

    def get_patient_distinct_unknowns_by_start_date(
        self,
        patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct unknown-category nodes for one patient from a start date."""
        return self.kg_repository.get_patient_distinct_unknowns_by_start_date(
            patient_id,
            start_date,
        )

    def get_patient_unknown_set_comparison_by_start_date(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
    ) -> list[dict[str, object]]:
        """Return unknown-category sets for two patients from a start date."""
        return self.kg_repository.get_patient_unknown_set_comparison_by_start_date(
            primary_patient_id,
            comparison_patient_id,
            start_date,
        )

    def get_patient_distinct_unknowns_by_date_range(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return distinct unknown-category nodes for one patient within a date range."""
        return self.kg_repository.get_patient_distinct_unknowns_by_date_range(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_unknown_set_comparison_by_date_range(
        self,
        primary_patient_id: str,
        comparison_patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return unknown-category sets for two patients within a date range."""
        return self.kg_repository.get_patient_unknown_set_comparison_by_date_range(
            primary_patient_id,
            comparison_patient_id,
            start_date,
            end_date,
        )

    def get_pattern_paths(
        self,
        source_id: str,
        base_date: str,
        window_days: int,
        pattern: PathPattern | str = PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        query_family: PatternQueryFamily | str | None = None,
    ) -> dict[str, Any]:
        """Run the end-to-end fixed-pattern path flow for one source node."""
        normalized_source_id = self._normalize_required_string(source_id, "source_id")
        spec = get_path_pattern_spec(pattern)
        normalized_pattern = spec.pattern
        path_window = self._build_path_window(base_date, window_days)
        LOGGER.info(
            "Starting pattern path flow in service: source_id=%s, source_parameter=%s, pattern=%s, query_mode=%s, base_date=%s, window_days=%s",
            normalized_source_id,
            spec.source_parameter,
            normalized_pattern.value,
            spec.query_mode.value,
            path_window["base_date"],
            path_window["window_days"],
        )

        if spec.query_mode == PatternQueryMode.DIRECT_PATH:
            if query_family is not None:
                raise ValueError(
                    f"Pattern {normalized_pattern.value} does not support query_family."
                )
            return self._get_direct_pattern_paths(
                source_id=normalized_source_id,
                pattern=normalized_pattern,
                source_parameter=spec.source_parameter,
                path_window=path_window,
            )
        elif spec.query_mode == PatternQueryMode.PAIRED_STATISTICS:
                return self._get_paired_statistics_pattern_paths(
                    source_id=normalized_source_id,
                    pattern=normalized_pattern,
                    source_parameter=spec.source_parameter,
                    query_family=query_family,
                    path_window=path_window,
                )
        else:
            raise ValueError(
                f"Unsupported pattern query mode for {normalized_pattern.value}: "
                f"{spec.query_mode}"
            )

    def _get_paired_statistics_pattern_paths(
        self,
        *,
        source_id: str,
        pattern: PathPattern,
        source_parameter: str,
        query_family: PatternQueryFamily | str | None,
        path_window: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a statistics-guided randomized path query for one pattern family."""
        normalized_query_family = (
            PatternQueryFamily.TRAINING_ORDER_SOURCE_WINDOW
            if query_family is None
            else self._normalize_pattern_query_family(query_family)
        )
        source_context = self._build_source_context(
            source_id,
            source_parameter,
        )
        self._log_source_context(source_context)

        statistics, active_statistics = self._load_window_statistics(
            source_id,
            pattern,
            normalized_query_family,
            path_window,
        )

        group_count = self._extract_pattern_group_count(
            pattern,
            active_statistics,
        )
        raw_total_paths = active_statistics.get("totalPaths")
        total_paths = (
            None
            if raw_total_paths is None
            else int(raw_total_paths or 0)
        )
        p2_count = int(active_statistics.get("p2Count") or 0)

        if group_count <= 0:
            LOGGER.warning(
                "No available paths after statistics evaluation: source_id=%s, active_statistics=%s",
                source_id,
                active_statistics,
            )
            return self._build_pattern_result(
                source_context=source_context,
                pattern=pattern,
                query_family=normalized_query_family,
                statistics=statistics,
                limit_recommendation=None,
                paths=[],
            )

        recommendation = self.kg_repository.recommend_graph_path_limit(
            total_paths=total_paths,
            g_count=group_count,
            p2_count=p2_count,
        )

        limit_recommendation = {
            "per_g": recommendation.per_g,
            "limit": recommendation.limit,
        }

        LOGGER.info(
            "Calculated path limit recommendation: source_id=%s, per_g=%s, limit=%s",
            source_id,
            recommendation.per_g,
            recommendation.limit,
        )

        if recommendation.limit <= 0:
            LOGGER.warning(
                "Recommendation limit is non-positive: source_id=%s, limit_recommendation=%s",
                source_id,
                limit_recommendation,
            )
            return self._build_pattern_result(
                source_context=source_context,
                pattern=pattern,
                query_family=normalized_query_family,
                statistics=statistics,
                limit_recommendation=limit_recommendation,
                paths=[],
            )

        paths = self.kg_repository.get_pattern_randomized_paths(
            pattern=pattern,
            query_family=normalized_query_family,
            patient_id=source_id,
            start_date=path_window["start_date"],
            end_date=path_window["end_date"],
            per_group=recommendation.per_g,
            limit=recommendation.limit,
        )

        LOGGER.info(
            "Loaded randomized paths: source_id=%s, path_count=%s",
            source_id,
            len(paths),
        )

        LOGGER.debug(
            "Pattern path flow result in service: source_id=%s, statistics_summary=%s, limit_recommendation=%s",
            source_id,
            self._summarize_statistics_for_logging(statistics),
            limit_recommendation,
        )

        return self._build_pattern_result(
            source_context=source_context,
            pattern=pattern,
            query_family=normalized_query_family,
            statistics=statistics,
            limit_recommendation=limit_recommendation,
            paths=paths,
        )

    def _get_direct_pattern_paths(
        self,
        *,
        source_id: str,
        pattern: PathPattern,
        source_parameter: str,
        path_window: dict[str, Any],
    ) -> dict[str, Any]:
        """Run a direct path query for a source-driven pattern."""
        paths = DirectPathProvider(
            kg_repository=self.kg_repository,
            config_path=self.kg_repository.config_path,
        ).get_randomized_paths(
            pattern=pattern,
            source_id=source_id,
            start_date=path_window["start_date"],
            end_date=path_window["end_date"],
        )

        LOGGER.info(
            "Loaded direct randomized paths: source_id=%s, pattern=%s, path_count=%s",
            source_id,
            pattern.value,
            len(paths),
        )
        statistics = {
            "base_date": path_window["base_date"],
            "query_family": None,
            "path_window": path_window,
            "window_statistics": None,
        }
        return self._build_pattern_result(
            source_context=self._build_source_context(source_id, source_parameter),
            pattern=pattern,
            query_family=None,
            statistics=statistics,
            limit_recommendation=None,
            paths=paths,
        )

    def get_patient_ordered_training_dates(self, patient_id: str) -> list[str]:
        """Return only the ordered TaskInstanceSet training dates for a patient."""
        records = self.kg_repository.get_patient_task_instance_set_ordered_training_dates(
            patient_id
        )
        if not records:
            return []

        ordered_dates = records[0].get("orderedDatesa", [])
        if not isinstance(ordered_dates, list):
            return []

        return [str(value) for value in ordered_dates]

    def get_patient_total_score_timepoints(
        self,
        patient_id: str,
    ) -> list[dict[str, object]]:
        """Return TaskInstanceSet timepoints that have total scores for one patient."""
        return self.kg_repository.get_patient_total_score_timepoints(patient_id)

    def get_patient_total_score_by_date(
        self,
        patient_id: str,
        training_date: str,
    ) -> dict[str, object] | None:
        """Return one patient's total score on a specific training date."""
        records = self.kg_repository.get_patient_total_score_by_date(
            patient_id,
            training_date,
        )
        if not records:
            return None
        return _normalize_total_score_timepoint(records[0])

    def find_patient_total_score_timepoint_matches(
        self,
        source_patient_id: str,
        source_training_date: str,
        comparison_patient_ids: list[str],
        *,
        tolerance: float | None = None,
    ) -> list[dict[str, object]]:
        """Batch-match comparison patient timepoints by a source date total score."""
        normalized_source_patient_id = self._normalize_required_string(
            source_patient_id,
            "source_patient_id",
        )
        normalized_source_training_date = _parse_date_value(
            source_training_date,
            "source_training_date",
        )
        normalized_comparison_patient_ids = [
            self._normalize_required_string(patient_id, "comparison_patient_id")
            for patient_id in comparison_patient_ids
        ]
        normalized_tolerance = _normalize_optional_non_negative_float(
            tolerance,
            "tolerance",
        )

        disease_course_window_days = self._get_disease_course_window_days()
        if disease_course_window_days is None:
            LOGGER.warning(
                "Skipped total-score timepoint matching because disease_course_window_days is missing: source_patient_id=%s, source_training_date=%s",
                normalized_source_patient_id,
                normalized_source_training_date.isoformat(),
            )
            return []

        source_total_score_rows = self.get_patient_total_scores_by_disease_course_window(
            normalized_source_patient_id,
            normalized_source_training_date.isoformat(),
            disease_course_window_days,
        )
        source_total_score_summary = _aggregate_total_score_rows(source_total_score_rows)
        if source_total_score_summary is None:
            return []

        source_score = float(source_total_score_summary["total_score"])
        source_timepoint = {
            "instance_set_id": None,
            "training_date": normalized_source_training_date.isoformat(),
            **source_total_score_summary,
        }
        match_top_k = self._get_total_score_match_top_k()
        matches: list[dict[str, object]] = []
        for comparison_patient_id in normalized_comparison_patient_ids:
            matched_timepoints = self._find_comparison_total_score_timepoint_matches(
                source_patient_id=normalized_source_patient_id,
                source_timepoint=source_timepoint,
                source_score=source_score,
                source_date=normalized_source_training_date,
                comparison_patient_id=comparison_patient_id,
                match_top_k=match_top_k,
                disease_course_window_days=disease_course_window_days,
                tolerance=normalized_tolerance,
            )
            matches.extend(matched_timepoints)
        return matches

    def _find_comparison_total_score_timepoint_matches(
        self,
        *,
        source_patient_id: str,
        source_timepoint: dict[str, object],
        source_score: float,
        source_date: date,
        comparison_patient_id: str,
        match_top_k: int,
        disease_course_window_days: int | None,
        tolerance: float | None,
    ) -> list[dict[str, object]]:
        """Find one comparison patient's nearest total-score timepoints."""
        comparison_timepoints = [
            timepoint
            for timepoint in (
                _normalize_total_score_timepoint(record)
                for record in self.get_patient_total_score_timepoints(
                    comparison_patient_id
                )
            )
            if timepoint is not None
        ]
        if not comparison_timepoints:
            return []

        matched_timepoints = sorted(
            comparison_timepoints,
            key=lambda timepoint: _total_score_match_sort_key(
                source_score,
                source_date,
                timepoint,
            ),
        )[:match_top_k]

        matches: list[dict[str, object]] = []
        for matched_timepoint in matched_timepoints:
            score_delta = abs(float(matched_timepoint["total_score"]) - source_score)
            if tolerance is not None and score_delta > tolerance:
                continue
            matches.append(
                {
                    "source": {
                        "patient_id": source_patient_id,
                        **source_timepoint,
                    },
                    "matched": {
                        "patient_id": comparison_patient_id,
                        **matched_timepoint,
                        "recommended_date": _build_recommended_date(
                            matched_timepoint.get("training_date"),
                            disease_course_window_days,
                        ),
                    },
                    "score_delta": round(score_delta, 6),
                }
            )
        return matches

    def _get_total_score_match_top_k(self) -> int:
        """Return configured number of total-score match points per comparison patient."""
        config_path = vars(self.kg_repository).get("config_path", DEFAULT_CONFIG_PATH)
        return load_query_settings(config_path).candidate_ranking.total_score_match_top_k

    def _get_disease_course_window_days(self) -> int | None:
        """Return configured disease-course window days for date recommendations."""
        config_path = vars(self.kg_repository).get("config_path", DEFAULT_CONFIG_PATH)
        return load_query_settings(
            config_path
        ).candidate_ranking.disease_course_window_days

    def get_patient_training_task_history(
        self,
        patient_id: str,
    ) -> list[dict[str, object]]:
        """Return dated task-instance and game rows for one patient."""
        return self.kg_repository.get_patient_training_task_history(patient_id)

    def get_patient_training_task_history_by_date_window(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return task history in a left-closed, right-open date window."""
        return self.kg_repository.get_patient_training_task_history_by_date_window(
            patient_id,
            start_date,
            end_date,
        )

    def get_patient_exclusive_training_task_history_by_date_window(
        self,
        patient_id: str,
        start_date: str,
        end_date: str,
    ) -> list[dict[str, object]]:
        """Return exclusive-task history in a left-closed, right-open date window."""
        return (
            self.kg_repository.get_patient_exclusive_training_task_history_by_date_window(
                patient_id,
                start_date,
                end_date,
            )
        )

    def resolve_direct_entity_name(
        self,
        entity_name: str,
    ) -> list[dict[str, object]]:
        """Resolve a user-entered entity name to Disease/Symptom/Unknown IDs."""
        return self.kg_repository.resolve_direct_entity_name(entity_name)

    def get_direct_entity_alias_index(self) -> list[dict[str, object]]:
        """Return Disease/Symptom/Unknown standard names and aliases."""
        return self.kg_repository.get_direct_entity_alias_index()

    def get_profile_matched_exclusive_tasks(
        self,
        *,
        base_date: str,
        age: int | None,
        min_age: int | None,
        max_age: int | None,
        gender: str | None,
        education: str | None,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return fallback exclusive tasks matching available profile fields."""
        return self.kg_repository.get_profile_matched_exclusive_tasks(
            base_date=base_date,
            age=age,
            min_age=min_age,
            max_age=max_age,
            gender=gender,
            education=education,
            limit=limit,
        )

    def get_global_popular_exclusive_tasks(
        self,
        *,
        base_date: str,
        limit: int,
    ) -> list[dict[str, object]]:
        """Return globally popular exclusive tasks for fallback recommendation."""
        return self.kg_repository.get_global_popular_exclusive_tasks(
            base_date=base_date,
            limit=limit,
        )

    def _load_window_statistics(
        self,
        patient_id: str,
        pattern: PathPattern,
        query_family: PatternQueryFamily,
        path_window: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, int]]:
        """Load path statistics for the configured left-closed, right-open window."""
        statistics_records = (
            self.kg_repository.get_pattern_statistics(
                pattern=pattern,
                query_family=query_family,
                patient_id=patient_id,
                start_date=path_window["start_date"],
                end_date=path_window["end_date"],
            )
        )

        window_statistics = self._extract_statistics(statistics_records)
        statistics = {
            "base_date": path_window["base_date"],
            "query_family": query_family.value,
            "path_window": path_window,
            "window_statistics": window_statistics,
        }

        LOGGER.info(
            "Loaded path window statistics: patient_id=%s, path_window=%s, window_statistics=%s",
            patient_id,
            path_window,
            window_statistics,
        )

        return statistics, window_statistics

    @staticmethod
    def _build_source_context(
        source_id: str,
        source_parameter: str,
    ) -> dict[str, Any]:
        """Build a normalized context payload for path generation."""
        context: dict[str, Any] = {
            "source_id": source_id,
            "source_parameter": source_parameter,
            source_parameter: source_id,
            "ordered_training_dates": [],
            "first_training_date": None,
            "last_training_date": None,
            "training_date_count": 0,
        }
        return context

    @staticmethod
    def _build_pattern_result(
        *,
        source_context: dict[str, Any],
        pattern: PathPattern,
        query_family: PatternQueryFamily | None,
        statistics: dict[str, Any] | None,
        limit_recommendation: dict[str, int] | None,
        paths: list[dict[str, object]],
    ) -> dict[str, Any]:
        """Build the standard pattern path result payload."""
        retrieval_context = (
            None
            if statistics is None and limit_recommendation is None and not paths
            else {
                "base_date": statistics.get("base_date") if isinstance(statistics, dict) else None,
                "query_family": query_family.value if query_family is not None else None,
                "path_window": statistics.get("path_window") if isinstance(statistics, dict) else None,
                "window_statistics": (
                    statistics.get("window_statistics")
                    if isinstance(statistics, dict)
                    else None
                ),
                "limit_recommendation": limit_recommendation,
                "paths": paths,
            }
        )
        return {
            **source_context,
            "pattern": pattern.value,
            "retrieval_context": retrieval_context,
        }

    @staticmethod
    def _normalize_pattern_query_family(
        value: PatternQueryFamily | str,
    ) -> PatternQueryFamily:
        """Normalize a query family from public input."""
        if isinstance(value, PatternQueryFamily):
            return value
        if isinstance(value, str) and value.strip():
            return PatternQueryFamily(value.strip())
        raise ValueError("query_family must be a supported pattern query family.")

    @staticmethod
    def _log_source_context(source_context: dict[str, Any]) -> None:
        """Log the basic context for the pattern path flow."""
        LOGGER.info(
            "Initialized path flow context: source_id=%s, source_parameter=%s",
            source_context["source_id"],
            source_context["source_parameter"],
        )

    @staticmethod
    def _normalize_required_string(value: object, field_name: str) -> str:
        """Normalize and validate a required string."""
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{field_name} must be a non-empty string.")
        return value.strip()

    @staticmethod
    def _extract_statistics(records: list[dict[str, Any]]) -> dict[str, int]:
        """Return a normalized statistics mapping from repository results."""
        if not records:
            return {
                "totalPaths": 0,
                "gCount": 0,
                "p2Count": 0,
            }

        return records[0]

    @staticmethod
    def _extract_pattern_group_count(
        pattern: PathPattern,
        statistics: dict[str, Any],
    ) -> int:
        """Return the pattern-specific grouping count used for path limits."""
        group_field = get_path_pattern_spec(pattern).group_field
        group_count_key = f"{group_field}Count"
        return int(statistics.get(group_count_key, 0))

    @staticmethod
    def _summarize_statistics_for_logging(
        statistics: dict[str, Any] | None,
    ) -> dict[str, Any] | None:
        """Return a log-safe statistics summary without dumping game-level details."""
        if statistics is None:
            return None

        return {
            "base_date": statistics.get("base_date"),
            "path_window": statistics.get("path_window"),
            "window_statistics": statistics.get("window_statistics"),
        }

    @staticmethod
    def _build_path_window(base_date: str, window_days: int) -> dict[str, Any]:
        """Build the left-closed, right-open path retrieval window."""
        parsed_base_date = _parse_date_value(base_date, "base_date")
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
            "range_semantics": "[start_date, end_date)",
        }


def _parse_date_value(value: str, field_name: str) -> date:
    """Parse a user-provided date string into an ISO calendar date."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty date string.")
    parts = value.strip().split("-")
    if len(parts) != 3:
        raise ValueError(f"{field_name} must use YYYY-MM-DD format.")
    try:
        year, month, day = (int(part) for part in parts)
        return date(year, month, day)
    except ValueError as exc:
        raise ValueError(f"{field_name} must be a valid calendar date.") from exc


def _normalize_total_score_timepoint(
    record: dict[str, object],
) -> dict[str, object] | None:
    """Normalize one TaskInstanceSet total-score row."""
    instance_set_id = record.get("instance_set_id")
    if not isinstance(instance_set_id, str) or not instance_set_id.strip():
        return None
    total_score = _coerce_optional_float(record.get("total_score"))
    if total_score is None:
        return None

    training_date = record.get("training_date")
    return {
        "instance_set_id": instance_set_id.strip(),
        "training_date": str(training_date) if training_date is not None else None,
        "total_score": total_score,
    }


def _aggregate_total_score_rows(
    rows: list[dict[str, object]],
) -> dict[str, object] | None:
    """Aggregate disease-course total-score rows into one mean score."""
    total_scores = [
        total_score
        for total_score in (
            _coerce_optional_float(row.get("total_score"))
            for row in rows
            if isinstance(row, dict)
        )
        if total_score is not None
    ]
    if not total_scores:
        return None
    effective_dates = [
        str(row.get("effective_total_score_date"))
        for row in rows
        if isinstance(row, dict) and row.get("effective_total_score_date") is not None
    ]
    return {
        "total_score": sum(total_scores) / len(total_scores),
        "total_score_aggregation": "mean",
        "total_score_record_count": len(total_scores),
        "effective_total_score_date": effective_dates[0] if effective_dates else None,
    }


def _total_score_match_sort_key(
    source_score: float,
    source_date: date | None,
    timepoint: dict[str, object],
) -> tuple[float, int, str, str]:
    """Return a stable sort key for nearest total-score matches."""
    total_score = float(timepoint["total_score"])
    training_date = str(timepoint.get("training_date") or "")
    instance_set_id = str(timepoint.get("instance_set_id") or "")
    target_date = _parse_optional_date_value(timepoint.get("training_date"))
    if source_date is not None and target_date is not None:
        date_delta = abs((target_date - source_date).days)
    else:
        date_delta = 10**9
    return (
        abs(total_score - source_score),
        date_delta,
        training_date,
        instance_set_id,
    )


def _build_recommended_date(
    training_date: object,
    disease_course_window_days: int | None,
) -> str | None:
    """Build a recommended downstream base date from a matched training date."""
    if disease_course_window_days is None:
        return None
    parsed_training_date = _parse_optional_date_value(training_date)
    if parsed_training_date is None:
        return None
    return (
        parsed_training_date + timedelta(days=disease_course_window_days // 2)
    ).isoformat()


def _normalize_optional_non_negative_float(
    value: object,
    field_name: str,
) -> float | None:
    """Normalize an optional non-negative float argument."""
    if value is None:
        return None
    normalized = _coerce_optional_float(value)
    if normalized is None or normalized < 0:
        raise ValueError(f"{field_name} must be a non-negative number.")
    return normalized


def _coerce_optional_float(value: object) -> float | None:
    """Coerce a raw numeric value to float when possible."""
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


def _iter_nodes(value: object) -> list[dict[str, object]]:
    """Return node dictionaries from a possibly missing Cypher collection."""
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _extract_expansion_game(row: dict[str, object]) -> dict[str, object]:
    """Extract the Game node from an entity expansion row."""
    nested_row = row.get("row")
    if isinstance(nested_row, dict):
        game = nested_row.get("g")
        if isinstance(game, dict):
            return game
    game = row.get("g")
    if isinstance(game, dict):
        return game
    return {}


def _node_identifier(node: dict[str, object]) -> str:
    """Return a stable node identifier, falling back to name when id is missing."""
    raw_id = node.get("id") or node.get("name")
    return str(raw_id or "").strip()


def _profile_candidate_cache_window_days(
    profile_candidate_training_window_days: int | None,
) -> int:
    """Encode nullable profile window days into the positive SQLite index field."""
    if profile_candidate_training_window_days is None:
        return 1
    if (
        not isinstance(profile_candidate_training_window_days, int)
        or isinstance(profile_candidate_training_window_days, bool)
        or profile_candidate_training_window_days < 0
    ):
        raise ValueError(
            "profile_candidate_training_window_days must be a non-negative integer or None."
        )
    return profile_candidate_training_window_days + 2


def _short_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:8]


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except TypeError:
            pass
    try:
        return _json_safe(dict(value))
    except (TypeError, ValueError):
        return str(value)


def _parse_optional_date_value(value: object) -> date | None:
    """Parse an optional date value and return None for missing or invalid values."""
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        return _parse_date_value(value, "training_date")
    except ValueError:
        return None
