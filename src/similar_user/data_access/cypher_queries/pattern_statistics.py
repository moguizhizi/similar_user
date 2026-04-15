"""Cypher queries for fixed-pattern statistics."""

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)
--(i2:TaskInstance)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE p <> p2

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)
--(i2:TaskInstance)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)
--(i2:TaskInstance)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s1.`训练日期`) <= date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)
--(i2:TaskInstance)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s1.`训练日期`) >= date($start_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)
--(i2:TaskInstance)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) <= date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()
