"""Cypher queries for comparing patient entity sets and ability scores."""

SECONDARY_ABILITY_SCORE_FIELDS = (
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
    "二级_阅读能力",
)


def _cypher_string_list(values: tuple[str, ...]) -> str:
    return "[\n        " + ",\n        ".join(f'"{value}"' for value in values) + "\n    ]"


def _secondary_ability_score_map(node_name: str) -> str:
    return "{\n        " + ",\n        ".join(
        f"`{field}`: {node_name}.`{field}`" for field in SECONDARY_ABILITY_SCORE_FIELDS
    ) + "\n    }"


SECONDARY_ABILITY_SCORE_FIELD_LIST = _cypher_string_list(SECONDARY_ABILITY_SCORE_FIELDS)
SECONDARY_ABILITY_SCORE_RETURN_MAP = _secondary_ability_score_map("window_s")

PATIENT_GAME_SET_COMPARISON_BY_END_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(:TaskInstance)
--(g1:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

WITH collect(DISTINCT g1) AS games1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(:TaskInstance)
--(g2:Game)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) < date($end_date)

WITH
    games1,
    collect(DISTINCT g2) AS games2

RETURN
    games1,
    games2
""".strip()

PATIENT_GAME_SET_COMPARISON_BY_START_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(:TaskInstance)
--(g1:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

WITH collect(DISTINCT g1) AS games1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(:TaskInstance)
--(g2:Game)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date)

WITH
    games1,
    collect(DISTINCT g2) AS games2

RETURN
    games1,
    games2
""".strip()

PATIENT_GAME_SET_COMPARISON_BY_DATE_RANGE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(:TaskInstance)
--(g1:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

WITH collect(DISTINCT g1) AS games1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(:TaskInstance)
--(g2:Game)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date) AND
    date(s2.`训练日期`) < date($end_date)

WITH
    games1,
    collect(DISTINCT g2) AS games2

RETURN
    games1,
    games2
""".strip()

PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(sym1:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

WITH collect(DISTINCT sym1) AS symptoms1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(sym2:Symptom)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) < date($end_date)

RETURN
    symptoms1,
    collect(DISTINCT sym2) AS symptoms2
""".strip()

PATIENT_SYMPTOM_SET_COMPARISON_BY_START_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(sym1:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

WITH collect(DISTINCT sym1) AS symptoms1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(sym2:Symptom)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date)

RETURN
    symptoms1,
    collect(DISTINCT sym2) AS symptoms2
""".strip()

PATIENT_SYMPTOM_SET_COMPARISON_BY_DATE_RANGE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(sym1:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

WITH collect(DISTINCT sym1) AS symptoms1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(sym2:Symptom)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date) AND
    date(s2.`训练日期`) < date($end_date)

RETURN
    symptoms1,
    collect(DISTINCT sym2) AS symptoms2
""".strip()

PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(dis1:Disease)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

WITH collect(DISTINCT dis1) AS diseases1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(dis2:Disease)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) < date($end_date)

RETURN
    diseases1,
    collect(DISTINCT dis2) AS diseases2
""".strip()

PATIENT_DISEASE_SET_COMPARISON_BY_START_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(dis1:Disease)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

WITH collect(DISTINCT dis1) AS diseases1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(dis2:Disease)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date)

RETURN
    diseases1,
    collect(DISTINCT dis2) AS diseases2
""".strip()

PATIENT_DISEASE_SET_COMPARISON_BY_DATE_RANGE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(dis1:Disease)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

WITH collect(DISTINCT dis1) AS diseases1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(dis2:Disease)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date) AND
    date(s2.`训练日期`) < date($end_date)

RETURN
    diseases1,
    collect(DISTINCT dis2) AS diseases2
""".strip()

PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(un1:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

WITH collect(DISTINCT un1) AS unknowns1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(un2:Unknown)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) < date($end_date)

RETURN
    unknowns1,
    collect(DISTINCT un2) AS unknowns2
""".strip()

PATIENT_UNKNOWN_SET_COMPARISON_BY_START_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(un1:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

WITH collect(DISTINCT un1) AS unknowns1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(un2:Unknown)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date)

RETURN
    unknowns1,
    collect(DISTINCT un2) AS unknowns2
""".strip()

PATIENT_UNKNOWN_SET_COMPARISON_BY_DATE_RANGE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(un1:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

WITH collect(DISTINCT un1) AS unknowns1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(un2:Unknown)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date) AND
    date(s2.`训练日期`) < date($end_date)

RETURN
    unknowns1,
    collect(DISTINCT un2) AS unknowns2
""".strip()

PATIENT_SECONDARY_ABILITY_SCORES_BY_DISEASE_COURSE_WINDOW_QUERY = f"""
MATCH (p:Patient {{id: $patient_id}})
--(s:TaskInstanceSet)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) <= date($base_date) AND
    any(field IN {SECONDARY_ABILITY_SCORE_FIELD_LIST} WHERE s[field] IS NOT NULL)

WITH
    p,
    max(date(s.`训练日期`)) AS effective_ability_date

MATCH (p)
--(window_s:TaskInstanceSet)

WHERE
    window_s.`训练日期` IS NOT NULL AND
    date(window_s.`训练日期`) >= (
        effective_ability_date - duration({{days: $disease_course_window_days}})
    ) AND
    date(window_s.`训练日期`) < effective_ability_date AND
    any(field IN {SECONDARY_ABILITY_SCORE_FIELD_LIST} WHERE window_s[field] IS NOT NULL)

RETURN
    effective_ability_date,
    window_s.id AS instance_set_id,
    window_s.`训练日期` AS training_date,
    {SECONDARY_ABILITY_SCORE_RETURN_MAP} AS secondary_ability_scores

ORDER BY date(window_s.`训练日期`)
""".strip()

PATIENT_TOTAL_SCORES_BY_DISEASE_COURSE_WINDOW_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s:TaskInstanceSet)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) <= date($base_date) AND
    s.`总分` IS NOT NULL

WITH
    p,
    max(date(s.`训练日期`)) AS effective_total_score_date

MATCH (p)
--(window_s:TaskInstanceSet)

WHERE
    window_s.`训练日期` IS NOT NULL AND
    date(window_s.`训练日期`) >= (
        effective_total_score_date - duration({days: $disease_course_window_days})
    ) AND
    date(window_s.`训练日期`) < effective_total_score_date AND
    window_s.`总分` IS NOT NULL

WITH DISTINCT
    effective_total_score_date,
    window_s,
    toFloat(window_s.`总分`) AS totalScore
WHERE totalScore IS NOT NULL

RETURN
    effective_total_score_date,
    window_s.id AS instance_set_id,
    window_s.`训练日期` AS training_date,
    totalScore AS total_score

ORDER BY date(window_s.`训练日期`)
""".strip()
