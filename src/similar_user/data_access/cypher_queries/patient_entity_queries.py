"""Cypher queries for one patient's related task and medical entity sets."""

PATIENT_PROFILE_ENTITIES_BY_EFFECTIVE_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s:TaskInstanceSet)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) <= date($base_date)

WITH max(date(s.`训练日期`)) AS effective_date

MATCH (p:Patient {id: $patient_id})
--(s:TaskInstanceSet)

WHERE date(s.`训练日期`) = effective_date

OPTIONAL MATCH (s)--(dis:Disease)
OPTIONAL MATCH (s)--(sym:Symptom)
OPTIONAL MATCH (s)--(un:Unknown)

RETURN
    toString(effective_date) AS effective_date,
    collect(DISTINCT dis) AS diseases,
    collect(DISTINCT sym) AS symptoms,
    collect(DISTINCT un) AS unknowns
""".strip()

PATIENT_DISTINCT_TASK_INSTANCES_BY_START_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

RETURN DISTINCT i1
""".strip()

PATIENT_DISTINCT_TASK_INSTANCES_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT i1
""".strip()

PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT i1
""".strip()

PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT sym
""".strip()

PATIENT_DISTINCT_SYMPTOMS_BY_START_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

RETURN DISTINCT sym
""".strip()

PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT sym
""".strip()

PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT dis
""".strip()

PATIENT_DISTINCT_DISEASES_BY_START_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

RETURN DISTINCT dis
""".strip()

PATIENT_DISTINCT_DISEASES_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT dis
""".strip()

PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT un
""".strip()

PATIENT_DISTINCT_UNKNOWNS_BY_START_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

RETURN DISTINCT un
""".strip()

PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT un
""".strip()
