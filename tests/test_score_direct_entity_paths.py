"""Tests for scoring saved direct entity-start paths."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.score_direct_entity_paths import (
    build_scored_direct_entity_summary,
    get_scored_direct_entity_output_paths,
    save_scored_direct_entity_result,
    score_direct_entity_paths,
)


class ScoreDirectEntityPathsTest(unittest.TestCase):
    def test_score_direct_entity_paths_scores_manual_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            output_dir = root / "pattern_paths"
            path_file = output_dir / "D1.json"
            index_path = output_dir / "direct_entity_path_index.json"
            config_path = root / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                        "score_pattern_paths:",
                        "  top_k: 1",
                        "direct_entity_path:",
                        f'  index_path: "{index_path}"',
                    ]
                ),
                encoding="utf-8",
            )
            path_file.parent.mkdir(parents=True, exist_ok=True)
            path_file.write_text(
                json.dumps(
                    {
                        "source_id": "D1",
                        "source_parameter": "disease_id",
                        "disease_id": "D1",
                        "pattern": "DISEASE_TASKSET_PATIENT",
                        "retrieval_context": {
                            "base_date": "2026-05-26",
                            "path_window": {
                                "start_date": "2025-11-27",
                                "end_date": "2026-05-27",
                            },
                            "paths": [
                                _disease_path(
                                    "D1",
                                    "S1",
                                    "P1",
                                    age="66",
                                    education="本科",
                                    gender="男",
                                ),
                                _disease_path(
                                    "D1",
                                    "S2",
                                    "P2",
                                    age="80",
                                    education="小学",
                                    gender="女",
                                ),
                            ],
                        },
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            index_path.write_text(
                json.dumps(
                    {
                        "entries": [
                            {
                                "pattern": "DISEASE_TASKSET_PATIENT",
                                "source_id": "D1",
                                "base_date": "2026-05-25",
                                "window_days": 180,
                                "path_key": "base_2026-05-25_window_180_directcfg_abcdef12",
                                "output_path": str(path_file),
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            result = score_direct_entity_paths(
                config_path=config_path,
                base_date="2026-05-26",
                age=66,
                education="本科",
                gender="男",
                disease_ids=["D1"],
            )

        self.assertTrue(result["should_score"])
        self.assertEqual(result["path_count"], 2)
        self.assertEqual(result["scored_path_count"], 1)
        self.assertEqual(result["scores"][0]["patient_id"], "P1")
        self.assertEqual(result["scores"][0]["score"]["total_score"], 100.0)
        self.assertEqual(
            result["cache_context"]["scored_key"],
            "base_2026-05-26_qf_direct_entity_scoretopk_1",
        )
        self.assertEqual(
            result["cache_context"]["pattern_source_keys"],
            {
                "DISEASE_TASKSET_PATIENT": (
                    "entitybase_2026-05-25_entitywindow_180_pathcfg_abcdef12"
                )
            },
        )

    def test_score_direct_entity_paths_reports_missing_index_entry(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            index_path = root / "direct_entity_path_index.json"
            config_path = root / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "direct_entity_path:",
                        f'  index_path: "{index_path}"',
                    ]
                ),
                encoding="utf-8",
            )
            index_path.write_text('{"entries": []}', encoding="utf-8")

            result = score_direct_entity_paths(
                config_path=config_path,
                age=66,
                education="本科",
                gender="男",
                disease_ids=["D1"],
            )

        self.assertEqual(result["path_count"], 0)
        self.assertEqual(
            result["missing_sources"],
            [{"pattern": "DISEASE_TASKSET_PATIENT", "source_id": "D1"}],
        )

    def test_save_scored_direct_entity_result_writes_detail_and_summary(self) -> None:
        result = {
            "source_id": "20123188",
            "source_parameter": "patient_id",
            "pattern": "DIRECT_ENTITY_PATHS",
            "should_score": True,
            "reason": "kg_profile",
            "base_date": "2026-05-26",
            "path_count": 1,
            "scored_path_count": 1,
            "top_k": 150,
            "cache_context": {
                "scored_key": "base_2026-05-26_qf_direct_entity_scoretopk_150",
                "source_entries": [
                    {
                        "pattern": "DISEASE_TASKSET_PATIENT",
                        "source_id": "D1",
                        "base_date": "2026-05-25",
                        "window_days": 180,
                        "path_key": "base_2026-05-25_window_180_directcfg_abcdef12",
                    }
                ],
            },
            "scores": [
                {
                    "pattern": "DISEASE_TASKSET_PATIENT",
                    "source_id": "D1",
                    "path_index": 3,
                    "patient_id": "P1",
                    "taskset_id": "S1",
                    "training_date": "2026-05-20",
                    "score": {"total_score": 95.0},
                    "path": {"row": {"p": {"id": "P1"}}},
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            output_paths = save_scored_direct_entity_result(result, temp_dir)

            detail = json.loads(output_paths[0]["detail"].read_text(encoding="utf-8"))
            summary = json.loads(output_paths[0]["summary"].read_text(encoding="utf-8"))

        self.assertEqual(detail["scores"][0]["path"]["row"]["p"]["id"], "P1")
        self.assertEqual(summary["scores"][0]["rank"], 1)
        self.assertEqual(summary["scores"][0]["total_score"], 95.0)
        self.assertNotIn("path", summary["scores"][0])
        self.assertEqual(
            output_paths[0]["detail"],
            Path(temp_dir)
            / "base_2026-05-26_qf_direct_entity_scoretopk_150"
            / "DISEASE_TASKSET_PATIENT"
            / "entitybase_2026-05-25_entitywindow_180_pathcfg_abcdef12"
            / "20"
            / "20123188.detail.json",
        )

    def test_get_scored_direct_entity_output_paths_requires_cache_context(self) -> None:
        with self.assertRaisesRegex(ValueError, "cache_context"):
            get_scored_direct_entity_output_paths(
                {"source_id": "20123188", "pattern": "DIRECT_ENTITY_PATHS"},
                "data/scored_pattern_paths",
            )

    def test_build_scored_direct_entity_summary_does_not_include_full_path(self) -> None:
        summary = build_scored_direct_entity_summary(
            {
                "source_id": "manual_abc",
                "source_parameter": "manual_profile",
                "pattern": "DIRECT_ENTITY_PATHS",
                "scores": [
                    {
                        "score": {"total_score": 88.0},
                        "path": {"row": {"p": {"id": "P1"}}},
                    }
                ],
            }
        )

        self.assertEqual(summary["scores"][0]["total_score"], 88.0)
        self.assertNotIn("path", summary["scores"][0])


def _disease_path(
    disease_id: str,
    taskset_id: str,
    patient_id: str,
    *,
    age: str,
    education: str,
    gender: str,
) -> dict[str, object]:
    return {
        "row": {
            "d": {"id": disease_id, "name": f"disease-{disease_id}"},
            "s": {
                "id": taskset_id,
                "训练日期": "2026-05-20",
                "执行年龄": age,
                "执行学历": education,
            },
            "p": {"id": patient_id, "name": f"patient-{patient_id}", "性别": gender},
        }
    }


if __name__ == "__main__":
    unittest.main()
