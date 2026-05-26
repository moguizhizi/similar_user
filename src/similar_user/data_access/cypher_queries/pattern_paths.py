"""Cypher queries for fixed-pattern path sampling."""

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY = """
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

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
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

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
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

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
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

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_DATED_RANDOMIZED_PATH_QUERY = """
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

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY = """
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

WITH p, s1, dis, s2, p2, path, rand() AS r
ORDER BY r

WITH dis, p2, collect({
    p: p,
    s1: s1,
    dis: dis,
    s2: s2,
    p2: p2
})[0] AS row

WITH dis, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
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

WITH p, s1, dis, s2, p2, path, rand() AS r
ORDER BY r

WITH dis, p2, collect({
    p: p,
    s1: s1,
    dis: dis,
    s2: s2,
    p2: p2
})[0] AS row

WITH dis, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
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

WITH p, s1, dis, s2, p2, path, rand() AS r
ORDER BY r

WITH dis, p2, collect({
    p: p,
    s1: s1,
    dis: dis,
    s2: s2,
    p2: p2
})[0] AS row

WITH dis, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
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

WITH p, s1, dis, s2, p2, path, rand() AS r
ORDER BY r

WITH dis, p2, collect({
    p: p,
    s1: s1,
    dis: dis,
    s2: s2,
    p2: p2
})[0] AS row

WITH dis, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY = """
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

WITH p, s1, dis, s2, p2, path, rand() AS r
ORDER BY r

WITH dis, p2, collect({
    p: p,
    s1: s1,
    dis: dis,
    s2: s2,
    p2: p2
})[0] AS row

WITH dis, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
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

WITH p, s1, dis, s2, p2, path, rand() AS r
ORDER BY r

WITH dis, p2, collect({
    p: p,
    s1: s1,
    dis: dis,
    s2: s2,
    p2: p2
})[0] AS row

WITH dis, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
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

WITH p, s1, dis, s2, p2, path, rand() AS r
ORDER BY r

WITH dis, p2, collect({
    p: p,
    s1: s1,
    dis: dis,
    s2: s2,
    p2: p2
})[0] AS row

WITH dis, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_DISEASE_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
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

WITH p, s1, dis, s2, p2, path, rand() AS r
ORDER BY r

WITH dis, p2, collect({
    p: p,
    s1: s1,
    dis: dis,
    s2: s2,
    p2: p2
})[0] AS row

WITH dis, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY = """
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

WITH p, s1, sym, s2, p2, path, rand() AS r
ORDER BY r

WITH sym, p2, collect({
    p: p,
    s1: s1,
    sym: sym,
    s2: s2,
    p2: p2
})[0] AS row

WITH sym, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
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

WITH p, s1, sym, s2, p2, path, rand() AS r
ORDER BY r

WITH sym, p2, collect({
    p: p,
    s1: s1,
    sym: sym,
    s2: s2,
    p2: p2
})[0] AS row

WITH sym, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
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

WITH p, s1, sym, s2, p2, path, rand() AS r
ORDER BY r

WITH sym, p2, collect({
    p: p,
    s1: s1,
    sym: sym,
    s2: s2,
    p2: p2
})[0] AS row

WITH sym, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
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

WITH p, s1, sym, s2, p2, path, rand() AS r
ORDER BY r

WITH sym, p2, collect({
    p: p,
    s1: s1,
    sym: sym,
    s2: s2,
    p2: p2
})[0] AS row

WITH sym, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY = """
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

WITH p, s1, sym, s2, p2, path, rand() AS r
ORDER BY r

WITH sym, p2, collect({
    p: p,
    s1: s1,
    sym: sym,
    s2: s2,
    p2: p2
})[0] AS row

WITH sym, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
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

WITH p, s1, sym, s2, p2, path, rand() AS r
ORDER BY r

WITH sym, p2, collect({
    p: p,
    s1: s1,
    sym: sym,
    s2: s2,
    p2: p2
})[0] AS row

WITH sym, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
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

WITH p, s1, sym, s2, p2, path, rand() AS r
ORDER BY r

WITH sym, p2, collect({
    p: p,
    s1: s1,
    sym: sym,
    s2: s2,
    p2: p2
})[0] AS row

WITH sym, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_SYMPTOM_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
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

WITH p, s1, sym, s2, p2, path, rand() AS r
ORDER BY r

WITH sym, p2, collect({
    p: p,
    s1: s1,
    sym: sym,
    s2: s2,
    p2: p2
})[0] AS row

WITH sym, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_QUERY = """
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

WITH p, s1, un, s2, p2, path, rand() AS r
ORDER BY r

WITH un, p2, collect({
    p: p,
    s1: s1,
    un: un,
    s2: s2,
    p2: p2
})[0] AS row

WITH un, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
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

WITH p, s1, un, s2, p2, path, rand() AS r
ORDER BY r

WITH un, p2, collect({
    p: p,
    s1: s1,
    un: un,
    s2: s2,
    p2: p2
})[0] AS row

WITH un, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
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

WITH p, s1, un, s2, p2, path, rand() AS r
ORDER BY r

WITH un, p2, collect({
    p: p,
    s1: s1,
    un: un,
    s2: s2,
    p2: p2
})[0] AS row

WITH un, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_DATE_WINDOW_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
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

WITH p, s1, un, s2, p2, path, rand() AS r
ORDER BY r

WITH un, p2, collect({
    p: p,
    s1: s1,
    un: un,
    s2: s2,
    p2: p2
})[0] AS row

WITH un, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_QUERY = """
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

WITH p, s1, un, s2, p2, path, rand() AS r
ORDER BY r

WITH un, p2, collect({
    p: p,
    s1: s1,
    un: un,
    s2: s2,
    p2: p2
})[0] AS row

WITH un, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
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

WITH p, s1, un, s2, p2, path, rand() AS r
ORDER BY r

WITH un, p2, collect({
    p: p,
    s1: s1,
    un: un,
    s2: s2,
    p2: p2
})[0] AS row

WITH un, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
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

WITH p, s1, un, s2, p2, path, rand() AS r
ORDER BY r

WITH un, p2, collect({
    p: p,
    s1: s1,
    un: un,
    s2: s2,
    p2: p2
})[0] AS row

WITH un, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

PATIENT_TASKSET_UNKNOWN_TASKSET_PATIENT_TRAINING_ORDER_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
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

WITH p, s1, un, s2, p2, path, rand() AS r
ORDER BY r

WITH un, p2, collect({
    p: p,
    s1: s1,
    un: un,
    s2: s2,
    p2: p2
})[0] AS row

WITH un, collect(row)[0..$per_g] AS rows

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY = """
MATCH path =
(d:Disease {id: $disease_id})
--(s:TaskInstanceSet)
--(p:Patient)

WITH d, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    d: d,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
MATCH path =
(d:Disease {id: $disease_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date)

WITH d, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    d: d,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
MATCH path =
(d:Disease {id: $disease_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) < date($end_date)

WITH d, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    d: d,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

DISEASE_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
MATCH path =
(d:Disease {id: $disease_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date) AND
    date(s.`训练日期`) < date($end_date)

WITH d, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    d: d,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY = """
MATCH path =
(sym:Symptom {id: $symptom_id})
--(s:TaskInstanceSet)
--(p:Patient)

WITH sym, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    sym: sym,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
MATCH path =
(sym:Symptom {id: $symptom_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date)

WITH sym, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    sym: sym,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
MATCH path =
(sym:Symptom {id: $symptom_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) < date($end_date)

WITH sym, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    sym: sym,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

SYMPTOM_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
MATCH path =
(sym:Symptom {id: $symptom_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date) AND
    date(s.`训练日期`) < date($end_date)

WITH sym, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    sym: sym,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_QUERY = """
MATCH path =
(un:Unknown {id: $unknown_id})
--(s:TaskInstanceSet)
--(p:Patient)

WITH un, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    un: un,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_START_DATE_QUERY = """
MATCH path =
(un:Unknown {id: $unknown_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date)

WITH un, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    un: un,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_END_DATE_QUERY = """
MATCH path =
(un:Unknown {id: $unknown_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) < date($end_date)

WITH un, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    un: un,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

UNKNOWN_TASKSET_PATIENT_RANDOMIZED_PATH_BY_DATE_RANGE_QUERY = """
MATCH path =
(un:Unknown {id: $unknown_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date) AND
    date(s.`训练日期`) < date($end_date)

WITH un, s, p, path, rand() AS r
ORDER BY r

WITH p, collect({
    un: un,
    s: s,
    p: p
})[0] AS row

RETURN row
""".strip()

DISEASE_TASKSET_PATIENT_CACHE_PATHS_QUERY = """
MATCH
(d:Disease)
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL

RETURN {
    d: d,
    s: s,
    p: p
} AS row
""".strip()

DISEASE_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY = """
MATCH
(d:Disease)
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date)

RETURN {
    d: d,
    s: s,
    p: p
} AS row
""".strip()

SYMPTOM_TASKSET_PATIENT_CACHE_PATHS_QUERY = """
MATCH
(sym:Symptom)
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL

RETURN {
    sym: sym,
    s: s,
    p: p
} AS row
""".strip()

SYMPTOM_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY = """
MATCH
(sym:Symptom)
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date)

RETURN {
    sym: sym,
    s: s,
    p: p
} AS row
""".strip()

UNKNOWN_TASKSET_PATIENT_CACHE_PATHS_QUERY = """
MATCH
(un:Unknown)
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL

RETURN {
    un: un,
    s: s,
    p: p
} AS row
""".strip()

UNKNOWN_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY = """
MATCH
(un:Unknown)
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date)

RETURN {
    un: un,
    s: s,
    p: p
} AS row
""".strip()

DISEASE_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY = """
MATCH
(d:Disease)
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    d.id IS NOT NULL AND
    s.`训练日期` IS NOT NULL

RETURN
    toString(d.id) AS source_id,
    d.name AS source_name,
    count(*) AS path_count,
    toString(max(date(s.`训练日期`))) AS latest_training_date
ORDER BY source_id
""".strip()

SYMPTOM_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY = """
MATCH
(sym:Symptom)
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    sym.id IS NOT NULL AND
    s.`训练日期` IS NOT NULL

RETURN
    toString(sym.id) AS source_id,
    sym.name AS source_name,
    count(*) AS path_count,
    toString(max(date(s.`训练日期`))) AS latest_training_date
ORDER BY source_id
""".strip()

UNKNOWN_TASKSET_PATIENT_SOURCE_SUMMARY_QUERY = """
MATCH
(un:Unknown)
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    un.id IS NOT NULL AND
    s.`训练日期` IS NOT NULL

RETURN
    toString(un.id) AS source_id,
    un.name AS source_name,
    count(*) AS path_count,
    toString(max(date(s.`训练日期`))) AS latest_training_date
ORDER BY source_id
""".strip()

DISEASE_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY = """
MATCH
(d:Disease {id: $source_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL

RETURN toString(max(date(s.`训练日期`))) AS latest_training_date
""".strip()

SYMPTOM_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY = """
MATCH
(sym:Symptom {id: $source_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL

RETURN toString(max(date(s.`训练日期`))) AS latest_training_date
""".strip()

UNKNOWN_TASKSET_PATIENT_LATEST_TRAINING_DATE_QUERY = """
MATCH
(un:Unknown {id: $source_id})
--(s:TaskInstanceSet)
--(p:Patient)

WHERE
    s.`训练日期` IS NOT NULL

RETURN toString(max(date(s.`训练日期`))) AS latest_training_date
""".strip()
