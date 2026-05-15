"""Tests for rule-based path scoring."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts.score_pattern_paths import (
    build_scored_pattern_summary,
    main,
    parse_args,
    save_scored_pattern_result,
    score_pattern_paths,
)
from src.similar_user.data_access.pattern_registry import available_path_pattern_aliases
from src.similar_user.domain import (
    GameNode,
    PathPattern,
    PatientNode,
    PatientTasksetTaskGameTaskTasksetPatientPath,
    TaskInstanceNode,
    TaskInstanceSetNode,
)
from src.similar_user.services.path_scoring import PatientGamePatientPathScorer, get_path_scorer
from src.similar_user.utils.pattern_storage import save_pattern_result


class PathScoringTest(unittest.TestCase):
    def test_patient_game_patient_path_scorer_supports_observed_education_values(self) -> None:
        scorer = PatientGamePatientPathScorer()

        self.assertEqual(scorer._map_education_rank("专科"), scorer._map_education_rank("大专"))
        self.assertEqual(scorer._map_education_rank("研究生"), scorer._map_education_rank("硕士"))
        self.assertEqual(scorer._map_education_rank("小学6年级"), scorer._map_education_rank("小学"))
        self.assertEqual(scorer._map_education_rank("初中3年级"), scorer._map_education_rank("初中"))
        self.assertIsNone(scorer._map_education_rank("保密"))

    def test_get_path_scorer_returns_registered_patient_game_scorer(self) -> None:
        scorer = get_path_scorer("patient_game_patient")

        self.assertIsInstance(scorer, PatientGamePatientPathScorer)

    def test_get_path_scorer_rejects_unsupported_pattern(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported scoring pattern"):
            get_path_scorer("patient_disease_patient")

    @patch("sys.argv", ["score_pattern_paths.py", "30010096"])
    def test_parse_args_defaults_to_patient_game_alias(self) -> None:
        args = parse_args()

        self.assertEqual(args.pattern, "patient_game_patient")

    def test_parse_args_accepts_all_public_pattern_aliases(self) -> None:
        for pattern in available_path_pattern_aliases():
            with self.subTest(pattern=pattern):
                with patch(
                    "sys.argv",
                    ["score_pattern_paths.py", "30010096", "--pattern", pattern],
                ):
                    args = parse_args()

                self.assertEqual(args.pattern, pattern)

    def test_parse_int_supports_decimal_strings(self) -> None:
        scorer = PatientGamePatientPathScorer()

        self.assertEqual(scorer._parse_int("14.0"), 14)
        self.assertEqual(scorer._parse_int(" 14.8 "), 14)
        self.assertEqual(scorer._parse_int("14"), 14)
        self.assertIsNone(scorer._parse_int("abc"))

    def test_patient_game_patient_path_scorer_returns_detailed_breakdown(self) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(
                id="30010096_20220522_348_x",
                任务类型="专属",
                结果="完成",
                活跃="是",
            ),
            g=GameNode(id="348", name="真假句辨别", 任务类型="句子识别"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                得分="82",
                常模分="102",
                结果="完成",
                活跃="是",
                任务类型="专属",
                状态="完成",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.total_score, 90.0)
        self.assertEqual(result.education_score, 100.0)
        self.assertEqual(result.age_score, 100.0)
        self.assertEqual(result.activity_score, 100.0)
        self.assertEqual(result.task_type_score, 30.0)
        self.assertIsNone(result.task_relevance_score)
        self.assertIn("学历一致", result.details["education"])
        self.assertIn("任务类型均为专属: 专属/专属", result.details["task_type"])
        self.assertIn("当前path上不足两个g", result.details["task_relevance"])

    def test_patient_game_patient_path_scorer_scores_neighboring_observed_education_levels(self) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="高中以后"),
            i1=TaskInstanceNode(id="30010096_20220522_348_x", 任务类型="专属", 结果="完成"),
            g=GameNode(id="348", name="真假句辨别", 任务类型="句子识别"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                得分="82",
                常模分="102",
                结果="完成",
                活跃="是",
                任务类型="专属",
                状态="完成",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="专科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.education_score, 85.0)
        self.assertIn("学历相差1级", result.details["education"])

    def test_patient_game_patient_path_scorer_completion_only_depends_on_result(self) -> None:
        scorer = PatientGamePatientPathScorer()
        base_path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(id="30010096_20220522_348_x", 任务类型="专属", 结果="完成"),
            g=GameNode(id="348", name="真假句辨别", 任务类型="句子识别"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                得分="10",
                常模分="55",
                结果="完成",
                活跃="是",
                任务类型="专属",
                状态="失败",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(base_path)

        self.assertEqual(result.completion_score, 100.0)
        self.assertEqual(result.details["completion"], "i1结果=完成, i2结果=完成")

    def test_patient_game_patient_path_scorer_completion_compares_i1_and_i2_results(self) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(id="30010096_20220522_348_x", 任务类型="专属", 结果="完成"),
            g=GameNode(id="348", name="真假句辨别", 任务类型="句子识别"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                结果="未完成",
                活跃="是",
                任务类型="专属",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.completion_score, 20.0)
        self.assertEqual(result.details["completion"], "i1结果=完成, i2结果=未完成")

    def test_patient_game_patient_path_scorer_completion_only_scores_both_completed_as_full(
        self,
    ) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(id="30010096_20220522_348_x", 任务类型="专属", 结果="未完成"),
            g=GameNode(id="348", name="真假句辨别", 任务类型="句子识别"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                结果="未完成",
                活跃="是",
                任务类型="专属",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.completion_score, 20.0)
        self.assertEqual(result.details["completion"], "i1结果=未完成, i2结果=未完成")

    def test_patient_game_patient_path_scorer_activity_requires_both_active_for_full_score(
        self,
    ) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(
                id="30010096_20220522_348_x",
                任务类型="专属",
                结果="完成",
                活跃="是",
            ),
            g=GameNode(id="348", name="真假句辨别", 任务类型="句子识别"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                结果="完成",
                活跃="否",
                任务类型="专属",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.activity_score, 20.0)
        self.assertEqual(result.details["activity"], "i1活跃=是, i2活跃=否")

    def test_patient_game_patient_path_scorer_activity_skips_missing_values(self) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(id="30010096_20220522_348_x", 任务类型="专属", 结果="完成"),
            g=GameNode(id="348", name="真假句辨别", 任务类型="句子识别"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                结果="完成",
                活跃="是",
                任务类型="专属",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertIsNone(result.activity_score)
        self.assertEqual(
            result.details["activity"],
            "i1活跃=None, i2活跃=是，活跃度缺失，跳过该项",
        )

    def test_patient_game_patient_path_scorer_activity_skips_unsupported_values(self) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(
                id="30010096_20220522_348_x",
                任务类型="专属",
                结果="完成",
                活跃="未知",
            ),
            g=GameNode(id="348", name="真假句辨别", 任务类型="句子识别"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                结果="完成",
                活跃="是",
                任务类型="专属",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertIsNone(result.activity_score)
        self.assertEqual(
            result.details["activity"],
            "i1活跃=未知, i2活跃=是，不在支持范围内，跳过该项",
        )

    def test_patient_game_patient_path_scorer_task_type_scores_task_instance_exclusive_type(self) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(id="30010096_20220522_348_x", 任务类型="专属", 结果="完成"),
            g=GameNode(id="348", name="真假句辨别", 任务类型="语义判断"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                结果="完成",
                活跃="是",
                任务类型="自由",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.task_type_score, 30.0)
        self.assertIn("任务类型不一致: 专属/自由", result.details["task_type"])

    def test_patient_game_patient_path_scorer_task_type_scores_both_free_as_full(
        self,
    ) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(id="30010096_20220522_348_x", 任务类型="自由", 结果="完成"),
            g=GameNode(id="348", name="真假句辨别", 任务类型="语义判断"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                结果="完成",
                活跃="是",
                任务类型="自由",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.task_type_score, 100.0)
        self.assertEqual(result.details["task_type"], "任务类型均为自由: 自由/自由")

    def test_patient_game_patient_path_scorer_task_type_returns_none_when_task_type_missing(self) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(id="30010096_20220522_348_x", 结果="完成"),
            g=GameNode(id="348", name="真假句辨别", 任务类型="句子识别"),
            i2=TaskInstanceNode(id="20113562_20211214_348_y", 结果="完成", 活跃="是"),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertIsNone(result.task_type_score)
        self.assertEqual(result.details["task_type"], "任务类型缺失，跳过该项")

    def test_patient_game_patient_path_scorer_task_relevance_returns_none_when_only_one_game_exists(self) -> None:
        scorer = PatientGamePatientPathScorer()
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            i1=TaskInstanceNode(id="30010096_20220522_348_x", 任务类型="专属", 结果="完成"),
            g=GameNode(id="348", name="真假句辨别", 任务类型="句子识别"),
            i2=TaskInstanceNode(
                id="20113562_20211214_348_y",
                结果="完成",
                活跃="是",
                任务类型="专属",
            ),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="本科"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertIsNone(result.task_relevance_score)
        self.assertEqual(
            result.details["task_relevance"],
            "当前path上不足两个g，无法计算两个g之间的相关度，跳过该项",
        )

    def test_score_pattern_paths_scores_saved_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            output_dir = Path(temp_dir) / "pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "training_date_split:",
                        "  min_training_dates: 5",
                        "  before_ratio: 4",
                        "  after_ratio: 1",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "statistics": None,
                "limit_recommendation": None,
                "paths": [
                    {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
                            "i1": {
                                "id": "30010096_20220522_348_x",
                                "任务类型": "专属",
                                "结果": "完成",
                                "活跃": "是",
                            },
                            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
                            "i2": {
                                "id": "20113562_20211214_348_y",
                                "常模分": "102",
                                "结果": "完成",
                                "活跃": "是",
                                "任务类型": "专属",
                                "状态": "完成",
                            },
                            "s2": {"id": "20113562_20211214", "执行年龄": "64", "执行学历": "本科"},
                            "p2": {"id": "20113562"},
                        }
                    }
                ],
            }
            save_pattern_result(result, config_path)

            scored = score_pattern_paths(
                "30010096",
                pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                config_path=config_path,
            )

        self.assertEqual(scored["path_count"], 1)
        self.assertEqual(scored["scored_path_count"], 1)
        self.assertEqual(scored["retrieval_context"]["score_end_date"], None)
        self.assertEqual(scored["scores"][0]["score"]["total_score"], 90.0)

    def test_score_pattern_paths_returns_top_k_paths(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            output_dir = Path(temp_dir) / "pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "training_date_split:",
                        "  min_training_dates: 5",
                        "  before_ratio: 4",
                        "  after_ratio: 1",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "statistics": None,
                "limit_recommendation": None,
                "paths": [
                    {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
                            "i1": {"id": "30010096_20220522_348_a", "任务类型": "专属", "结果": "完成"},
                            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
                            "i2": {
                                "id": "20113562_20211214_348_a",
                                "结果": "完成",
                                "活跃": "是",
                                "任务类型": "专属",
                            },
                            "s2": {"id": "20113562_20211214", "执行年龄": "64", "执行学历": "本科"},
                            "p2": {"id": "20113562"},
                        }
                    },
                    {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
                            "i1": {"id": "30010096_20220522_348_b", "任务类型": "专属", "结果": "完成"},
                            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
                            "i2": {
                                "id": "20113563_20211214_348_b",
                                "结果": "未完成",
                                "活跃": "否",
                                "任务类型": "自由",
                            },
                            "s2": {"id": "20113563_20211214", "执行年龄": "88", "执行学历": "小学"},
                            "p2": {"id": "20113563"},
                        }
                    },
                ],
            }
            save_pattern_result(result, config_path)

            scored = score_pattern_paths(
                "30010096",
                pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                config_path=config_path,
                top_k=1,
            )

        self.assertEqual(scored["path_count"], 2)
        self.assertEqual(scored["scored_path_count"], 1)
        self.assertEqual(scored["retrieval_context"]["score_end_date"], None)
        self.assertEqual(scored["scores"][0]["path_index"], 0)

    def test_save_scored_pattern_result_writes_detail_and_summary_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            result = {
                "source_id": "30010096",
                "source_parameter": "patient_id",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "path_count": 1,
                "scored_path_count": 1,
                "retrieval_context": {"score_end_date": "2022-05-22"},
                "scores": [
                    {
                        "path_index": 3,
                        "score": {
                            "total_score": 95.0,
                            "education_score": 100.0,
                            "details": {"education": "学历一致"},
                        },
                        "path": {
                            "row": {
                                "g": {"id": "348", "name": "真假句辨别"},
                                "p2": {"id": "20113562"},
                            }
                        },
                    }
                ],
            }

            output_paths = save_scored_pattern_result(result, Path(temp_dir))

            detail = json.loads(output_paths["detail"].read_text(encoding="utf-8"))
            summary = json.loads(output_paths["summary"].read_text(encoding="utf-8"))

        self.assertEqual(detail, result)
        self.assertEqual(
            output_paths["detail"].name,
            "30010096.detail.json",
        )
        self.assertEqual(
            output_paths["summary"].name,
            "30010096.summary.json",
        )
        self.assertEqual(summary["scores"][0]["rank"], 1)
        self.assertEqual(summary["scores"][0]["path_index"], 3)
        self.assertEqual(summary["scores"][0]["total_score"], 95.0)
        self.assertEqual(summary["scores"][0]["candidate_id"], "20113562")
        self.assertEqual(summary["scores"][0]["game_id"], "348")
        self.assertEqual(summary["scores"][0]["game_name"], "真假句辨别")
        self.assertNotIn("path", summary["scores"][0])

    def test_build_scored_pattern_summary_does_not_include_full_path_rows(self) -> None:
        summary = build_scored_pattern_summary(
            {
                "source_id": "30010096",
                "source_parameter": "patient_id",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "path_count": 1,
                "scored_path_count": 1,
                "retrieval_context": {},
                "scores": [
                    {
                        "path_index": 0,
                        "score": {"total_score": 88.0},
                        "path": {"row": {"p2": {"id": "20113562"}}},
                    }
                ],
            }
        )

        self.assertEqual(summary["scores"][0]["candidate_id"], "20113562")
        self.assertNotIn("path", summary["scores"][0])

    def test_score_pattern_paths_rejects_unsupported_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            output_dir = Path(temp_dir) / "pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "training_date_split:",
                        "  min_training_dates: 5",
                        "  before_ratio: 4",
                        "  after_ratio: 1",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "statistics": None,
                "limit_recommendation": None,
                "paths": [],
            }
            save_pattern_result(result, config_path)

            with self.assertRaisesRegex(ValueError, "Unsupported scoring pattern"):
                score_pattern_paths(
                    "30010096",
                    pattern="PATIENT_TASKSET_DISEASE_TASKSET_PATIENT",
                    config_path=config_path,
                )

    def test_score_pattern_paths_uses_source_id_for_non_patient_pattern(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            output_dir = Path(temp_dir) / "pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "training_date_split:",
                        "  min_training_dates: 5",
                        "  before_ratio: 4",
                        "  after_ratio: 1",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            result = {
                "disease_id": "AU_DIS_0013",
                "pattern": "DISEASE_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "statistics": None,
                "limit_recommendation": None,
                "paths": [],
            }
            save_pattern_result(result, config_path)

            with self.assertRaisesRegex(ValueError, "Unsupported scoring pattern"):
                score_pattern_paths(
                    "AU_DIS_0013",
                    pattern="disease_patient",
                    config_path=config_path,
                )

    @patch("scripts.score_pattern_paths.LOGGER")
    @patch("scripts.score_pattern_paths.parse_args")
    def test_main_prints_scored_result(
        self,
        mock_parse_args: Mock,
        mock_logger: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            output_dir = Path(temp_dir) / "pattern_paths"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "training_date_split:",
                        "  min_training_dates: 5",
                        "  before_ratio: 4",
                        "  after_ratio: 1",
                        "pattern_path_storage:",
                        f'  output_dir: "{output_dir}"',
                    ]
                ),
                encoding="utf-8",
            )
            result = {
                "patient_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "ordered_training_dates": [],
                "first_training_date": None,
                "last_training_date": None,
                "training_date_count": 0,
                "statistics": None,
                "limit_recommendation": None,
                "paths": [
                    {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {"id": "30010096_20220522", "执行年龄": "66", "执行学历": "本科"},
                            "i1": {"id": "30010096_20220522_348_x", "任务类型": "专属", "结果": "完成"},
                            "g": {"id": "348", "name": "真假句辨别", "任务类型": "句子识别"},
                            "i2": {
                                "id": "20113562_20211214_348_y",
                                "常模分": "102",
                                "结果": "完成",
                                "活跃": "是",
                                "任务类型": "专属",
                                "状态": "完成",
                            },
                            "s2": {"id": "20113562_20211214", "执行年龄": "64", "执行学历": "本科"},
                            "p2": {"id": "20113562"},
                        }
                    }
                ],
            }
            save_pattern_result(result, config_path)
            expected = score_pattern_paths(
                "30010096",
                pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                config_path=config_path,
            )
            mock_parse_args.return_value = Mock(
                source_id="30010096",
                pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                config=str(config_path),
                path_index=None,
                top_k=None,
                save=False,
                scored_output_dir="data/scored_pattern_paths",
            )

            exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_logger.info.assert_called_once_with(
            json.dumps(expected, ensure_ascii=False, indent=2, default=str)
        )

    @patch("scripts.score_pattern_paths.LOGGER")
    @patch("scripts.score_pattern_paths.parse_args")
    def test_main_logs_error_when_scoring_fails(
        self,
        mock_parse_args: Mock,
        mock_logger: Mock,
    ) -> None:
        mock_parse_args.return_value = Mock(
            source_id="missing",
            pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
            config="missing.yaml",
            path_index=None,
            top_k=None,
            save=False,
            scored_output_dir="data/scored_pattern_paths",
        )

        exit_code = main()

        self.assertEqual(exit_code, 1)
        mock_logger.exception.assert_called_once()


if __name__ == "__main__":
    unittest.main()
