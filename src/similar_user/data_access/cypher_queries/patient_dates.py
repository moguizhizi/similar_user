"""Cypher queries for patient dates and game collections."""

PATIENT_TRAINING_DATE_GAMES_BY_START_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

WITH
    date(s1.`训练日期`) AS trainingDate,
    collect(DISTINCT g) AS games

RETURN
    trainingDate,
    games
ORDER BY trainingDate
""".strip()

PATIENT_DISTINCT_GAMES_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) <= date($end_date)

RETURN DISTINCT g
""".strip()

PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY = """
MATCH (p:Patient {id: $patient_id})--(s:TaskInstanceSet)
WHERE s.`训练日期` IS NOT NULL

WITH p, s
ORDER BY date(s.`训练日期`)

RETURN
    p,
    collect(s.`训练日期`) AS orderedDatesa
""".strip()
