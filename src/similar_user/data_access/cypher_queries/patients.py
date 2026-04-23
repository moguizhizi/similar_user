"""Cypher queries for patient node collections."""

PATIENT_IDS_QUERY = """
MATCH (p:Patient)
RETURN p.id AS patient_id
ORDER BY patient_id
""".strip()
