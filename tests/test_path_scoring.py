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
    save_scored_pattern_results,
    score_and_save_configured_pattern_paths,
    score_configured_pattern_paths,
    score_pattern_paths,
)
from src.similar_user.data_access.pattern_registry import available_path_pattern_aliases
from src.similar_user.domain import (
    DiseaseNode,
    GameNode,
    PathPattern,
    PatientNode,
    PatientTasksetDiseaseTasksetPatientPath,
    PatientTasksetSymptomTasksetPatientPath,
    PatientTasksetTaskGameTaskTasksetPatientPath,
    PatientTasksetUnknownTasksetPatientPath,
    SymptomNode,
    TaskInstanceNode,
    TaskInstanceSetNode,
    UnknownNode,
)
from src.similar_user.services.path_scoring import (
    PatientDiseasePatientPathScorer,
    PatientGamePatientPathScorer,
    PatientSymptomPatientPathScorer,
    PatientUnknownPatientPathScorer,
    PathScoringRules,
    get_path_scorer,
)
from src.similar_user.utils.pattern_storage import save_pattern_result


class PathScoringTest(unittest.TestCase):
    SOURCE_DEMOGRAPHIC_PATTERN_ALIASES = {
        "disease_patient",
        "symptom_patient",
        "unknown_patient",
    }

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

    def test_get_path_scorer_returns_registered_patient_disease_scorer(self) -> None:
        scorer = get_path_scorer("patient_disease_patient")

        self.assertIsInstance(scorer, PatientDiseasePatientPathScorer)

    def test_get_path_scorer_returns_registered_patient_symptom_scorer(self) -> None:
        scorer = get_path_scorer("patient_symptom_patient")

        self.assertIsInstance(scorer, PatientSymptomPatientPathScorer)

    def test_get_path_scorer_returns_registered_patient_unknown_scorer(self) -> None:
        scorer = get_path_scorer("patient_unknown_patient")

        self.assertIsInstance(scorer, PatientUnknownPatientPathScorer)

    def test_path_scorers_share_rules_without_inheriting_each_other(self) -> None:
        self.assertTrue(issubclass(PatientGamePatientPathScorer, PathScoringRules))
        self.assertTrue(issubclass(PatientDiseasePatientPathScorer, PathScoringRules))
        self.assertTrue(issubclass(PatientSymptomPatientPathScorer, PathScoringRules))
        self.assertTrue(issubclass(PatientUnknownPatientPathScorer, PathScoringRules))
        self.assertFalse(
            issubclass(PatientDiseasePatientPathScorer, PatientGamePatientPathScorer)
        )

    def test_get_path_scorer_rejects_unsupported_pattern(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unsupported scoring pattern"):
            get_path_scorer("disease_patient")

    @patch(
        "sys.argv",
        [
            "score_pattern_paths.py",
            "--source-id",
            "30010096",
            "--pattern",
            "patient_game_patient",
        ],
    )
    def test_parse_args_requires_explicit_source_id_and_pattern(self) -> None:
        args = parse_args()

        self.assertEqual(args.source_id, "30010096")
        self.assertEqual(args.pattern, "patient_game_patient")

    @patch(
        "sys.argv",
        [
            "score_pattern_paths.py",
            "--source-id",
            "30010096",
            "--patterns-from-config",
        ],
    )
    def test_parse_args_accepts_patterns_from_config(self) -> None:
        args = parse_args()

        self.assertEqual(args.source_id, "30010096")
        self.assertTrue(args.patterns_from_config)
        self.assertIsNone(args.pattern)

    @patch(
        "sys.argv",
        [
            "score_pattern_paths.py",
            "--source-id",
            "30010096",
            "--pattern",
            "patient_game_patient",
            "--patterns-from-config",
        ],
    )
    def test_parse_args_rejects_pattern_with_patterns_from_config(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args()

    def test_parse_args_accepts_all_public_pattern_aliases(self) -> None:
        for pattern in available_path_pattern_aliases():
            args = [
                "score_pattern_paths.py",
                "--source-id",
                "30010096",
                "--pattern",
                pattern,
            ]
            if pattern in self.SOURCE_DEMOGRAPHIC_PATTERN_ALIASES:
                args.extend(["--age", "66", "--education", "本科"])
            with self.subTest(pattern=pattern):
                with patch("sys.argv", args):
                    args = parse_args()

                self.assertEqual(args.pattern, pattern)

    @patch(
        "sys.argv",
        [
            "score_pattern_paths.py",
            "--source-id",
            "AU_DIS_0013",
            "--pattern",
            "disease_patient",
        ],
    )
    def test_parse_args_requires_age_and_education_for_direct_demographic_patterns(
        self,
    ) -> None:
        with self.assertRaises(SystemExit):
            parse_args()

    @patch(
        "sys.argv",
        [
            "score_pattern_paths.py",
            "--source-id",
            "AU_DIS_0013",
            "--pattern",
            "disease_patient",
            "--age",
            "66",
            "--education",
            "本科",
        ],
    )
    def test_parse_args_accepts_age_and_education_for_direct_demographic_patterns(
        self,
    ) -> None:
        args = parse_args()

        self.assertEqual(args.age, "66")
        self.assertEqual(args.education, "本科")

    @patch(
        "sys.argv",
        [
            "score_pattern_paths.py",
            "--source-id",
            "AU_DIS_0013",
            "--pattern",
            "disease_patient",
            "--age",
            "66",
            "--education",
            "未知学历",
        ],
    )
    def test_parse_args_rejects_unsupported_education_for_direct_demographic_patterns(
        self,
    ) -> None:
        with self.assertRaises(SystemExit):
            parse_args()

    @patch(
        "sys.argv",
        [
            "score_pattern_paths.py",
            "--source-id",
            "AU_DIS_0013",
            "--pattern",
            "disease_patient",
            "--age",
            "abc",
            "--education",
            "本科",
        ],
    )
    def test_parse_args_rejects_non_numeric_age_for_direct_demographic_patterns(
        self,
    ) -> None:
        with self.assertRaises(SystemExit):
            parse_args()

    @patch("sys.argv", ["score_pattern_paths.py", "30010096", "--pattern", "patient_game_patient"])
    def test_parse_args_rejects_positional_source_id(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args()

    @patch("sys.argv", ["score_pattern_paths.py", "--source-id", "30010096"])
    def test_parse_args_requires_pattern_option(self) -> None:
        with self.assertRaises(SystemExit):
            parse_args()

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

        self.assertEqual(result.total_score, 91.25)
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

    def test_patient_disease_patient_path_scorer_uses_age_and_education_only(self) -> None:
        scorer = PatientDiseasePatientPathScorer()
        path = PatientTasksetDiseaseTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            dis=DiseaseNode(id="AU_DIS_0013", name="遗忘型轻度认知障碍"),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="大专"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.education_score, 85.0)
        self.assertEqual(result.age_score, 100.0)
        self.assertEqual(result.total_score, 91.0)
        self.assertEqual(result.used_weights, {"education": 0.6, "age": 0.4})
        self.assertIsNone(result.completion_score)
        self.assertIsNone(result.activity_score)
        self.assertIsNone(result.task_type_score)
        self.assertIsNone(result.task_relevance_score)
        self.assertIn("不适用完成情况评分", result.details["completion"])

    def test_patient_disease_patient_path_scorer_reweights_available_dimensions(self) -> None:
        scorer = PatientDiseasePatientPathScorer()
        path = PatientTasksetDiseaseTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_DISEASE_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄=None, 执行学历="本科"),
            dis=DiseaseNode(id="AU_DIS_0013", name="遗忘型轻度认知障碍"),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="大专"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.education_score, 85.0)
        self.assertIsNone(result.age_score)
        self.assertEqual(result.total_score, 85.0)
        self.assertEqual(result.used_weights, {"education": 1.0})

    def test_patient_symptom_patient_path_scorer_uses_age_and_education_only(self) -> None:
        scorer = PatientSymptomPatientPathScorer()
        path = PatientTasksetSymptomTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            sym=SymptomNode(id="AU_SYM_0007", name="记忆下降"),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="大专"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.total_score, 91.0)
        self.assertEqual(result.used_weights, {"education": 0.6, "age": 0.4})
        self.assertIn(
            PathPattern.PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT.value,
            result.details["activity"],
        )

    def test_patient_unknown_patient_path_scorer_uses_age_and_education_only(self) -> None:
        scorer = PatientUnknownPatientPathScorer()
        path = PatientTasksetUnknownTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT,
            p=PatientNode(id="30010096"),
            s1=TaskInstanceSetNode(id="30010096_20220522", 执行年龄="66", 执行学历="本科"),
            un=UnknownNode(id="AU_UNKOWN_0005", name="未知实体"),
            s2=TaskInstanceSetNode(id="20113562_20211214", 执行年龄="64", 执行学历="大专"),
            p2=PatientNode(id="20113562"),
        )

        result = scorer.score(path)

        self.assertEqual(result.total_score, 91.0)
        self.assertEqual(result.used_weights, {"education": 0.6, "age": 0.4})
        self.assertIn(
            PathPattern.PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT.value,
            result.details["task_type"],
        )

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
        self.assertEqual(scored["scores"][0]["score"]["total_score"], 91.25)

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

    @patch("scripts.score_pattern_paths.save_scored_pattern_result")
    def test_save_scored_pattern_results_saves_each_result(
        self,
        mock_save_scored: Mock,
    ) -> None:
        results = [
            {"source_id": "30010096", "pattern": "PATTERN_A"},
            {"source_id": "30010096", "pattern": "PATTERN_B"},
        ]
        mock_save_scored.side_effect = [
            {"detail": Path("a.detail.json"), "summary": Path("a.summary.json")},
            {"detail": Path("b.detail.json"), "summary": Path("b.summary.json")},
        ]

        output_paths = save_scored_pattern_results(
            results,
            output_dir="data/scored_pattern_paths",
        )

        self.assertEqual(
            output_paths,
            [
                {"detail": Path("a.detail.json"), "summary": Path("a.summary.json")},
                {"detail": Path("b.detail.json"), "summary": Path("b.summary.json")},
            ],
        )
        mock_save_scored.assert_any_call(
            results[0],
            output_dir="data/scored_pattern_paths",
        )
        mock_save_scored.assert_any_call(
            results[1],
            output_dir="data/scored_pattern_paths",
        )

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

    def test_score_pattern_paths_scores_saved_patient_disease_paths(self) -> None:
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
                "paths": [
                    {
                        "row": {
                            "p": {"id": "30010096"},
                            "s1": {
                                "id": "30010096_20220522",
                                "执行年龄": "66",
                                "执行学历": "本科",
                            },
                            "dis": {"id": "AU_DIS_0013", "name": "遗忘型轻度认知障碍"},
                            "s2": {
                                "id": "20113562_20211214",
                                "执行年龄": "64",
                                "执行学历": "大专",
                            },
                            "p2": {"id": "20113562"},
                        }
                    }
                ],
            }
            save_pattern_result(result, config_path)

            scored = score_pattern_paths(
                "30010096",
                pattern="PATIENT_TASKSET_DISEASE_TASKSET_PATIENT",
                config_path=config_path,
            )

        self.assertEqual(scored["path_count"], 1)
        self.assertEqual(scored["scored_path_count"], 1)
        self.assertEqual(scored["scores"][0]["score"]["total_score"], 91.0)
        self.assertEqual(scored["scores"][0]["score"]["education_score"], 85.0)
        self.assertEqual(scored["scores"][0]["score"]["age_score"], 100.0)
        self.assertIsNone(scored["scores"][0]["score"]["completion_score"])

    def test_score_pattern_paths_scores_saved_patient_symptom_paths(self) -> None:
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
                "pattern": "PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT",
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
                            "s1": {
                                "id": "30010096_20220522",
                                "执行年龄": "66",
                                "执行学历": "本科",
                            },
                            "sym": {"id": "AU_SYM_0007", "name": "记忆下降"},
                            "s2": {
                                "id": "20113562_20211214",
                                "执行年龄": "64",
                                "执行学历": "大专",
                            },
                            "p2": {"id": "20113562"},
                        }
                    }
                ],
            }
            save_pattern_result(result, config_path)

            scored = score_pattern_paths(
                "30010096",
                pattern="PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT",
                config_path=config_path,
            )

        self.assertEqual(scored["path_count"], 1)
        self.assertEqual(scored["scored_path_count"], 1)
        self.assertEqual(scored["scores"][0]["score"]["total_score"], 91.0)
        self.assertEqual(scored["scores"][0]["score"]["education_score"], 85.0)
        self.assertEqual(scored["scores"][0]["score"]["age_score"], 100.0)
        self.assertIsNone(scored["scores"][0]["score"]["completion_score"])

    def test_score_pattern_paths_scores_saved_patient_unknown_paths(self) -> None:
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
                "pattern": "PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT",
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
                            "s1": {
                                "id": "30010096_20220522",
                                "执行年龄": "66",
                                "执行学历": "本科",
                            },
                            "un": {"id": "AU_UNKOWN_0005", "name": "未知实体"},
                            "s2": {
                                "id": "20113562_20211214",
                                "执行年龄": "64",
                                "执行学历": "大专",
                            },
                            "p2": {"id": "20113562"},
                        }
                    }
                ],
            }
            save_pattern_result(result, config_path)

            scored = score_pattern_paths(
                "30010096",
                pattern="PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT",
                config_path=config_path,
            )

        self.assertEqual(scored["path_count"], 1)
        self.assertEqual(scored["scored_path_count"], 1)
        self.assertEqual(scored["scores"][0]["score"]["total_score"], 91.0)
        self.assertEqual(scored["scores"][0]["score"]["education_score"], 85.0)
        self.assertEqual(scored["scores"][0]["score"]["age_score"], 100.0)
        self.assertIsNone(scored["scores"][0]["score"]["completion_score"])

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

    @patch("scripts.score_pattern_paths.score_pattern_paths")
    def test_score_configured_pattern_paths_uses_yaml_patterns(
        self,
        mock_score_paths: Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "candidate_ranking:",
                        "  patterns:",
                        "    - patient_game_patient",
                        "    - patient_disease_patient",
                        "  candidate_top_k: 10",
                    ]
                ),
                encoding="utf-8",
            )
            mock_score_paths.side_effect = [
                {"pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"},
                {"pattern": "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT"},
            ]

            results = score_configured_pattern_paths(
                "30010096",
                config_path=config_path,
                top_k=50,
            )

        self.assertEqual(
            results,
            [
                {"pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"},
                {"pattern": "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT"},
            ],
        )
        self.assertEqual(mock_score_paths.call_count, 2)
        mock_score_paths.assert_any_call(
            "30010096",
            pattern="patient_game_patient",
            config_path=config_path,
            path_index=None,
            top_k=50,
        )
        mock_score_paths.assert_any_call(
            "30010096",
            pattern="patient_disease_patient",
            config_path=config_path,
            path_index=None,
            top_k=50,
        )

    def test_score_configured_pattern_paths_rejects_direct_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "graph_path_limit:",
                        "  bands:",
                        "    - per_g: 1",
                        "candidate_ranking:",
                        "  patterns:",
                        "    - disease_patient",
                        "  candidate_top_k: 10",
                    ]
                ),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "patient-source patterns"):
                score_configured_pattern_paths(
                    "AU_DIS_0013",
                    config_path=config_path,
                )

    @patch("scripts.score_pattern_paths.save_scored_pattern_results")
    @patch("scripts.score_pattern_paths.score_configured_pattern_paths")
    def test_score_and_save_configured_pattern_paths_reuses_save_helper(
        self,
        mock_score_configured: Mock,
        mock_save_results: Mock,
    ) -> None:
        results = [
            {"source_id": "30010096", "pattern": "PATTERN_A"},
            {"source_id": "30010096", "pattern": "PATTERN_B"},
        ]
        mock_score_configured.return_value = results

        actual = score_and_save_configured_pattern_paths(
            "30010096",
            config_path="config/settings.yaml",
            top_k=50,
            output_dir="data/scored_pattern_paths",
        )

        self.assertEqual(actual, results)
        mock_score_configured.assert_called_once_with(
            "30010096",
            config_path="config/settings.yaml",
            path_index=None,
            top_k=50,
        )
        mock_save_results.assert_called_once_with(
            results,
            output_dir="data/scored_pattern_paths",
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
                age=None,
                education=None,
                scored_paths_dir=str(Path(temp_dir) / "scored_pattern_paths"),
            )

            exit_code = main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(mock_logger.info.call_count, 2)
        mock_logger.info.assert_any_call(
            "Saved scored pattern result: detail_path=%s, summary_path=%s",
            Path(temp_dir)
            / "scored_pattern_paths"
            / "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"
            / "30"
            / "30010096.detail.json",
            Path(temp_dir)
            / "scored_pattern_paths"
            / "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT"
            / "30"
            / "30010096.summary.json",
        )
        mock_logger.info.assert_any_call(
            json.dumps(expected, ensure_ascii=False, indent=2, default=str)
        )

    @patch("scripts.score_pattern_paths.save_scored_pattern_result")
    @patch("scripts.score_pattern_paths.LOGGER")
    @patch("scripts.score_pattern_paths.parse_args")
    def test_main_does_not_save_single_path_debug_result(
        self,
        mock_parse_args: Mock,
        mock_logger: Mock,
        mock_save_scored: Mock,
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
                            "i2": {"id": "20113562_20211214_348_y", "结果": "完成", "活跃": "是", "任务类型": "专属"},
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
                path_index=0,
            )
            mock_parse_args.return_value = Mock(
                source_id="30010096",
                pattern="PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                config=str(config_path),
                path_index=0,
                top_k=None,
                age=None,
                education=None,
                scored_paths_dir=str(Path(temp_dir) / "scored_pattern_paths"),
            )

            exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_save_scored.assert_not_called()
        mock_logger.info.assert_called_once_with(
            json.dumps(expected, ensure_ascii=False, indent=2, default=str)
        )

    @patch("scripts.score_pattern_paths.LOGGER")
    @patch("scripts.score_pattern_paths.save_scored_pattern_result")
    @patch("scripts.score_pattern_paths.score_configured_pattern_paths")
    @patch("scripts.score_pattern_paths.parse_args")
    def test_main_scores_configured_patterns_and_saves_each_result(
        self,
        mock_parse_args: Mock,
        mock_score_configured: Mock,
        mock_save_scored: Mock,
        mock_logger: Mock,
    ) -> None:
        results = [
            {
                "source_id": "30010096",
                "pattern": "PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT",
                "scores": [],
            },
            {
                "source_id": "30010096",
                "pattern": "PATIENT_TASKSET_DISEASE_TASKSET_PATIENT",
                "scores": [],
            },
        ]
        mock_parse_args.return_value = Mock(
            source_id="30010096",
            pattern=None,
            patterns_from_config=True,
            config="config/settings.yaml",
            path_index=None,
            top_k=50,
            age=None,
            education=None,
            scored_paths_dir="data/scored_pattern_paths",
        )
        mock_score_configured.return_value = results
        mock_save_scored.side_effect = [
            {
                "detail": Path("game.detail.json"),
                "summary": Path("game.summary.json"),
            },
            {
                "detail": Path("disease.detail.json"),
                "summary": Path("disease.summary.json"),
            },
        ]

        exit_code = main()

        self.assertEqual(exit_code, 0)
        mock_score_configured.assert_called_once_with(
            "30010096",
            config_path="config/settings.yaml",
            path_index=None,
            top_k=50,
        )
        self.assertEqual(mock_save_scored.call_count, 2)
        mock_save_scored.assert_any_call(
            results[0],
            output_dir="data/scored_pattern_paths",
        )
        mock_save_scored.assert_any_call(
            results[1],
            output_dir="data/scored_pattern_paths",
        )
        mock_logger.info.assert_any_call(
            json.dumps(results, ensure_ascii=False, indent=2, default=str)
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
            age=None,
            education=None,
            scored_paths_dir="data/scored_pattern_paths",
        )

        exit_code = main()

        self.assertEqual(exit_code, 1)
        mock_logger.exception.assert_called_once()


if __name__ == "__main__":
    unittest.main()
