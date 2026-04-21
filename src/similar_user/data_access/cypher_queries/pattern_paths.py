"""Cypher queries for fixed-pattern path sampling."""

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_RANDOMIZED_PATH_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)
--(i2:TaskInstance)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE p2 <> p

WITH p, s1, i1, g, i2, s2, p2, path, rand() AS r
ORDER BY r

WITH g, p2, collect({
    p: p,
    s1: s1,
    i1: i1,
    g: g,
    i2: i2,
    s2: s2,
    p2: p2
})[0] AS row

WITH g, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
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

WITH p, s1, i1, g, i2, s2, p2, path, rand() AS r
ORDER BY r

WITH g, p2, collect({
    p: p,
    s1: s1,
    i1: i1,
    g: g,
    i2: i2,
    s2: s2,
    p2: p2
})[0] AS row

WITH g, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
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

WITH p, s1, i1, g, i2, s2, p2, path, rand() AS r
ORDER BY r

WITH g, p2, collect({
    p: p,
    s1: s1,
    i1: i1,
    g: g,
    i2: i2,
    s2: s2,
    p2: p2
})[0] AS row

WITH g, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
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

WITH p, s1, i1, g, i2, s2, p2, path, rand() AS r
ORDER BY r

WITH g, p2, collect({
    p: p,
    s1: s1,
    i1: i1,
    g: g,
    i2: i2,
    s2: s2,
    p2: p2
})[0] AS row

WITH g, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_END_DATE_RANDOMIZED_PATH_QUERY = """
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

WITH p, s1, i1, g, i2, s2, p2, path, rand() AS r
ORDER BY r

WITH g, p2, collect({
    p: p,
    s1: s1,
    i1: i1,
    g: g,
    i2: i2,
    s2: s2,
    p2: p2
})[0] AS row

WITH g, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()
