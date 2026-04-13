"""Tests for domain graph path models."""

from __future__ import annotations

import unittest

from src.similar_user.domain import (
    PATIENT_TASKSET_TASK_GAME_TASK_TASKSET_PATIENT,
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


if __name__ == "__main__":
    unittest.main()
