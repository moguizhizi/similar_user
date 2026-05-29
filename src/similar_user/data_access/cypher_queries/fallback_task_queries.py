"""Cypher queries for task recommendation fallback flows."""

PROFILE_MATCHED_EXCLUSIVE_TASKS_QUERY = """
MATCH (p:Patient)
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) < date($base_date) AND
    i.`任务类型` = "专属" AND
    ($gender IS NULL OR p.`性别` = $gender) AND
    ($education IS NULL OR s.`执行学历` = $education) AND
    (
        $age IS NULL OR
        (
            s.`执行年龄` IS NOT NULL AND
            toInteger(toFloat(s.`执行年龄`)) >= $min_age AND
            toInteger(toFloat(s.`执行年龄`)) <= $max_age
        )
    )

WITH
    g,
    count(*) AS support_count,
    count(DISTINCT p) AS patient_count,
    max(date(s.`训练日期`)) AS latest_training_date

RETURN
    g,
    support_count,
    patient_count,
    latest_training_date

ORDER BY support_count DESC, patient_count DESC, latest_training_date DESC, toString(g.id) ASC
LIMIT $limit
""".strip()

GLOBAL_POPULAR_EXCLUSIVE_TASKS_QUERY = """
MATCH (p:Patient)
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) < date($base_date) AND
    i.`任务类型` = "专属"

WITH
    g,
    count(*) AS support_count,
    count(DISTINCT p) AS patient_count,
    max(date(s.`训练日期`)) AS latest_training_date

RETURN
    g,
    support_count,
    patient_count,
    latest_training_date

ORDER BY support_count DESC, patient_count DESC, latest_training_date DESC, toString(g.id) ASC
LIMIT $limit
""".strip()
