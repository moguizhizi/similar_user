"""Tests for SQLite direct path cache storage."""

from __future__ import annotations

import tempfile
import unittest
import sqlite3
from pathlib import Path

from similar_user.data_access.direct_path_cache_store import DirectPathCacheStore
from similar_user.domain.graph_schema import PathPattern


class DirectPathCacheStoreTest(unittest.TestCase):
    def test_upsert_paths_deduplicates_by_path_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = DirectPathCacheStore(Path(temp_dir) / "direct_paths.sqlite")

            summary = store.upsert_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                [
                    _disease_path(
                        disease_id="D1",
                        taskset_id="S1",
                        patient_id="P1",
                        training_date="2026-05-01",
                    ),
                    _disease_path(
                        disease_id="D1",
                        taskset_id="S1",
                        patient_id="P1",
                        training_date="2026-05-02",
                    ),
                ],
            )

            self.assertEqual(summary.input_path_count, 2)
            self.assertEqual(summary.stored_path_count, 1)
            self.assertEqual(summary.last_synced_training_date, "2026-05-02")
            result = store.get_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                "D1",
            )
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["row"]["s"]["训练日期"], "2026-05-02")

    def test_upsert_paths_splits_path_and_node_tables(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "direct_paths.sqlite"
            store = DirectPathCacheStore(sqlite_path)

            store.upsert_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                [_disease_path("D1", "S1", "P1", "2026-05-01")],
            )

            connection = sqlite3.connect(sqlite_path)
            direct_path_columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(direct_paths)")
            }
            self.assertNotIn("source_json", direct_path_columns)
            self.assertEqual(
                connection.execute("SELECT count(*) FROM direct_paths").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute("SELECT count(*) FROM source_nodes").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute("SELECT count(*) FROM taskset_nodes").fetchone()[0],
                1,
            )
            self.assertEqual(
                connection.execute("SELECT count(*) FROM patient_nodes").fetchone()[0],
                1,
            )

    def test_get_paths_filters_by_source_and_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = DirectPathCacheStore(Path(temp_dir) / "direct_paths.sqlite")
            store.upsert_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                [
                    _disease_path("D1", "S1", "P1", "2026-05-01"),
                    _disease_path("D1", "S2", "P2", "2026-05-10"),
                    _disease_path("D2", "S3", "P3", "2026-05-10"),
                ],
            )

            result = store.get_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                "D1",
                start_date="2026-05-05",
                end_date="2026-05-20",
            )

            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["row"]["d"]["id"], "D1")
            self.assertEqual(result[0]["row"]["s"]["id"], "S2")
            self.assertEqual(result[0]["row"]["p"]["id"], "P2")

    def test_get_paths_keeps_one_path_per_patient_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = DirectPathCacheStore(Path(temp_dir) / "direct_paths.sqlite")
            store.upsert_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                [
                    _disease_path("D1", "S1", "P1", "2026-05-01"),
                    _disease_path("D1", "S2", "P1", "2026-05-02"),
                    _disease_path("D1", "S3", "P2", "2026-05-03"),
                ],
            )

            result = store.get_paths(PathPattern.DISEASE_TASKSET_PATIENT, "D1")

            self.assertEqual(len(result), 2)
            self.assertEqual(
                sorted(record["row"]["p"]["id"] for record in result),
                ["P1", "P2"],
            )

    def test_replace_pattern_paths_deletes_orphan_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "direct_paths.sqlite"
            store = DirectPathCacheStore(sqlite_path)
            store.upsert_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                [_disease_path("D1", "S1", "P1", "2026-05-01")],
            )

            store.replace_pattern_paths(
                PathPattern.DISEASE_TASKSET_PATIENT,
                [_disease_path("D2", "S2", "P2", "2026-05-02")],
            )

            connection = sqlite3.connect(sqlite_path)
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM source_nodes WHERE source_id = 'D1'"
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM taskset_nodes WHERE taskset_id = 'S1'"
                ).fetchone()[0],
                0,
            )
            self.assertEqual(
                connection.execute(
                    "SELECT count(*) FROM patient_nodes WHERE patient_id = 'P1'"
                ).fetchone()[0],
                0,
            )

    def test_initialize_rejects_legacy_inline_json_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            sqlite_path = Path(temp_dir) / "direct_paths.sqlite"
            connection = sqlite3.connect(sqlite_path)
            connection.execute(
                """
                CREATE TABLE direct_paths (
                    pattern TEXT NOT NULL,
                    source_json TEXT NOT NULL
                )
                """.strip()
            )
            connection.commit()
            connection.close()

            store = DirectPathCacheStore(sqlite_path)

            with self.assertRaisesRegex(ValueError, "legacy inline-JSON schema"):
                store.initialize()


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
