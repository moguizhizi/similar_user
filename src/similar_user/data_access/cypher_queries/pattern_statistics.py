"""Cypher queries for fixed-pattern statistics."""


def _require_taskset_total_score(query: str) -> str:
    """Require source and candidate TaskInstanceSet total scores in a query."""
    return query.replace(
        "    s1.`训练日期` IS NOT NULL AND\n"
        "    s2.`训练日期` IS NOT NULL AND",
        "    s1.`训练日期` IS NOT NULL AND\n"
        "    s2.`训练日期` IS NOT NULL AND\n"
        "    s1.`总分` IS NOT NULL AND\n"
        "    s2.`总分` IS NOT NULL AND",
    )

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY = """
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
    s2.`训练日期` IS NOT NULL

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY = """
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
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY = """
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
    date(s1.`训练日期`) >= date($start_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = """
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
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

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
    date(s1.`训练日期`) < date($end_date)

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
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL

RETURN
    count(*) AS totalPaths,
    count(DISTINCT dis) AS disCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT dis) AS disCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT dis) AS disCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT dis) AS disCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT dis) AS disCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)
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
    count(DISTINCT dis) AS disCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT dis) AS disCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT dis) AS disCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL

RETURN
    count(*) AS totalPaths,
    count(DISTINCT sym) AS symCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT sym) AS symCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT sym) AS symCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT sym) AS symCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT sym) AS symCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)
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
    count(DISTINCT sym) AS symCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT sym) AS symCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT sym) AS symCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL

RETURN
    count(*) AS totalPaths,
    count(DISTINCT un) AS unCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_START_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT un) AS unCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_END_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT un) AS unCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT un) AS unCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT un) AS unCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)
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
    count(DISTINCT un) AS unCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT un) AS unCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s1.`训练日期` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    count(*) AS totalPaths,
    count(DISTINCT un) AS unCount,
    count(DISTINCT p2) AS p2Count
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY = _require_taskset_total_score(
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_QUERY
)
PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY = _require_taskset_total_score(
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_START_DATE_QUERY
)
PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY = _require_taskset_total_score(
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_END_DATE_QUERY
)
PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = _require_taskset_total_score(
    PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY
)
PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY
)
PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY
)
PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY
)
PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY
)
PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY
)
PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY
)
PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY
)
PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY
)
PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_QUERY
)
PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_START_DATE_QUERY
)
PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_END_DATE_QUERY
)
PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY = _require_taskset_total_score(
    PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_PATTERN_STATISTICS_BY_DATE_RANGE_QUERY
)
