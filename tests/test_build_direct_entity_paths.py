"""Tests for building direct entity-start path files."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.build_direct_entity_paths import build_direct_entity_paths
from similar_user.data_access.direct_path_cache_store import DirectPathCacheStore
from similar_user.domain.graph_schema import PathPattern


class BuildDirectEntityPathsTest(unittest.TestCase):
    def test_build_direct_entity_paths_reads_sqlite_and_updates_index(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            sqlite_path = root / "direct_paths.sqlite"
            output_dir = root / "pattern_paths"
            index_path = output_dir / "direct_entity_path_index.json"
            config_path = root / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "query:",
                        "  graph_path_limit:",
                        "    bands:",
                        "      - per_g: 1",
                        "  pattern_path_storage:",
                        f'    output_dir: "{output_dir}"',
                        "  direct_entity_path:",
                        "    window_days: 10",
                        "    direct_path_limit: 1",
                        f'    index_path: "{index_path}"',
                        "direct_path_cache:",
                        "  enabled: true",
                        f'  sqlite_path: "{sqlite_path}"',
                    ]
                ),
                encoding="utf-8",
            )
            store = DirectPathCacheStore(sqlite_path)
            store.upsert_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                [
                    _disease_path("D1", "S1", "P1", "2026-05-01"),
                    _disease_path("D1", "S2", "P2", "2026-05-10"),
                ],
            )

            summary = build_direct_entity_paths(
                config_path=config_path,
                disease_ids=["D1"],
            )

            self.assertEqual(summary["processed_count"], 1)
            self.assertEqual(summary["saved_count"], 1)
            detail = summary["details"][0]
            self.assertEqual(detail["path_count"], 1)
            self.assertEqual(detail["base_date"], "2026-05-10")
            self.assertTrue(Path(detail["output_path"]).exists())
            payload = json.loads(Path(detail["output_path"]).read_text(encoding="utf-8"))
            self.assertEqual(payload["source_id"], "D1")
            self.assertEqual(payload["source_parameter"], "disease_id")
            self.assertEqual(
                payload["retrieval_context"]["cache_context"]["cache_type"],
                "direct_pattern_paths",
            )
            index_payload = json.loads(index_path.read_text(encoding="utf-8"))
            self.assertEqual(index_payload["direct_path_limit"], 1)
            self.assertEqual(len(index_payload["entries"]), 1)
            self.assertEqual(index_payload["entries"][0]["source_id"], "D1")


def _disease_path(
    disease_id: str,
    taskset_id: str,
    patient_id: str,
    training_date: str,
) -> dict[str, object]:
    return {
        "row": {
            "d": {"id": disease_id, "name": f"disease-{disease_id}"},
            "s": {"id": taskset_id, "训练日期": training_date},
            "p": {"id": patient_id, "name": f"patient-{patient_id}"},
        }
    }


if __name__ == "__main__":
    unittest.main()
