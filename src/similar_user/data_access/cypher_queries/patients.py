"""Cypher queries for patient node collections."""

PATIENT_IDS_QUERY = """
MATCH (p:Patient)
RETURN p.id AS patient_id
ORDER BY patient_id
""".strip()

PATIENT_IDS_WITH_TRAINING_ON_DATE_QUERY = """
MATCH (p:Patient)
--(s:TaskInstanceSet)
WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) = date($base_date)
RETURN DISTINCT p.id AS patient_id
ORDER BY patient_id
""".strip()
