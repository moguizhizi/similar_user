"""Tests for domain graph path models."""

from __future__ import annotations

import unittest

from src.similar_user.domain import (
    TASK_INSTANCE_EXCLUSIVE_TYPE_VALUES,
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
    TASK_INSTANCE_ACTIVITY_VALUES,
    TASK_INSTANCE_RESULT_VALUES,
    TASK_INSTANCE_SET_EDUCATION_VALUES,
    GameNode,
    PathPattern,
    PatientNode,
    PatientTasksetTaskGameTaskTasksetPatientPath,
    PatternPathResult,
    TaskInstanceNode,
    TaskInstanceSetNode,
)


class DomainModelsTest(unittest.TestCase):
    def test_path_pattern_constant_matches_enum(self) -> None:
        self.assertEqual(
            PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT.value,
        )

    def test_patient_taskset_task_game_task_taskset_patient_path_can_be_built(
        self,
    ) -> None:
        path = PatientTasksetTaskGameTaskTasksetPatientPath(
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            p=PatientNode(id="40", name="患者_40", 性别="女"),
            s1=TaskInstanceSetNode(id="40_20220401", 训练日期="2022-04-01"),
            i1=TaskInstanceNode(id="40_20220401_8_x"),
            g=GameNode(id="8", name="打怪物"),
            i2=TaskInstanceNode(id="20102799_20230123_8_y"),
            s2=TaskInstanceSetNode(id="20102799_20230123", 训练日期="2023-01-23"),
            p2=PatientNode(id="20102799", name="患者_20102799", 性别="女"),
        )
        result = PatternPathResult(
            patient_id="40",
            pattern=PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
            paths=[path],
        )

        self.assertEqual(result.patient_id, "40")
        self.assertEqual(result.pattern, PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT)
        self.assertEqual(result.paths[0].g.name, "打怪物")

    def test_task_instance_set_education_values_are_bound_to_domain_field(self) -> None:
        self.assertIn("高中以后", TASK_INSTANCE_SET_EDUCATION_VALUES)
        self.assertIn("保密", TASK_INSTANCE_SET_EDUCATION_VALUES)

        path = PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
            {
                "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "row": {
                    "p": {"id": "40"},
                    "s1": {"id": "40_20220401", "执行学历": "高中以后"},
                    "i1": {"id": "40_20220401_8_x"},
                    "g": {"id": "8"},
                    "i2": {"id": "20102799_20230123_8_y"},
                    "s2": {"id": "20102799_20230123", "执行学历": "专科"},
                    "p2": {"id": "20102799"},
                },
            }
        )

        self.assertEqual(path.s1.执行学历, "高中以后")
        self.assertEqual(path.s2.执行学历, "专科")

    def test_task_instance_result_values_are_bound_to_domain_field(self) -> None:
        self.assertEqual(TASK_INSTANCE_RESULT_VALUES, ("完成", "未完成"))

        path = PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
            {
                "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "row": {
                    "p": {"id": "40"},
                    "s1": {"id": "40_20220401"},
                    "i1": {"id": "40_20220401_8_x", "结果": "完成"},
                    "g": {"id": "8"},
                    "i2": {"id": "20102799_20230123_8_y", "结果": "未完成"},
                    "s2": {"id": "20102799_20230123"},
                    "p2": {"id": "20102799"},
                },
            }
        )

        self.assertEqual(path.i1.结果, "完成")
        self.assertEqual(path.i2.结果, "未完成")

    def test_task_instance_activity_values_are_bound_to_domain_field(self) -> None:
        self.assertEqual(TASK_INSTANCE_ACTIVITY_VALUES, ("是", "否"))

        path = PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
            {
                "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "row": {
                    "p": {"id": "40"},
                    "s1": {"id": "40_20220401"},
                    "i1": {"id": "40_20220401_8_x", "结果": "完成"},
                    "g": {"id": "8"},
                    "i2": {"id": "20102799_20230123_8_y", "结果": "未完成", "活跃": "是"},
                    "s2": {"id": "20102799_20230123"},
                    "p2": {"id": "20102799"},
                },
            }
        )

        self.assertEqual(path.i2.活跃, "是")

    def test_task_instance_task_type_values_are_bound_to_domain_field(self) -> None:
        self.assertEqual(TASK_INSTANCE_EXCLUSIVE_TYPE_VALUES, ("专属", "自由"))

        path = PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
            {
                "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "row": {
                    "p": {"id": "40"},
                    "s1": {"id": "40_20220401"},
                    "i1": {"id": "40_20220401_8_x", "任务类型": "专属"},
                    "g": {"id": "8"},
                    "i2": {"id": "20102799_20230123_8_y", "任务类型": "自由"},
                    "s2": {"id": "20102799_20230123"},
                    "p2": {"id": "20102799"},
                },
            }
        )

        self.assertEqual(path.i1.任务类型, "专属")
        self.assertEqual(path.i2.任务类型, "自由")

    def test_patient_taskset_task_game_task_taskset_patient_path_can_be_built_from_dict(
        self,
    ) -> None:
        path = PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
            {
                "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "row": {
                    "p": {"id": "40", "name": "患者_40", "性别": "女"},
                    "s1": {"id": "40_20220401", "训练日期": "2022-04-01"},
                    "i1": {"id": "40_20220401_8_x", "状态": "完成"},
                    "g": {"id": "8", "name": "打怪物"},
                    "i2": {"id": "20102799_20230123_8_y"},
                    "s2": {"id": "20102799_20230123", "训练日期": "2023-01-23"},
                    "p2": {"id": "20102799", "name": "患者_20102799", "性别": "女"},
                },
            }
        )

        self.assertEqual(
            path.pattern,
            PathPattern.PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
        )
        self.assertEqual(path.p.id, "40")
        self.assertEqual(path.g.name, "打怪物")
        self.assertEqual(path.i1.状态, "完成")
        self.assertIsNone(path.g.艺术风格)

    def test_task_instance_set_rejects_unsupported_education_value_from_dict(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported value"):
            PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
                {
                    "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                    "row": {
                        "p": {"id": "40"},
                        "s1": {"id": "40_20220401", "执行学历": "夜校"},
                        "i1": {"id": "40_20220401_8_x"},
                        "g": {"id": "8"},
                        "i2": {"id": "20102799_20230123_8_y"},
                        "s2": {"id": "20102799_20230123"},
                        "p2": {"id": "20102799"},
                    },
                }
            )

    def test_task_instance_rejects_unsupported_result_value_from_dict(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported value"):
            PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
                {
                    "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                    "row": {
                        "p": {"id": "40"},
                        "s1": {"id": "40_20220401"},
                        "i1": {"id": "40_20220401_8_x", "结果": "达标"},
                        "g": {"id": "8"},
                        "i2": {"id": "20102799_20230123_8_y", "结果": "未完成"},
                        "s2": {"id": "20102799_20230123"},
                        "p2": {"id": "20102799"},
                    },
                }
            )

    def test_task_instance_rejects_unsupported_activity_value_from_dict(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported value"):
            PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
                {
                    "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                    "row": {
                        "p": {"id": "40"},
                        "s1": {"id": "40_20220401"},
                        "i1": {"id": "40_20220401_8_x", "结果": "完成"},
                        "g": {"id": "8"},
                        "i2": {"id": "20102799_20230123_8_y", "结果": "未完成", "活跃": "高"},
                        "s2": {"id": "20102799_20230123"},
                        "p2": {"id": "20102799"},
                    },
                }
            )

    def test_task_instance_rejects_unsupported_task_type_value_from_dict(self) -> None:
        with self.assertRaisesRegex(ValueError, "unsupported value"):
            PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
                {
                    "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                    "row": {
                        "p": {"id": "40"},
                        "s1": {"id": "40_20220401"},
                        "i1": {"id": "40_20220401_8_x", "任务类型": "句子识别"},
                        "g": {"id": "8"},
                        "i2": {"id": "20102799_20230123_8_y", "任务类型": "自由"},
                        "s2": {"id": "20102799_20230123"},
                        "p2": {"id": "20102799"},
                    },
                }
            )

    def test_game_node_can_load_extended_properties_from_dict(self) -> None:
        path = PatientTasksetTaskGameTaskTasksetPatientPath.from_dict(
            {
                "pattern": PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
                "row": {
                    "p": {"id": "40"},
                    "s1": {"id": "40_20220401"},
                    "i1": {"id": "40_20220401_8_x"},
                    "g": {
                        "id": "348",
                        "name": "真假句辨别",
                        "<elementId>": "4:11f7608e-a38a-4667-8632-459abd9062e0:12810",
                        "<id>": 12810,
                        "UI边框样式": "木纹",
                        "主要颜色": "棕_白_黄",
                        "同屏spine数量上限": 0.0,
                        "规则理解难度": 1,
                        "难度星级": "4",
                        "题目是否语音播放": "是",
                        "艺术风格": "卡通",
                        "背景环境": "教室",
                    },
                    "i2": {"id": "20102799_20230123_8_y"},
                    "s2": {"id": "20102799_20230123"},
                    "p2": {"id": "20102799"},
                },
            }
        )

        self.assertEqual(path.g.id, "348")
        self.assertEqual(path.g.name, "真假句辨别")
        self.assertEqual(path.g.UI边框样式, "木纹")
        self.assertEqual(path.g.主要颜色, "棕_白_黄")
        self.assertEqual(path.g.背景环境, "教室")
        self.assertEqual(path.g.艺术风格, "卡通")
        self.assertEqual(path.g.题目是否语音播放, "是")
        self.assertEqual(path.g.同屏spine数量上限, 0.0)
        self.assertEqual(path.g.规则理解难度, 1)
        self.assertEqual(path.g.难度星级, 4)

    def test_game_node_from_dict_can_be_used_directly(self) -> None:
        game = GameNode.from_dict(
            {
                "id": "348",
                "name": "真假句辨别",
                "艺术风格": "卡通",
                "背景环境": "教室",
                "难度星级": "4",
            }
        )

        self.assertEqual(game.id, "348")
        self.assertEqual(game.name, "真假句辨别")
        self.assertEqual(game.艺术风格, "卡通")
        self.assertEqual(game.背景环境, "教室")
        self.assertEqual(game.难度星级, 4)


if __name__ == "__main__":
    unittest.main()
