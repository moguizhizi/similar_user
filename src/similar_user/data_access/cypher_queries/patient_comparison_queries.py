"""Cypher queries for comparing two patients' entity sets."""

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
