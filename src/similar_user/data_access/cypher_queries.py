"""Central place for Cypher query definitions."""

PATIENT_TASK_SET_TASK_GAME_TASK_SET_PATIENT_PATTERN_STATISTICS_QUERY = """
MATCH path =
(p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)
--(i2:TaskInstance)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE p2 <> p

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()

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

WITH g, p2, path, rand() AS r
ORDER BY r

WITH g, p2, collect(path)[0] AS path

WITH g, collect(path)[0..$per_g] AS paths

UNWIND paths AS path

RETURN path
LIMIT $limit
""".strip()

P_E_I_G_I_E_P_PATH_STATISTICS_QUERY = """
UNWIND $limits AS lim

MATCH (p:Patient {id: $patient_id})
CALL apoc.path.expandConfig(p, {
  minLevel: 6,
  maxLevel: 6,
  bfs: true,
  limit: lim,
  uniqueness: "NODE_GLOBAL",
  labelFilter: "+Patient|+TaskInstanceSet|+TaskInstance|+Game"
})
YIELD path

WITH p, lim, path,
     nodes(path)[3] AS gNode,
     last(nodes(path)) AS endNode

WHERE
    nodes(path)[1]:TaskInstanceSet AND
    nodes(path)[2]:TaskInstance AND
    nodes(path)[3]:Game AND
    nodes(path)[4]:TaskInstance AND
    nodes(path)[5]:Patient AND
    endNode:Patient AND
    endNode <> p

RETURN
    lim,
    count(*) AS totalPaths,
    count(DISTINCT gNode) AS gCount,
    count(DISTINCT endNode) AS pCount
ORDER BY lim
""".strip()
