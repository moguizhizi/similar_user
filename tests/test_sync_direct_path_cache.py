"""Tests for direct path cache sync script."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.sync_direct_path_cache import sync_direct_path_cache
from similar_user.data_access.direct_path_cache_store import DirectPathCacheStore
from similar_user.domain.graph_schema import PathPattern


class SyncDirectPathCacheTest(unittest.TestCase):
    @patch("scripts.sync_direct_path_cache.Neo4jClient")
    @patch("scripts.sync_direct_path_cache.KgRepository")
    def test_sync_initializes_full_cache_when_no_watermark(
        self,
        mock_repository_class: Mock,
        mock_client_class: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "direct_paths.sqlite"
            config_path = _write_config(temp_dir, sqlite_path)
            mock_client = Mock()
            mock_client_class.from_config.return_value.__enter__.return_value = (
                mock_client
            )
            mock_repository = Mock()
            mock_repository.get_direct_taskset_patient_cache_paths.return_value = [
                _disease_path("D1", "S1", "P1", "2026-05-01")
            ]
            mock_repository_class.return_value = mock_repository

            summaries = sync_direct_path_cache(
                config_path=config_path,
                pattern="disease_patient",
            )

            self.assertEqual(summaries[0]["mode"], "full_initial")
            self.assertEqual(summaries[0]["input_path_count"], 1)
            self.assertEqual(
                summaries[0]["last_synced_training_date"],
                "2026-05-01",
            )
            mock_repository.get_direct_taskset_patient_cache_paths.assert_called_once_with(
                PathPattern.DISEASE_TASKSET_PATIENT
            )

    @patch("scripts.sync_direct_path_cache.Neo4jClient")
    @patch("scripts.sync_direct_path_cache.KgRepository")
    def test_sync_uses_training_date_watermark_for_incremental(
        self,
        mock_repository_class: Mock,
        mock_client_class: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "direct_paths.sqlite"
            config_path = _write_config(temp_dir, sqlite_path)
            store = DirectPathCacheStore(sqlite_path)
            store.upsert_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                [_disease_path("D1", "S1", "P1", "2026-05-10")],
            )
            mock_client = Mock()
            mock_client_class.from_config.return_value.__enter__.return_value = (
                mock_client
            )
            mock_repository = Mock()
            mock_repository.get_direct_taskset_patient_cache_paths.return_value = [
                _disease_path("D1", "S2", "P2", "2026-05-11")
            ]
            mock_repository_class.return_value = mock_repository

            summaries = sync_direct_path_cache(
                config_path=config_path,
                pattern="disease_patient",
            )

            self.assertEqual(summaries[0]["mode"], "incremental")
            self.assertEqual(summaries[0]["start_date"], "2026-05-09")
            self.assertEqual(summaries[0]["stored_path_count"], 2)
            mock_repository.get_direct_taskset_patient_cache_paths.assert_called_once_with(
                PathPattern.DISEASE_TASKSET_PATIENT,
                start_date="2026-05-09",
            )

    @patch("scripts.sync_direct_path_cache.Neo4jClient")
    @patch("scripts.sync_direct_path_cache.KgRepository")
    def test_sync_force_full_refresh_replaces_pattern_rows(
        self,
        mock_repository_class: Mock,
        mock_client_class: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "direct_paths.sqlite"
            config_path = _write_config(temp_dir, sqlite_path)
            store = DirectPathCacheStore(sqlite_path)
            store.upsert_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                [_disease_path("D1", "S1", "P1", "2026-05-10")],
            )
            mock_client = Mock()
            mock_client_class.from_config.return_value.__enter__.return_value = (
                mock_client
            )
            mock_repository = Mock()
            mock_repository.get_direct_taskset_patient_cache_paths.return_value = [
                _disease_path("D2", "S2", "P2", "2026-05-11")
            ]
            mock_repository_class.return_value = mock_repository

            summaries = sync_direct_path_cache(
                config_path=config_path,
                pattern="disease_patient",
                force_full_refresh=True,
            )

            self.assertEqual(summaries[0]["mode"], "full_refresh")
            self.assertEqual(summaries[0]["stored_path_count"], 1)
            self.assertEqual(
                store.get_paths(PathPattern.DISEASE_TASKSET_PATIENT, "D1"),
                [],
            )
            self.assertEqual(
                len(store.get_paths(PathPattern.DISEASE_TASKSET_PATIENT, "D2")),
                1,
            )


def _write_config(temp_dir: str, sqlite_path: Path) -> Path:
    config_path = Path(temp_dir) / "settings.yaml"
    config_path.write_text(
        "\n".join(
            [
                "direct_path_cache:",
                "  enabled: true",
                f'  sqlite_path: "{sqlite_path}"',
                "  incremental_enabled: true",
                "  overlap_days: 1",
            ]
        ),
        encoding="utf-8",
    )
    return config_path


def _disease_path(
    disease_id: str,
    taskset_id: str,
    patient_id: str,
    training_date: str,
) -> dict[str, object]:
    return {
        "row": {
            "d": {"id": disease_id},
            "s": {"id": taskset_id, "训练日期": training_date},
            "p": {"id": patient_id},
        }
    }


if __name__ == "__main__":
    unittest.main()
