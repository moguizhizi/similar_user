"""SQLite queries matching direct Neo4j source-taskset-patient path lookups."""

from __future__ import annotations

from dataclasses import dataclass

from .pattern_registry import QueryDateVariant, QueryDateWindow


DIRECT_PATH_RANDOMIZED_SQL_QUERY = """
WITH matched_paths AS (
    SELECT
        dp.source_type,
        dp.source_id,
        dp.taskset_id,
        dp.patient_id,
        dp.training_date,
        sn.source_json,
        ts.taskset_json,
        pn.patient_json
    FROM direct_paths dp
    JOIN source_nodes sn
      ON sn.source_type = dp.source_type
     AND sn.source_id = dp.source_id
    JOIN taskset_nodes ts
      ON ts.taskset_id = dp.taskset_id
    JOIN patient_nodes pn
      ON pn.patient_id = dp.patient_id
    WHERE dp.pattern = ?
      AND dp.source_type = ?
      AND dp.source_id = ?
),
randomized_paths AS (
    SELECT
        matched_paths.*,
        ROW_NUMBER() OVER (
            PARTITION BY matched_paths.patient_id
            ORDER BY RANDOM()
        ) AS patient_path_rank
    FROM matched_paths
)
SELECT source_json, taskset_json, patient_json
FROM randomized_paths
WHERE patient_path_rank = 1
ORDER BY training_date, taskset_id, patient_id
""".strip()


DIRECT_PATH_RANDOMIZED_SQL_BY_START_DATE_QUERY = """
WITH matched_paths AS (
    SELECT
        dp.source_type,
        dp.source_id,
        dp.taskset_id,
        dp.patient_id,
        dp.training_date,
        sn.source_json,
        ts.taskset_json,
        pn.patient_json
    FROM direct_paths dp
    JOIN source_nodes sn
      ON sn.source_type = dp.source_type
     AND sn.source_id = dp.source_id
    JOIN taskset_nodes ts
      ON ts.taskset_id = dp.taskset_id
    JOIN patient_nodes pn
      ON pn.patient_id = dp.patient_id
    WHERE dp.pattern = ?
      AND dp.source_type = ?
      AND dp.source_id = ?
      AND dp.training_date >= ?
),
randomized_paths AS (
    SELECT
        matched_paths.*,
        ROW_NUMBER() OVER (
            PARTITION BY matched_paths.patient_id
            ORDER BY RANDOM()
        ) AS patient_path_rank
    FROM matched_paths
)
SELECT source_json, taskset_json, patient_json
FROM randomized_paths
WHERE patient_path_rank = 1
ORDER BY training_date, taskset_id, patient_id
""".strip()


DIRECT_PATH_RANDOMIZED_SQL_BY_END_DATE_QUERY = """
WITH matched_paths AS (
    SELECT
        dp.source_type,
        dp.source_id,
        dp.taskset_id,
        dp.patient_id,
        dp.training_date,
        sn.source_json,
        ts.taskset_json,
        pn.patient_json
    FROM direct_paths dp
    JOIN source_nodes sn
      ON sn.source_type = dp.source_type
     AND sn.source_id = dp.source_id
    JOIN taskset_nodes ts
      ON ts.taskset_id = dp.taskset_id
    JOIN patient_nodes pn
      ON pn.patient_id = dp.patient_id
    WHERE dp.pattern = ?
      AND dp.source_type = ?
      AND dp.source_id = ?
      AND dp.training_date < ?
),
randomized_paths AS (
    SELECT
        matched_paths.*,
        ROW_NUMBER() OVER (
            PARTITION BY matched_paths.patient_id
            ORDER BY RANDOM()
        ) AS patient_path_rank
    FROM matched_paths
)
SELECT source_json, taskset_json, patient_json
FROM randomized_paths
WHERE patient_path_rank = 1
ORDER BY training_date, taskset_id, patient_id
""".strip()


DIRECT_PATH_RANDOMIZED_SQL_BY_DATE_RANGE_QUERY = """
WITH matched_paths AS (
    SELECT
        dp.source_type,
        dp.source_id,
        dp.taskset_id,
        dp.patient_id,
        dp.training_date,
        sn.source_json,
        ts.taskset_json,
        pn.patient_json
    FROM direct_paths dp
    JOIN source_nodes sn
      ON sn.source_type = dp.source_type
     AND sn.source_id = dp.source_id
    JOIN taskset_nodes ts
      ON ts.taskset_id = dp.taskset_id
    JOIN patient_nodes pn
      ON pn.patient_id = dp.patient_id
    WHERE dp.pattern = ?
      AND dp.source_type = ?
      AND dp.source_id = ?
      AND dp.training_date >= ?
      AND dp.training_date < ?
),
randomized_paths AS (
    SELECT
        matched_paths.*,
        ROW_NUMBER() OVER (
            PARTITION BY matched_paths.patient_id
            ORDER BY RANDOM()
        ) AS patient_path_rank
    FROM matched_paths
)
SELECT source_json, taskset_json, patient_json
FROM randomized_paths
WHERE patient_path_rank = 1
ORDER BY training_date, taskset_id, patient_id
""".strip()


DIRECT_PATH_ALL_SQL_QUERY = """
SELECT
    sn.source_json,
    ts.taskset_json,
    pn.patient_json
FROM direct_paths dp
JOIN source_nodes sn
  ON sn.source_type = dp.source_type
 AND sn.source_id = dp.source_id
JOIN taskset_nodes ts
  ON ts.taskset_id = dp.taskset_id
JOIN patient_nodes pn
  ON pn.patient_id = dp.patient_id
WHERE dp.pattern = ?
  AND dp.source_type = ?
  AND dp.source_id = ?
ORDER BY dp.training_date, dp.taskset_id, dp.patient_id
""".strip()


DIRECT_PATH_ALL_SQL_BY_START_DATE_QUERY = """
SELECT
    sn.source_json,
    ts.taskset_json,
    pn.patient_json
FROM direct_paths dp
JOIN source_nodes sn
  ON sn.source_type = dp.source_type
 AND sn.source_id = dp.source_id
JOIN taskset_nodes ts
  ON ts.taskset_id = dp.taskset_id
JOIN patient_nodes pn
  ON pn.patient_id = dp.patient_id
WHERE dp.pattern = ?
  AND dp.source_type = ?
  AND dp.source_id = ?
  AND dp.training_date >= ?
ORDER BY dp.training_date, dp.taskset_id, dp.patient_id
""".strip()


DIRECT_PATH_ALL_SQL_BY_END_DATE_QUERY = """
SELECT
    sn.source_json,
    ts.taskset_json,
    pn.patient_json
FROM direct_paths dp
JOIN source_nodes sn
  ON sn.source_type = dp.source_type
 AND sn.source_id = dp.source_id
JOIN taskset_nodes ts
  ON ts.taskset_id = dp.taskset_id
JOIN patient_nodes pn
  ON pn.patient_id = dp.patient_id
WHERE dp.pattern = ?
  AND dp.source_type = ?
  AND dp.source_id = ?
  AND dp.training_date < ?
ORDER BY dp.training_date, dp.taskset_id, dp.patient_id
""".strip()


DIRECT_PATH_ALL_SQL_BY_DATE_RANGE_QUERY = """
SELECT
    sn.source_json,
    ts.taskset_json,
    pn.patient_json
FROM direct_paths dp
JOIN source_nodes sn
  ON sn.source_type = dp.source_type
 AND sn.source_id = dp.source_id
JOIN taskset_nodes ts
  ON ts.taskset_id = dp.taskset_id
JOIN patient_nodes pn
  ON pn.patient_id = dp.patient_id
WHERE dp.pattern = ?
  AND dp.source_type = ?
  AND dp.source_id = ?
  AND dp.training_date >= ?
  AND dp.training_date < ?
ORDER BY dp.training_date, dp.taskset_id, dp.patient_id
""".strip()


@dataclass(frozen=True)
class DirectPathSqlVariants:
    """Date-bound SQLite variants for one direct path query purpose."""

    base: str
    by_start_date: str
    by_end_date: str
    by_date_range: str

    def select(self, window: QueryDateWindow) -> str:
        """Select the static SQL query matching the supplied date window."""
        if window.variant == QueryDateVariant.DATE_RANGE:
            return self.by_date_range
        if window.variant == QueryDateVariant.START_DATE:
            return self.by_start_date
        if window.variant == QueryDateVariant.END_DATE:
            return self.by_end_date
        return self.base


DIRECT_PATH_RANDOMIZED_SQL_VARIANTS = DirectPathSqlVariants(
    base=DIRECT_PATH_RANDOMIZED_SQL_QUERY,
    by_start_date=DIRECT_PATH_RANDOMIZED_SQL_BY_START_DATE_QUERY,
    by_end_date=DIRECT_PATH_RANDOMIZED_SQL_BY_END_DATE_QUERY,
    by_date_range=DIRECT_PATH_RANDOMIZED_SQL_BY_DATE_RANGE_QUERY,
)


DIRECT_PATH_ALL_SQL_VARIANTS = DirectPathSqlVariants(
    base=DIRECT_PATH_ALL_SQL_QUERY,
    by_start_date=DIRECT_PATH_ALL_SQL_BY_START_DATE_QUERY,
    by_end_date=DIRECT_PATH_ALL_SQL_BY_END_DATE_QUERY,
    by_date_range=DIRECT_PATH_ALL_SQL_BY_DATE_RANGE_QUERY,
)


def direct_path_sql_parameters(
    *,
    pattern: str,
    source_type: str,
    source_id: str,
    window: QueryDateWindow,
) -> list[object]:
    """Build positional SQLite parameters in the same order as query variants."""
    parameters: list[object] = [pattern, source_type, source_id]
    if window.start_date is not None:
        parameters.append(window.start_date)
    if window.end_date is not None:
        parameters.append(window.end_date)
    return parameters
