"""Cypher queries for one patient's related task and medical entity sets."""

PATIENT_PROFILE_ENTITIES_BY_EFFECTIVE_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s:TaskInstanceSet)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) <= date($base_date)

WITH max(date(s.`训练日期`)) AS effective_date

MATCH (p:Patient {id: $patient_id})
--(s:TaskInstanceSet)

WHERE date(s.`训练日期`) = effective_date

OPTIONAL MATCH (s)--(dis:Disease)
OPTIONAL MATCH (s)--(sym:Symptom)
OPTIONAL MATCH (s)--(un:Unknown)

RETURN
    toString(effective_date) AS effective_date,
    collect(DISTINCT dis) AS diseases,
    collect(DISTINCT sym) AS symptoms,
    collect(DISTINCT un) AS unknowns
""".strip()

PATIENT_DIRECT_ENTITY_SCORING_PROFILE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(profile_s:TaskInstanceSet)

WHERE
    profile_s.`训练日期` IS NOT NULL AND
    date(profile_s.`训练日期`) <= date($base_date)

WITH
    p,
    max(date(profile_s.`训练日期`)) AS effective_date

MATCH (p)
--(profile_s:TaskInstanceSet)

WHERE
    date(profile_s.`训练日期`) = effective_date AND
    p.`性别` IS NOT NULL AND
    profile_s.`执行学历` IS NOT NULL AND
    profile_s.`执行年龄` IS NOT NULL

WITH
    p,
    profile_s,
    effective_date,
    p.`性别` AS gender,
    profile_s.`执行学历` AS education,
    toInteger(toFloat(profile_s.`执行年龄`)) AS profile_age,
    duration.inDays(effective_date, date($base_date)).days AS age_delta_days

WITH
    p,
    profile_s,
    effective_date,
    gender,
    education,
    profile_age,
    profile_age + toInteger(floor(age_delta_days / 365.25)) AS age_at_base_date

OPTIONAL MATCH (profile_s)--(dis:Disease)
WITH
    p,
    profile_s,
    effective_date,
    gender,
    education,
    profile_age,
    age_at_base_date,
    [x IN collect(DISTINCT dis.id) WHERE x IS NOT NULL] AS disease_ids

OPTIONAL MATCH (profile_s)--(sym:Symptom)
WITH
    p,
    profile_s,
    effective_date,
    gender,
    education,
    profile_age,
    age_at_base_date,
    disease_ids,
    [x IN collect(DISTINCT sym.id) WHERE x IS NOT NULL] AS symptom_ids

OPTIONAL MATCH (profile_s)--(un:Unknown)

RETURN
    toString(p.id) AS patient_id,
    toString(effective_date) AS effective_date,
    gender,
    education,
    profile_age,
    age_at_base_date,
    disease_ids,
    symptom_ids,
    [x IN collect(DISTINCT un.id) WHERE x IS NOT NULL] AS unknown_ids
""".strip()

PATIENT_PROFILE_GENDER_EDUCATION_AGE_EXCLUSIVE_TASK_GAME_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(profile_s:TaskInstanceSet)

WHERE
    p.`性别` IS NOT NULL AND
    profile_s.`训练日期` IS NOT NULL AND
    date(profile_s.`训练日期`) <= date($base_date)

WITH
    p,
    max(date(profile_s.`训练日期`)) AS effective_date

MATCH (p)
--(profile_s:TaskInstanceSet)

WHERE
    date(profile_s.`训练日期`) = effective_date AND
    profile_s.`执行学历` IS NOT NULL AND
    profile_s.`执行年龄` IS NOT NULL

WITH
    effective_date,
    profile_s,
    p.`性别` AS gender,
    profile_s.`执行学历` AS education,
    toInteger(toFloat(profile_s.`执行年龄`)) AS profile_age,
    duration.inDays(effective_date, date($base_date)).days AS age_delta_days

WITH
    effective_date,
    profile_s,
    gender,
    education,
    profile_age,
    profile_age + toInteger(floor(age_delta_days / 365.25)) AS age_at_base_date

OPTIONAL MATCH (profile_s)--(dis:Disease)
WITH
    effective_date,
    profile_s,
    gender,
    education,
    profile_age,
    age_at_base_date,
    [x IN collect(DISTINCT dis) WHERE x IS NOT NULL] AS diseases

OPTIONAL MATCH (profile_s)--(sym:Symptom)
WITH
    effective_date,
    profile_s,
    gender,
    education,
    profile_age,
    age_at_base_date,
    diseases,
    [x IN collect(DISTINCT sym) WHERE x IS NOT NULL] AS symptoms

OPTIONAL MATCH (profile_s)--(un:Unknown)
WITH
    effective_date,
    gender,
    education,
    profile_age,
    age_at_base_date,
    CASE
        WHEN age_at_base_date - $age_window < 0 THEN 0
        ELSE age_at_base_date - $age_window
    END AS min_age,
    age_at_base_date + $age_window AS max_age,
    diseases,
    symptoms,
    [x IN collect(DISTINCT un) WHERE x IS NOT NULL] AS unknowns

CALL (diseases, symptoms, unknowns, gender, education, min_age, max_age) {
    UNWIND diseases AS entity
    MATCH (entity)--(s:TaskInstanceSet)--(candidate_p:Patient)
    MATCH (s)--(i:TaskInstance)--(g:Game)
    WHERE
        candidate_p.`性别` = gender AND
        i.`任务类型` = "专属" AND
        (entity.id IS NOT NULL OR entity.name IS NOT NULL) AND
        s.`执行学历` = education AND
        s.`执行年龄` IS NOT NULL AND
        toInteger(toFloat(s.`执行年龄`)) >= min_age AND
        toInteger(toFloat(s.`执行年龄`)) <= max_age
    RETURN
        g,
        CASE
            WHEN entity.id IS NOT NULL THEN toString(entity.id)
            ELSE toString(entity.name)
        END AS support_source

    UNION ALL

    UNWIND symptoms AS entity
    MATCH (entity)--(s:TaskInstanceSet)--(candidate_p:Patient)
    MATCH (s)--(i:TaskInstance)--(g:Game)
    WHERE
        candidate_p.`性别` = gender AND
        i.`任务类型` = "专属" AND
        (entity.id IS NOT NULL OR entity.name IS NOT NULL) AND
        s.`执行学历` = education AND
        s.`执行年龄` IS NOT NULL AND
        toInteger(toFloat(s.`执行年龄`)) >= min_age AND
        toInteger(toFloat(s.`执行年龄`)) <= max_age
    RETURN
        g,
        CASE
            WHEN entity.id IS NOT NULL THEN toString(entity.id)
            ELSE toString(entity.name)
        END AS support_source

    UNION ALL

    UNWIND unknowns AS entity
    MATCH (entity)--(s:TaskInstanceSet)--(candidate_p:Patient)
    MATCH (s)--(i:TaskInstance)--(g:Game)
    WHERE
        candidate_p.`性别` = gender AND
        i.`任务类型` = "专属" AND
        (entity.id IS NOT NULL OR entity.name IS NOT NULL) AND
        s.`执行学历` = education AND
        s.`执行年龄` IS NOT NULL AND
        toInteger(toFloat(s.`执行年龄`)) >= min_age AND
        toInteger(toFloat(s.`执行年龄`)) <= max_age
    RETURN
        g,
        CASE
            WHEN entity.id IS NOT NULL THEN toString(entity.id)
            ELSE toString(entity.name)
        END AS support_source
}

RETURN
    g,
    profile_age,
    age_at_base_date,
    gender AS profile_gender,
    education AS profile_education,
    collect(DISTINCT support_source) AS support_sources,
    count(DISTINCT support_source) AS support_count

ORDER BY support_count DESC, toString(g.id) ASC
""".strip()

PATIENT_PROFILE_GENDER_EDUCATION_AGE_WINDOWED_EXCLUSIVE_TASK_GAME_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(profile_s:TaskInstanceSet)

WHERE
    p.`性别` IS NOT NULL AND
    profile_s.`训练日期` IS NOT NULL AND
    date(profile_s.`训练日期`) <= date($base_date)

WITH
    p,
    max(date(profile_s.`训练日期`)) AS effective_date

MATCH (p)
--(profile_s:TaskInstanceSet)

WHERE
    date(profile_s.`训练日期`) = effective_date AND
    profile_s.`执行学历` IS NOT NULL AND
    profile_s.`执行年龄` IS NOT NULL

WITH
    effective_date,
    profile_s,
    p.`性别` AS gender,
    profile_s.`执行学历` AS education,
    toInteger(toFloat(profile_s.`执行年龄`)) AS profile_age,
    duration.inDays(effective_date, date($base_date)).days AS age_delta_days

WITH
    effective_date,
    profile_s,
    gender,
    education,
    profile_age,
    profile_age + toInteger(floor(age_delta_days / 365.25)) AS age_at_base_date

OPTIONAL MATCH (profile_s)--(dis:Disease)
WITH
    effective_date,
    profile_s,
    gender,
    education,
    profile_age,
    age_at_base_date,
    [x IN collect(DISTINCT dis) WHERE x IS NOT NULL] AS diseases

OPTIONAL MATCH (profile_s)--(sym:Symptom)
WITH
    effective_date,
    profile_s,
    gender,
    education,
    profile_age,
    age_at_base_date,
    diseases,
    [x IN collect(DISTINCT sym) WHERE x IS NOT NULL] AS symptoms

OPTIONAL MATCH (profile_s)--(un:Unknown)
WITH
    effective_date,
    gender,
    education,
    profile_age,
    age_at_base_date,
    CASE
        WHEN age_at_base_date - $age_window < 0 THEN 0
        ELSE age_at_base_date - $age_window
    END AS min_age,
    age_at_base_date + $age_window AS max_age,
    CASE
        WHEN $profile_candidate_training_window_days IS NULL THEN NULL
        ELSE date($base_date) - duration({days: $profile_candidate_training_window_days})
    END AS min_training_date,
    CASE
        WHEN $profile_candidate_training_window_days IS NULL THEN NULL
        ELSE date($base_date)
    END AS max_training_date,
    diseases,
    symptoms,
    [x IN collect(DISTINCT un) WHERE x IS NOT NULL] AS unknowns

CALL (
    diseases,
    symptoms,
    unknowns,
    gender,
    education,
    min_age,
    max_age,
    min_training_date,
    max_training_date
) {
    UNWIND diseases AS entity
    MATCH (entity)--(s:TaskInstanceSet)--(candidate_p:Patient)
    MATCH (s)--(i:TaskInstance)--(g:Game)
    WHERE
        candidate_p.`性别` = gender AND
        toString(candidate_p.id) <> toString($patient_id) AND
        i.`任务类型` = "专属" AND
        (entity.id IS NOT NULL OR entity.name IS NOT NULL) AND
        s.`执行学历` = education AND
        s.`执行年龄` IS NOT NULL AND
        toInteger(toFloat(s.`执行年龄`)) >= min_age AND
        toInteger(toFloat(s.`执行年龄`)) <= max_age AND
        (
            min_training_date IS NULL OR
            (
                s.`训练日期` IS NOT NULL AND
                date(s.`训练日期`) >= min_training_date AND
                date(s.`训练日期`) <= max_training_date
            )
        )
    RETURN
        g,
        CASE
            WHEN entity.id IS NOT NULL THEN toString(entity.id)
            ELSE toString(entity.name)
        END AS support_source

    UNION ALL

    UNWIND symptoms AS entity
    MATCH (entity)--(s:TaskInstanceSet)--(candidate_p:Patient)
    MATCH (s)--(i:TaskInstance)--(g:Game)
    WHERE
        candidate_p.`性别` = gender AND
        toString(candidate_p.id) <> toString($patient_id) AND
        i.`任务类型` = "专属" AND
        (entity.id IS NOT NULL OR entity.name IS NOT NULL) AND
        s.`执行学历` = education AND
        s.`执行年龄` IS NOT NULL AND
        toInteger(toFloat(s.`执行年龄`)) >= min_age AND
        toInteger(toFloat(s.`执行年龄`)) <= max_age AND
        (
            min_training_date IS NULL OR
            (
                s.`训练日期` IS NOT NULL AND
                date(s.`训练日期`) >= min_training_date AND
                date(s.`训练日期`) <= max_training_date
            )
        )
    RETURN
        g,
        CASE
            WHEN entity.id IS NOT NULL THEN toString(entity.id)
            ELSE toString(entity.name)
        END AS support_source

    UNION ALL

    UNWIND unknowns AS entity
    MATCH (entity)--(s:TaskInstanceSet)--(candidate_p:Patient)
    MATCH (s)--(i:TaskInstance)--(g:Game)
    WHERE
        candidate_p.`性别` = gender AND
        toString(candidate_p.id) <> toString($patient_id) AND
        i.`任务类型` = "专属" AND
        (entity.id IS NOT NULL OR entity.name IS NOT NULL) AND
        s.`执行学历` = education AND
        s.`执行年龄` IS NOT NULL AND
        toInteger(toFloat(s.`执行年龄`)) >= min_age AND
        toInteger(toFloat(s.`执行年龄`)) <= max_age AND
        (
            min_training_date IS NULL OR
            (
                s.`训练日期` IS NOT NULL AND
                date(s.`训练日期`) >= min_training_date AND
                date(s.`训练日期`) <= max_training_date
            )
        )
    RETURN
        g,
        CASE
            WHEN entity.id IS NOT NULL THEN toString(entity.id)
            ELSE toString(entity.name)
        END AS support_source
}

RETURN
    g,
    profile_age,
    age_at_base_date,
    gender AS profile_gender,
    education AS profile_education,
    collect(DISTINCT support_source) AS support_sources,
    count(DISTINCT support_source) AS support_count

ORDER BY support_count DESC, toString(g.id) ASC
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
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT i1
""".strip()

PATIENT_DISTINCT_TASK_INSTANCES_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT i1
""".strip()

PATIENT_DISTINCT_SYMPTOMS_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT sym
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

PATIENT_DISTINCT_SYMPTOMS_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(sym:Symptom)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT sym
""".strip()

PATIENT_DISTINCT_DISEASES_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(dis:Disease)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT dis
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
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT dis
""".strip()

PATIENT_DISTINCT_UNKNOWNS_BY_END_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT un
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

PATIENT_DISTINCT_UNKNOWNS_BY_DATE_RANGE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(un:Unknown)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN DISTINCT un
""".strip()
