"""Tests for background user-cache refresh jobs."""

from __future__ import annotations

import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.refresh_user_cache_jobs import refresh_user_cache_jobs
from similar_user.data_access.user_cache_index import (
    UserCacheEntry,
    UserCacheIndexStore,
)


class RefreshUserCacheJobsTest(unittest.TestCase):
    def test_refresh_user_cache_jobs_rebuilds_patient_topk_job(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_config(root)
            store = UserCacheIndexStore(root / "user_cache" / "cache_index.sqlite")
            store.enqueue_refresh_job(
                cache_type="topk_candidates",
                source_type="patient",
                source_id="30010096",
                query_family="training_order_source_window",
                window_days=14,
                config_hash="cfg",
                request_base_date="2024-02-09",
                reason="stale_topk_hit",
            )

            with (
                patch(
                    "scripts.refresh_user_cache_jobs.build_similar_user_candidates",
                    return_value={"source_id": "30010096"},
                ) as mock_build,
                patch(
                    "scripts.refresh_user_cache_jobs.save_similar_user_candidates_result"
                ) as mock_save,
            ):
                summary = refresh_user_cache_jobs(
                    config_path=config_path,
                    scored_paths_dir=root / "scored",
                    candidates_dir=root / "candidates",
                    limit=10,
                    cleanup=False,
                )
                job_status = _job_status(root / "user_cache" / "cache_index.sqlite")

        self.assertEqual(summary["claimed_jobs"], 1)
        self.assertEqual(summary["completed_jobs"], 1)
        self.assertEqual(job_status, "completed")
        mock_build.assert_called_once_with(
            "30010096",
            config_path=config_path,
            scored_paths_dir=root / "scored",
            candidates_dir=root / "candidates",
            base_date="2024-02-09",
            query_family="training_order_source_window",
            skip_topk_user_cache_read=True,
        )
        mock_save.assert_called_once_with(
            {"source_id": "30010096"},
            output_dir=root / "candidates",
        )

    def test_refresh_user_cache_jobs_recovers_direct_entity_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            config_path = _write_config(root)
            sqlite_path = root / "user_cache" / "cache_index.sqlite"
            store = UserCacheIndexStore(sqlite_path)
            scored_key = "base_2024-01-31_qf_direct_entity_scoretopk_150"
            scoring_input = {
                "patient_id": "201231885555",
                "age": 66,
                "education": "本科",
                "gender": "男",
                "disease_ids": ["D1"],
                "symptom_ids": ["S1"],
                "unknown_ids": ["U1"],
            }
            topk_detail_path = root / "topk.detail.json"
            topk_detail_path.write_text(
                json.dumps(
                    {
                        "source_id": "201231885555",
                        "cache_context": {
                            "candidate_key": "old-candidate-key",
                            "direct_entity_scored_context": {
                                "scored_key": scored_key,
                            },
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            scored_detail_path = root / "scored.detail.json"
            scored_detail_path.write_text(
                json.dumps(
                    {
                        "source_id": "201231885555",
                        "source_parameter": "manual_profile",
                        "pattern": "DISEASE_TASKSET_PATIENT",
                        "base_date": "2024-01-31",
                        "direct_path_source_key": "entitybase_2024-01-31_entitywindow_180_pathcfg_cfg",
                        "scoring_input": scoring_input,
                        "cache_context": {
                            "scored_key": scored_key,
                        },
                        "path_count": 0,
                        "scored_path_count": 0,
                        "scores": [],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            store.upsert_entry(
                UserCacheEntry(
                    cache_type="topk_candidates",
                    patient_id="201231885555",
                    source_type="direct_entity_profile",
                    source_id="201231885555",
                    query_family="direct_entity",
                    window_days=14,
                    config_hash="topkcfg",
                    cached_base_date="2024-01-31",
                    valid_days=7,
                    data_path=str(topk_detail_path),
                    payload={"candidate_key": "old-candidate-key"},
                )
            )
            store.upsert_entry(
                UserCacheEntry(
                    cache_type="scored_direct_entity_paths",
                    patient_id="201231885555",
                    source_type="direct_entity_profile",
                    source_id="201231885555",
                    query_family="direct_entity",
                    window_days=180,
                    config_hash="scoredcfg",
                    cached_base_date="2024-01-31",
                    valid_days=60,
                    data_path=str(scored_detail_path),
                    payload={
                        "scored_key": scored_key,
                        "pattern": "DISEASE_TASKSET_PATIENT",
                    },
                )
            )
            store.enqueue_refresh_job(
                cache_type="topk_candidates",
                source_type="direct_entity_profile",
                source_id="201231885555",
                query_family="direct_entity",
                window_days=14,
                config_hash="topkcfg",
                request_base_date="2024-02-09",
                reason="stale_topk_hit",
            )
            refreshed_score_result = {
                "source_id": "201231885555",
                "source_parameter": "manual_profile",
                "base_date": "2024-02-09",
                "scoring_input": scoring_input,
                "cache_context": {
                    "scored_key": "base_2024-02-09_qf_direct_entity_scoretopk_150",
                    "pattern_source_keys": {},
                    "source_entries": [],
                },
                "path_count": 0,
                "scored_path_count": 0,
                "scores": [],
            }

            with (
                patch(
                    "scripts.refresh_user_cache_jobs._score_direct_entity_paths_with_auto_refresh",
                    return_value=refreshed_score_result,
                ) as mock_score,
                patch(
                    "scripts.refresh_user_cache_jobs.save_scored_direct_entity_result",
                    return_value=[],
                ),
                patch(
                    "scripts.refresh_user_cache_jobs.save_similar_user_candidates_result"
                ) as mock_save_candidates,
            ):
                summary = refresh_user_cache_jobs(
                    config_path=config_path,
                    scored_paths_dir=root / "scored",
                    candidates_dir=root / "candidates",
                    limit=10,
                    cleanup=False,
                )
                job_status = _job_status(sqlite_path)

        self.assertEqual(summary["claimed_jobs"], 1)
        self.assertEqual(summary["completed_jobs"], 1)
        self.assertEqual(job_status, "completed")
        mock_score.assert_called_once_with(
            config_path=config_path,
            patient_id="201231885555",
            base_date="2024-02-09",
            age=66,
            education="本科",
            gender="男",
            disease_ids=["D1"],
            symptom_ids=["S1"],
            unknown_ids=["U1"],
            top_k=150,
        )
        self.assertEqual(mock_save_candidates.call_count, 1)

def _write_config(root: Path) -> Path:
    config_path = root / "settings.yaml"
    config_path.write_text(
        "\n".join(
            [
                "graph_path_limit:",
                "  bands:",
                "    - per_g: 1",
                "patient_path:",
                "  window_days: 14",
                "score_pattern_paths:",
                "  top_k: 150",
                "candidate_ranking:",
                "  candidate_top_k: 2",
                "  disease_course_window_days: 14",
                "direct_entity_path:",
                "  window_days: 180",
                "  direct_path_limit: 1000",
                "user_cache:",
                "  enabled: true",
                f'  sqlite_path: "{root / "user_cache" / "cache_index.sqlite"}"',
                "  topk_candidates_valid_days: 7",
                "  topk_candidates_stale_valid_days: 14",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _job_status(sqlite_path: Path) -> str:
    with sqlite3.connect(sqlite_path) as connection:
        row = connection.execute(
            "SELECT status FROM user_cache_refresh_jobs ORDER BY id DESC LIMIT 1"
        ).fetchone()
    assert row is not None
    return str(row[0])


if __name__ == "__main__":
    unittest.main()
