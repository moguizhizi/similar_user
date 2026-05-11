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
