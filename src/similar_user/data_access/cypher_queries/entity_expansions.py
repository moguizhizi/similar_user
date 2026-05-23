"""Reusable Cypher queries that expand one graph entity into related context."""

DISEASE_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY = """
MATCH path =
(d:Disease {id: $disease_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WITH d, s, i, g, path, rand() AS r
ORDER BY r

WITH g, collect({
    d: d,
    s: s,
    i: i,
    g: g
})[0] AS row

RETURN row
""".strip()

DISEASE_TASKSET_EXCLUSIVE_TASK_GAME_SAMPLED_PER_GAME_QUERY = """
MATCH path =
(d:Disease {id: $disease_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE i.`任务类型` = "专属"

WITH d, s, i, g, path, rand() AS r
ORDER BY r

WITH g, collect({
    d: d,
    s: s,
    i: i,
    g: g
})[0] AS row

RETURN row
""".strip()

DISEASE_EDUCATION_AGE_EXCLUSIVE_TASK_GAME_QUERY = """
MATCH (d:Disease {id: $disease_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE
    i.`任务类型` = "专属" AND
    s.`执行学历` = $education AND
    s.`执行年龄` IS NOT NULL AND
    toInteger(toFloat(s.`执行年龄`)) >= $min_age AND
    toInteger(toFloat(s.`执行年龄`)) <= $max_age

RETURN
    g,
    count(*) AS support_count,
    count(DISTINCT s) AS taskset_count,
    count(DISTINCT i) AS task_instance_count

ORDER BY support_count DESC, toString(g.id) ASC
""".strip()

SYMPTOM_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY = """
MATCH path =
(sym:Symptom {id: $symptom_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WITH sym, s, i, g, path, rand() AS r
ORDER BY r

WITH g, collect({
    sym: sym,
    s: s,
    i: i,
    g: g
})[0] AS row

RETURN row
""".strip()

SYMPTOM_TASKSET_EXCLUSIVE_TASK_GAME_SAMPLED_PER_GAME_QUERY = """
MATCH path =
(sym:Symptom {id: $symptom_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE i.`任务类型` = "专属"

WITH sym, s, i, g, path, rand() AS r
ORDER BY r

WITH g, collect({
    sym: sym,
    s: s,
    i: i,
    g: g
})[0] AS row

RETURN row
""".strip()

SYMPTOM_EDUCATION_AGE_EXCLUSIVE_TASK_GAME_QUERY = """
MATCH (sym:Symptom {id: $symptom_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE
    i.`任务类型` = "专属" AND
    s.`执行学历` = $education AND
    s.`执行年龄` IS NOT NULL AND
    toInteger(toFloat(s.`执行年龄`)) >= $min_age AND
    toInteger(toFloat(s.`执行年龄`)) <= $max_age

RETURN
    g,
    count(*) AS support_count,
    count(DISTINCT s) AS taskset_count,
    count(DISTINCT i) AS task_instance_count

ORDER BY support_count DESC, toString(g.id) ASC
""".strip()

UNKNOWN_TASKSET_TASK_GAME_SAMPLED_PER_GAME_QUERY = """
MATCH path =
(un:Unknown {id: $unknown_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WITH un, s, i, g, path, rand() AS r
ORDER BY r

WITH g, collect({
    un: un,
    s: s,
    i: i,
    g: g
})[0] AS row

RETURN row
""".strip()

UNKNOWN_EDUCATION_AGE_EXCLUSIVE_TASK_GAME_QUERY = """
MATCH (un:Unknown {id: $unknown_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE
    i.`任务类型` = "专属" AND
    s.`执行学历` = $education AND
    s.`执行年龄` IS NOT NULL AND
    toInteger(toFloat(s.`执行年龄`)) >= $min_age AND
    toInteger(toFloat(s.`执行年龄`)) <= $max_age

RETURN
    g,
    count(*) AS support_count,
    count(DISTINCT s) AS taskset_count,
    count(DISTINCT i) AS task_instance_count

ORDER BY support_count DESC, toString(g.id) ASC
""".strip()

UNKNOWN_TASKSET_EXCLUSIVE_TASK_GAME_SAMPLED_PER_GAME_QUERY = """
MATCH path =
(un:Unknown {id: $unknown_id})
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE i.`任务类型` = "专属"

WITH un, s, i, g, path, rand() AS r
ORDER BY r

WITH g, collect({
    un: un,
    s: s,
    i: i,
    g: g
})[0] AS row

RETURN row
""".strip()
