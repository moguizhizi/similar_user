"""Cypher queries for patient node collections."""

PATIENT_IDS_QUERY = """
MATCH (p:Patient)
RETURN p.id AS patient_id
ORDER BY patient_id
""".strip()

PATIENT_EXISTS_QUERY = """
MATCH (p:Patient {id: $patient_id})
RETURN count(p) > 0 AS exists
""".strip()

PATIENT_IDS_WITH_TRAINING_ON_DATE_QUERY = """
MATCH (p:Patient)
--(s:TaskInstanceSet)
WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) = date($base_date)
RETURN DISTINCT p.id AS patient_id
ORDER BY patient_id
""".strip()

PATIENT_IDS_WITH_TRAINING_ON_DATE_LIMIT_QUERY = """
MATCH (p:Patient)
--(s:TaskInstanceSet)
WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) = date($base_date)
WITH DISTINCT p.id AS patient_id
ORDER BY patient_id
LIMIT $limit
RETURN patient_id
""".strip()

SOURCE_PATIENT_IDS_WITH_SECONDARY_ABILITY_SCORES_QUERY = """
MATCH (p:Patient)
--(s:TaskInstanceSet)
--(:TaskInstance)
--(:Game)
WHERE
    s.`训练日期` IS NOT NULL AND
    any(field IN [
        "二级_书写能力",
        "二级_任务切换",
        "二级_冲突抑制",
        "二级_前瞻记忆",
        "二级_反应速度",
        "二级_口语生成",
        "二级_听理解",
        "二级_客体识别",
        "二级_工作记忆",
        "二级_归纳与推理",
        "二级_心算",
        "二级_情景记忆",
        "二级_情绪识别",
        "二级_情绪调节",
        "二级_手眼协调",
        "二级_持续注意",
        "二级_注意分配",
        "二级_注意广度",
        "二级_积极情绪",
        "二级_空间知觉",
        "二级_空间记忆",
        "二级_联结记忆",
        "二级_节律感知",
        "二级_表象与想象",
        "二级_记忆广度",
        "二级_语义系统",
        "二级_路径规划",
        "二级_运动知觉",
        "二级_选择注意",
        "二级_问题解决",
        "二级_阅读能力"
    ] WHERE s[field] IS NOT NULL)
RETURN DISTINCT p.id AS patient_id
ORDER BY patient_id
""".strip()
