"""Cypher queries for patient score-series comparisons."""

PATIENT_GAME_NORM_SCORE_SERIES_COMPARISON_BY_END_DATE_QUERY = """
MATCH
(p1:Patient {id: $primary_patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    i1.`常模分` IS NOT NULL AND
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

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
    date(s2.`训练日期`) < date($end_date)

WITH g, scores_p1, i2.`常模分` AS score2, date(s2.`训练日期`) AS d2
ORDER BY g.name, d2

WITH g, scores_p1, collect(score2) AS scores_p2

RETURN
    g.name AS game,
    scores_p1,
    scores_p2
ORDER BY game
""".strip()
