"""Cypher queries for resolving user-entered entity names."""

DIRECT_ENTITY_NAME_RESOLUTION_QUERY = """
MATCH (d:Disease)
WITH d, properties(d)["别名"] AS alias_prop
WITH d, [d.name] + CASE
    WHEN alias_prop IS NULL THEN []
    ELSE split(toString(alias_prop), ",")
END AS names
WHERE any(name IN names WHERE name IS NOT NULL AND trim(toString(name)) = $entity_name)
RETURN
    "disease" AS entity_type,
    d.id AS entity_id,
    d.name AS entity_name

UNION

MATCH (sym:Symptom)
WITH sym, properties(sym)["别名"] AS alias_prop
WITH sym, [sym.name] + CASE
    WHEN alias_prop IS NULL THEN []
    ELSE split(toString(alias_prop), ",")
END AS names
WHERE any(name IN names WHERE name IS NOT NULL AND trim(toString(name)) = $entity_name)
RETURN
    "symptom" AS entity_type,
    sym.id AS entity_id,
    sym.name AS entity_name

UNION

MATCH (un:Unknown)
WITH un, properties(un)["别名"] AS alias_prop
WITH un, [un.name] + CASE
    WHEN alias_prop IS NULL THEN []
    ELSE split(toString(alias_prop), ",")
END AS names
WHERE any(name IN names WHERE name IS NOT NULL AND trim(toString(name)) = $entity_name)
RETURN
    "unknown" AS entity_type,
    un.id AS entity_id,
    un.name AS entity_name

ORDER BY entity_type, entity_id
""".strip()

DIRECT_ENTITY_ALIAS_INDEX_QUERY = """
MATCH (d:Disease)
WITH "disease" AS entity_type, d.id AS entity_id, d.name AS entity_name, properties(d)["别名"] AS alias_prop
WITH entity_type, entity_id, entity_name, [entity_name] + CASE
    WHEN alias_prop IS NULL THEN []
    ELSE split(toString(alias_prop), ",")
END AS names
UNWIND names AS alias_label
WITH entity_type, entity_id, entity_name, trim(toString(alias_label)) AS alias_label
WHERE alias_label <> ""
RETURN entity_type, entity_id, entity_name, alias_label

UNION

MATCH (sym:Symptom)
WITH "symptom" AS entity_type, sym.id AS entity_id, sym.name AS entity_name, properties(sym)["别名"] AS alias_prop
WITH entity_type, entity_id, entity_name, [entity_name] + CASE
    WHEN alias_prop IS NULL THEN []
    ELSE split(toString(alias_prop), ",")
END AS names
UNWIND names AS alias_label
WITH entity_type, entity_id, entity_name, trim(toString(alias_label)) AS alias_label
WHERE alias_label <> ""
RETURN entity_type, entity_id, entity_name, alias_label

UNION

MATCH (un:Unknown)
WITH "unknown" AS entity_type, un.id AS entity_id, un.name AS entity_name, properties(un)["别名"] AS alias_prop
WITH entity_type, entity_id, entity_name, [entity_name] + CASE
    WHEN alias_prop IS NULL THEN []
    ELSE split(toString(alias_prop), ",")
END AS names
UNWIND names AS alias_label
WITH entity_type, entity_id, entity_name, trim(toString(alias_label)) AS alias_label
WHERE alias_label <> ""
RETURN entity_type, entity_id, entity_name, alias_label

ORDER BY entity_type, entity_id, alias_label
""".strip()
