"""Tests for direct path provider backend selection."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

from similar_user.data_access.direct_path_cache_store import DirectPathCacheStore
from similar_user.domain.graph_schema import PathPattern
from similar_user.services.direct_path_provider import DirectPathProvider


class DirectPathProviderTest(unittest.TestCase):
    def test_get_randomized_paths_reads_sqlite_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "direct_paths.sqlite"
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "direct_path_cache:",
                        "  enabled: true",
                        f'  sqlite_path: "{sqlite_path}"',
                    ]
                ),
                encoding="utf-8",
            )
            DirectPathCacheStore(sqlite_path).upsert_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                [
                    {
                        "row": {
                            "d": {"id": "D1"},
                            "s": {"id": "S1", "训练日期": "2026-05-01"},
                            "p": {"id": "P1"},
                        }
                    }
                ],
            )
            repository = Mock()

            paths = DirectPathProvider(
                kg_repository=repository,
                config_path=config_path,
            ).get_randomized_paths(
                pattern=PathPattern.DISEASE_TASKSET_PATIENT,
                source_id="D1",
                start_date="2026-05-01",
                end_date="2026-06-01",
            )

            self.assertEqual(paths[0]["row"]["p"]["id"], "P1")
            repository.get_disease_taskset_patient_randomized_paths.assert_not_called()

    def test_get_randomized_paths_reads_neo4j_when_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "direct_path_cache:",
                        "  enabled: false",
                    ]
                ),
                encoding="utf-8",
            )
            repository = Mock()
            repository.get_disease_taskset_patient_randomized_paths.return_value = [
                {"row": {"d": {"id": "D1"}, "s": {"id": "S1"}, "p": {"id": "P1"}}}
            ]

            paths = DirectPathProvider(
                kg_repository=repository,
                config_path=config_path,
            ).get_randomized_paths(
                pattern=PathPattern.DISEASE_TASKSET_PATIENT,
                source_id="D1",
                start_date="2026-05-01",
                end_date="2026-06-01",
            )

            self.assertEqual(paths[0]["row"]["p"]["id"], "P1")
            repository.get_disease_taskset_patient_randomized_paths.assert_called_once_with(
                "D1",
                start_date="2026-05-01",
                end_date="2026-06-01",
            )


if __name__ == "__main__":
    unittest.main()
