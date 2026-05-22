"""Cypher queries for one patient's training timeline and task history."""

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

PATIENT_TASK_INSTANCE_SET_ORDERED_TRAINING_DATES_QUERY = """
MATCH (p:Patient {id: $patient_id})--(s:TaskInstanceSet)
WHERE s.`训练日期` IS NOT NULL

WITH p, s
ORDER BY date(s.`训练日期`)

RETURN
    p,
    collect(s.`训练日期`) AS orderedDatesa
""".strip()

PATIENT_TOTAL_SCORE_TIMEPOINTS_QUERY = """
MATCH (p:Patient {id: $patient_id})--(s:TaskInstanceSet)
WHERE
    s.`训练日期` IS NOT NULL AND
    s.`总分` IS NOT NULL

WITH DISTINCT s, toFloat(s.`总分`) AS totalScore
WHERE totalScore IS NOT NULL

RETURN
    s.id AS instance_set_id,
    s.`训练日期` AS training_date,
    totalScore AS total_score
ORDER BY date(s.`训练日期`), instance_set_id
""".strip()

PATIENT_TOTAL_SCORE_BY_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})--(s:TaskInstanceSet)
WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) = date($training_date) AND
    s.`总分` IS NOT NULL

WITH DISTINCT s, toFloat(s.`总分`) AS totalScore
WHERE totalScore IS NOT NULL

RETURN
    s.id AS instance_set_id,
    s.`训练日期` AS training_date,
    totalScore AS total_score
ORDER BY instance_set_id
LIMIT 1
""".strip()

PATIENT_TRAINING_TASK_HISTORY_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE s.`训练日期` IS NOT NULL

WITH
    date(s.`训练日期`) AS trainingDate,
    s,
    i,
    g
ORDER BY trainingDate

RETURN
    trainingDate,
    s,
    i,
    g
""".strip()

PATIENT_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date) AND
    date(s.`训练日期`) < date($end_date)

WITH
    date(s.`训练日期`) AS trainingDate,
    g
ORDER BY trainingDate

RETURN
    trainingDate,
    g
""".strip()

PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date) AND
    date(s.`训练日期`) < date($end_date) AND
    i.`任务类型` = "专属"

WITH
    date(s.`训练日期`) AS trainingDate,
    g
ORDER BY trainingDate

RETURN
    trainingDate,
    g
""".strip()
