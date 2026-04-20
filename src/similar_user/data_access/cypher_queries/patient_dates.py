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

PATIENT_DISTINCT_GAMES_BY_START_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

RETURN DISTINCT g
""".strip()

PATIENT_DISTINCT_GAMES_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) <= date($end_date)

RETURN DISTINCT g
""".strip()

PATIENT_GAMES_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) <= date($end_date)

RETURN g
""".strip()

PATIENT_GAMES_BY_START_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date)

RETURN g
""".strip()

PATIENT_GAMES_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) <= date($end_date)

RETURN g
""".strip()

PATIENT_GAME_SET_COMPARISON_BY_END_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(:TaskInstance)
--(g1:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) <= date($end_date)

WITH collect(DISTINCT g1) AS games1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(:TaskInstance)
--(g2:Game)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) <= date($end_date)

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
    date(s1.`训练日期`) <= date($end_date)

WITH collect(DISTINCT g1) AS games1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(:TaskInstance)
--(g2:Game)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date) AND
    date(s2.`训练日期`) <= date($end_date)

WITH
    games1,
    collect(DISTINCT g2) AS games2

RETURN
    games1,
    games2
""".strip()

PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY = """
MATCH
(p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    i1.`常模分` IS NOT NULL AND
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) <= date($end_date)

WITH g, i1.`常模分` AS score1, date(s1.`训练日期`) AS d1
ORDER BY g.name, d1

WITH g, collect(score1) AS scores_p1

MATCH
(p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(i2:TaskInstance)
--(g:Game)

WHERE
    i2.`常模分` IS NOT NULL AND
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) <= date($end_date)

WITH g, scores_p1, i2.`常模分` AS score2, date(s2.`训练日期`) AS d2
ORDER BY g.name, d2

WITH g, scores_p1, collect(score2) AS scores_p2

RETURN
    g.name AS game,
    scores_p1,
    scores_p2
ORDER BY game
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
    date(s1.`训练日期`) <= date($end_date)

RETURN DISTINCT i1
""".strip()

PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) <= date($end_date)

RETURN DISTINCT i1
""".strip()

PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) <= date($end_date)

RETURN DISTINCT sym
""".strip()

PATIENT_SYMPTOM_SET_COMPARISON_BY_END_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(sym1:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) <= date($end_date)

WITH collect(DISTINCT sym1) AS symptoms1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(sym2:Symptom)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) <= date($end_date)

RETURN
    symptoms1,
    collect(DISTINCT sym2) AS symptoms2
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

PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) <= date($end_date)

RETURN DISTINCT sym
""".strip()

PATIENT_SYMPTOM_SET_COMPARISON_BY_DATE_RANGE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(sym1:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) <= date($end_date)

WITH collect(DISTINCT sym1) AS symptoms1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(sym2:Symptom)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date) AND
    date(s2.`训练日期`) <= date($end_date)

RETURN
    symptoms1,
    collect(DISTINCT sym2) AS symptoms2
""".strip()

PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) <= date($end_date)

RETURN DISTINCT dis
""".strip()

PATIENT_DISEASE_SET_COMPARISON_BY_END_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(dis1:Disease)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) <= date($end_date)

WITH collect(DISTINCT dis1) AS diseases1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(dis2:Disease)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) <= date($end_date)

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
    date(s1.`训练日期`) <= date($end_date)

WITH collect(DISTINCT dis1) AS diseases1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(dis2:Disease)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date) AND
    date(s2.`训练日期`) <= date($end_date)

RETURN
    diseases1,
    collect(DISTINCT dis2) AS diseases2
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
    date(s1.`训练日期`) <= date($end_date)

RETURN DISTINCT dis
""".strip()

PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) <= date($end_date)

RETURN DISTINCT un
""".strip()

PATIENT_UNKNOWN_SET_COMPARISON_BY_END_DATE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(un1:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) <= date($end_date)

WITH collect(DISTINCT un1) AS unknowns1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(un2:Unknown)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) <= date($end_date)

RETURN
    unknowns1,
    collect(DISTINCT un2) AS unknowns2
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

PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) <= date($end_date)

RETURN DISTINCT un
""".strip()

PATIENT_UNKNOWN_SET_COMPARISON_BY_DATE_RANGE_QUERY = """
MATCH (p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(un1:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) <= date($end_date)

WITH collect(DISTINCT un1) AS unknowns1

MATCH (p2:Patient {id: $comparison_patient_id})
--(s2:TaskInstanceSet)
--(un2:Unknown)

WHERE
    s2.`训练日期` IS NOT NULL AND
    date(s2.`训练日期`) >= date($start_date) AND
    date(s2.`训练日期`) <= date($end_date)

RETURN
    unknowns1,
    collect(DISTINCT un2) AS unknowns2
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
