"""Benchmark patient_game_patient path query variants.

This script is intentionally separate from the production pipeline. It runs a
small set of Cypher variants for one patient/date window and records elapsed
time, returned row count, and errors so query changes can be compared in Neo4j.
"""

from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from similar_user.data_access.cypher_queries import (
    PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY,
    PATIENT_PROFILE_GENDER_EDUCATION_AGE_WINDOWED_EXCLUSIVE_TASK_GAME_QUERY,
)
from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.utils.logger import get_logger


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
DEFAULT_OUTPUT_DIR = Path("logs/path_query_benchmarks")
DEFAULT_PATIENT_ID = "30050783"
DEFAULT_START_DATE = "2026-05-11"
DEFAULT_END_DATE = "2026-05-25"
DEFAULT_PER_G = 10
DEFAULT_LIMIT = 310
DEFAULT_TIMEOUT_SECONDS = 900
DEFAULT_BASE_DATE = "2026-05-25"
DEFAULT_AGE_WINDOW = 0
DEFAULT_PROFILE_CANDIDATE_TRAINING_WINDOW_DAYS = 80
LOGGER = get_logger(__name__)


def _require_taskset_total_score(query: str) -> str:
    """Require source and candidate TaskInstanceSet total scores in a query."""
    return (
        query.replace(
            "    s1.`训练日期` IS NOT NULL AND\n"
            "    s2.`训练日期` IS NOT NULL AND",
            "    s1.`训练日期` IS NOT NULL AND\n"
            "    s2.`训练日期` IS NOT NULL AND\n"
            "    s1.`总分` IS NOT NULL AND\n"
            "    s2.`总分` IS NOT NULL AND",
        )
        .replace(
            "        s1.`训练日期` IS NOT NULL AND\n"
            "        s2.`训练日期` IS NOT NULL AND",
            "        s1.`训练日期` IS NOT NULL AND\n"
            "        s2.`训练日期` IS NOT NULL AND\n"
            "        s1.`总分` IS NOT NULL AND\n"
            "        s2.`总分` IS NOT NULL AND",
        )
        .replace(
            "    s1.`训练日期` IS NOT NULL AND\n"
            "    date(s1.`训练日期`)",
            "    s1.`训练日期` IS NOT NULL AND\n"
            "    s1.`总分` IS NOT NULL AND\n"
            "    date(s1.`训练日期`)",
        )
        .replace(
            "        s1.`训练日期` IS NOT NULL AND\n"
            "        date(s1.`训练日期`)",
            "        s1.`训练日期` IS NOT NULL AND\n"
            "        s1.`总分` IS NOT NULL AND\n"
            "        date(s1.`训练日期`)",
        )
    )


def _require_candidate_taskset_date_window(query: str) -> str:
    """Require candidate TaskInstanceSet training dates in the date-range window."""
    return (
        query.replace(
            "    s2.`总分` IS NOT NULL AND\n"
            "    date(s1.`训练日期`) >= date(s2.`训练日期`) AND\n"
            "    date(s1.`训练日期`) >= date($start_date) AND\n"
            "    date(s1.`训练日期`) < date($end_date)",
            "    s2.`总分` IS NOT NULL AND\n"
            "    date(s1.`训练日期`) >= date(s2.`训练日期`) AND\n"
            "    date(s1.`训练日期`) >= date($start_date) AND\n"
            "    date(s1.`训练日期`) < date($end_date) AND\n"
            "    date(s2.`训练日期`) >= date($start_date) AND\n"
            "    date(s2.`训练日期`) < date($end_date)",
        )
        .replace(
            "        s2.`总分` IS NOT NULL AND\n"
            "        date(s1.`训练日期`) >= date(s2.`训练日期`) AND\n"
            "        date(s1.`训练日期`) >= date($start_date) AND\n"
            "        date(s1.`训练日期`) < date($end_date)",
            "        s2.`总分` IS NOT NULL AND\n"
            "        date(s1.`训练日期`) >= date(s2.`训练日期`) AND\n"
            "        date(s1.`训练日期`) >= date($start_date) AND\n"
            "        date(s1.`训练日期`) < date($end_date) AND\n"
            "        date(s2.`训练日期`) >= date($start_date) AND\n"
            "        date(s2.`训练日期`) < date($end_date)",
        )
    )


def _require_task_game_training_order_conditions(
    query: str,
    conditions: tuple[str, ...],
) -> str:
    """Add source/candidate TaskInstanceSet conditions to a task-game path query."""
    if not conditions:
        return query
    anchor = "    date(s1.`训练日期`) < date($end_date)"
    replacement = anchor + " AND\n" + " AND\n".join(
        f"    {condition}" for condition in conditions
    )
    return query.replace(anchor, replacement, 1)


ORIGINAL_QUERY = """
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


LOCAL_SAMPLING_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

WITH DISTINCT p, g

CALL {
    WITH p, g

    MATCH (p)
    --(s1:TaskInstanceSet)
    --(i1:TaskInstance)
    --(g)
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

    WITH p, s1, i1, g, i2, s2, p2, rand() AS r
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

    WITH row, rand() AS r
    ORDER BY r
    LIMIT $per_g

    RETURN collect(row) AS rows
}

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()


AGE_ONLY_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

WITH DISTINCT p, g

CALL {
    WITH p, g

    MATCH (p)
    --(s1:TaskInstanceSet)
    --(i1:TaskInstance)
    --(g)
    --(i2:TaskInstance)
    --(s2:TaskInstanceSet)
    --(p2:Patient)

    WHERE
        p <> p2 AND
        s1.`训练日期` IS NOT NULL AND
        s2.`训练日期` IS NOT NULL AND
        date(s1.`训练日期`) >= date(s2.`训练日期`) AND
        date(s1.`训练日期`) >= date($start_date) AND
        date(s1.`训练日期`) < date($end_date) AND
        s1.`执行年龄` IS NOT NULL AND
        s2.`执行年龄` IS NOT NULL AND
        abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5

    WITH p, s1, i1, g, i2, s2, p2, rand() AS r
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

    WITH row, rand() AS r
    ORDER BY r
    LIMIT $per_g

    RETURN collect(row) AS rows
}

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()


LAYER1_AGE_COMPLETION_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

WITH DISTINCT p, g

CALL {
    WITH p, g

    MATCH (p)
    --(s1:TaskInstanceSet)
    --(i1:TaskInstance)
    --(g)
    --(i2:TaskInstance)
    --(s2:TaskInstanceSet)
    --(p2:Patient)

    WHERE
        p <> p2 AND
        s1.`训练日期` IS NOT NULL AND
        s2.`训练日期` IS NOT NULL AND
        date(s1.`训练日期`) >= date(s2.`训练日期`) AND
        date(s1.`训练日期`) >= date($start_date) AND
        date(s1.`训练日期`) < date($end_date) AND
        s1.`执行年龄` IS NOT NULL AND
        s2.`执行年龄` IS NOT NULL AND
        abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5 AND
        i1.`结果` = "完成" AND
        i2.`结果` = "完成"

    WITH p, s1, i1, g, i2, s2, p2, rand() AS r
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

    WITH row, rand() AS r
    ORDER BY r
    LIMIT $per_g

    RETURN collect(row) AS rows
}

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()


LAYER2_EDUCATION_EXACT_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

WITH DISTINCT p, g

CALL {
    WITH p, g

    MATCH (p)
    --(s1:TaskInstanceSet)
    --(i1:TaskInstance)
    --(g)
    --(i2:TaskInstance)
    --(s2:TaskInstanceSet)
    --(p2:Patient)

    WHERE
        p <> p2 AND
        s1.`训练日期` IS NOT NULL AND
        s2.`训练日期` IS NOT NULL AND
        date(s1.`训练日期`) >= date(s2.`训练日期`) AND
        date(s1.`训练日期`) >= date($start_date) AND
        date(s1.`训练日期`) < date($end_date) AND
        s1.`执行年龄` IS NOT NULL AND
        s2.`执行年龄` IS NOT NULL AND
        abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5 AND
        s1.`执行学历` IS NOT NULL AND
        s2.`执行学历` IS NOT NULL AND
        s1.`执行学历` = s2.`执行学历` AND
        i1.`结果` = "完成" AND
        i2.`结果` = "完成"

    WITH p, s1, i1, g, i2, s2, p2, rand() AS r
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

    WITH row, rand() AS r
    ORDER BY r
    LIMIT $per_g

    RETURN collect(row) AS rows
}

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()


LAYER3_ACTIVITY_TASK_TYPE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

WITH DISTINCT p, g

CALL {
    WITH p, g

    MATCH (p)
    --(s1:TaskInstanceSet)
    --(i1:TaskInstance)
    --(g)
    --(i2:TaskInstance)
    --(s2:TaskInstanceSet)
    --(p2:Patient)

    WHERE
        p <> p2 AND
        s1.`训练日期` IS NOT NULL AND
        s2.`训练日期` IS NOT NULL AND
        date(s1.`训练日期`) >= date(s2.`训练日期`) AND
        date(s1.`训练日期`) >= date($start_date) AND
        date(s1.`训练日期`) < date($end_date) AND
        s1.`执行年龄` IS NOT NULL AND
        s2.`执行年龄` IS NOT NULL AND
        abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5 AND
        s1.`执行学历` IS NOT NULL AND
        s2.`执行学历` IS NOT NULL AND
        s1.`执行学历` = s2.`执行学历` AND
        i1.`结果` = "完成" AND
        i2.`结果` = "完成" AND
        i1.`活跃` = "是" AND
        i2.`活跃` = "是" AND
        i1.`任务类型` = i2.`任务类型`

    WITH p, s1, i1, g, i2, s2, p2, rand() AS r
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

    WITH row, rand() AS r
    ORDER BY r
    LIMIT $per_g

    RETURN collect(row) AS rows
}

UNWIND rows AS row

RETURN row
LIMIT $limit
""".strip()

LOCAL_SAMPLING_QUERY = ORIGINAL_QUERY
AGE_ONLY_QUERY = _require_task_game_training_order_conditions(
    ORIGINAL_QUERY,
    (
        "s1.`执行年龄` IS NOT NULL",
        "s2.`执行年龄` IS NOT NULL",
        "abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5",
    ),
)
AGE_EDU_QUERY = _require_task_game_training_order_conditions(
    ORIGINAL_QUERY,
    (
        "s1.`执行年龄` IS NOT NULL",
        "s2.`执行年龄` IS NOT NULL",
        "abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5",
        "s1.`执行学历` IS NOT NULL",
        "s2.`执行学历` IS NOT NULL",
        "s1.`执行学历` = s2.`执行学历`",
    ),
)
AGE_I1_COMPLETION_QUERY = _require_task_game_training_order_conditions(
    ORIGINAL_QUERY,
    (
        "s1.`执行年龄` IS NOT NULL",
        "s2.`执行年龄` IS NOT NULL",
        "abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5",
        'i1.`结果` = "完成"',
    ),
)
AGE_I2_COMPLETION_QUERY = _require_task_game_training_order_conditions(
    ORIGINAL_QUERY,
    (
        "s1.`执行年龄` IS NOT NULL",
        "s2.`执行年龄` IS NOT NULL",
        "abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5",
        'i2.`结果` = "完成"',
    ),
)
LAYER1_AGE_COMPLETION_QUERY = _require_task_game_training_order_conditions(
    ORIGINAL_QUERY,
    (
        "s1.`执行年龄` IS NOT NULL",
        "s2.`执行年龄` IS NOT NULL",
        "abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5",
        'i1.`结果` = "完成"',
        'i2.`结果` = "完成"',
    ),
)
LAYER2_EDUCATION_EXACT_QUERY = _require_task_game_training_order_conditions(
    ORIGINAL_QUERY,
    (
        "s1.`执行年龄` IS NOT NULL",
        "s2.`执行年龄` IS NOT NULL",
        "abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5",
        "s1.`执行学历` IS NOT NULL",
        "s2.`执行学历` IS NOT NULL",
        "s1.`执行学历` = s2.`执行学历`",
        'i1.`结果` = "完成"',
        'i2.`结果` = "完成"',
    ),
)
LAYER3_ACTIVITY_TASK_TYPE_QUERY = _require_task_game_training_order_conditions(
    ORIGINAL_QUERY,
    (
        "s1.`执行年龄` IS NOT NULL",
        "s2.`执行年龄` IS NOT NULL",
        "abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5",
        "s1.`执行学历` IS NOT NULL",
        "s2.`执行学历` IS NOT NULL",
        "s1.`执行学历` = s2.`执行学历`",
        'i1.`结果` = "完成"',
        'i2.`结果` = "完成"',
        'i1.`活跃` = "是"',
        'i2.`活跃` = "是"',
        "i1.`任务类型` = i2.`任务类型`",
    ),
)

LAYER1_AGE_COMPLETION_TWO_STAGE_DUAL_WINDOW_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    s1.`总分` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date) AND
    s1.`执行年龄` IS NOT NULL AND
    i1.`结果` = "完成"

WITH p, s1, i1, g

MATCH (g)
--(i2:TaskInstance)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s2.`训练日期` IS NOT NULL AND
    s2.`总分` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s2.`训练日期`) >= date($start_date) AND
    date(s2.`训练日期`) < date($end_date) AND
    s2.`执行年龄` IS NOT NULL AND
    abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5 AND
    i2.`结果` = "完成"

WITH p, s1, i1, g, i2, s2, p2, rand() AS r
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

AGE_EDU_TWO_STAGE_DUAL_WINDOW_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    s1.`总分` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date) AND
    s1.`执行年龄` IS NOT NULL AND
    s1.`执行学历` IS NOT NULL

WITH p, s1, i1, g

MATCH (g)
--(i2:TaskInstance)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s2.`训练日期` IS NOT NULL AND
    s2.`总分` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`) AND
    date(s2.`训练日期`) >= date($start_date) AND
    date(s2.`训练日期`) < date($end_date) AND
    s2.`执行年龄` IS NOT NULL AND
    s2.`执行学历` IS NOT NULL AND
    abs(toInteger(s2.`执行年龄`) - toInteger(s1.`执行年龄`)) <= 5 AND
    s1.`执行学历` = s2.`执行学历`

WITH g, p, s1, i1, i2, s2, p2
ORDER BY id(g), id(p2), date(s2.`训练日期`) DESC, id(s2), id(i2)

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

ORIGINAL_QUERY = _require_taskset_total_score(ORIGINAL_QUERY)
LOCAL_SAMPLING_QUERY = _require_taskset_total_score(LOCAL_SAMPLING_QUERY)
AGE_ONLY_QUERY = _require_taskset_total_score(AGE_ONLY_QUERY)
AGE_EDU_QUERY = _require_taskset_total_score(AGE_EDU_QUERY)
AGE_I1_COMPLETION_QUERY = _require_taskset_total_score(AGE_I1_COMPLETION_QUERY)
AGE_I2_COMPLETION_QUERY = _require_taskset_total_score(AGE_I2_COMPLETION_QUERY)
LAYER1_AGE_COMPLETION_QUERY = _require_taskset_total_score(
    LAYER1_AGE_COMPLETION_QUERY
)
LAYER2_EDUCATION_EXACT_QUERY = _require_taskset_total_score(
    LAYER2_EDUCATION_EXACT_QUERY
)
LAYER3_ACTIVITY_TASK_TYPE_QUERY = _require_taskset_total_score(
    LAYER3_ACTIVITY_TASK_TYPE_QUERY
)
ORIGINAL_DUAL_WINDOW_QUERY = _require_candidate_taskset_date_window(ORIGINAL_QUERY)
LOCAL_SAMPLING_DUAL_WINDOW_QUERY = _require_candidate_taskset_date_window(
    LOCAL_SAMPLING_QUERY
)
AGE_ONLY_DUAL_WINDOW_QUERY = _require_candidate_taskset_date_window(AGE_ONLY_QUERY)
AGE_EDU_DUAL_WINDOW_QUERY = _require_candidate_taskset_date_window(AGE_EDU_QUERY)
AGE_I1_COMPLETION_DUAL_WINDOW_QUERY = _require_candidate_taskset_date_window(
    AGE_I1_COMPLETION_QUERY
)
AGE_I2_COMPLETION_DUAL_WINDOW_QUERY = _require_candidate_taskset_date_window(
    AGE_I2_COMPLETION_QUERY
)
LAYER1_AGE_COMPLETION_DUAL_WINDOW_QUERY = _require_candidate_taskset_date_window(
    LAYER1_AGE_COMPLETION_QUERY
)
LAYER2_EDUCATION_EXACT_DUAL_WINDOW_QUERY = _require_candidate_taskset_date_window(
    LAYER2_EDUCATION_EXACT_QUERY
)
LAYER3_ACTIVITY_TASK_TYPE_DUAL_WINDOW_QUERY = _require_candidate_taskset_date_window(
    LAYER3_ACTIVITY_TASK_TYPE_QUERY
)


PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BATCH_BY_DATE_WINDOW_QUERY = """
MATCH (p:Patient)
WHERE toString(p.id) IN $patient_ids

MATCH (p)
--(s:TaskInstanceSet)
--(i:TaskInstance)
--(g:Game)

WHERE
    s.`训练日期` IS NOT NULL AND
    date(s.`训练日期`) >= date($start_date) AND
    date(s.`训练日期`) < date($end_date) AND
    i.`任务类型` = "专属"

WITH
    toString(p.id) AS patient_id,
    date(s.`训练日期`) AS trainingDate,
    g
ORDER BY patient_id, trainingDate

RETURN
    patient_id,
    trainingDate,
    g
""".strip()


QUERY_VARIANTS = {
    "patient_exclusive_training_task_history_batch_by_date_window": (
        PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BATCH_BY_DATE_WINDOW_QUERY
    ),
    "patient_exclusive_training_task_history_by_date_window": (
        PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY
    ),
    "patient_profile_gender_education_age_windowed_exclusive_task_game": (
        PATIENT_PROFILE_GENDER_EDUCATION_AGE_WINDOWED_EXCLUSIVE_TASK_GAME_QUERY
    ),
    "training_order_source_window": ORIGINAL_QUERY,
    "training_order_local_sampling_source_window": LOCAL_SAMPLING_QUERY,
    "training_order_age_source_window": AGE_ONLY_QUERY,
    "training_order_age_edu_source_window": AGE_EDU_QUERY,
    "training_order_age_completed_source_window": LAYER1_AGE_COMPLETION_QUERY,
    "training_order_age_edu_completed_source_window": LAYER2_EDUCATION_EXACT_QUERY,
    "training_order_age_edu_task_completed_source_window": LAYER3_ACTIVITY_TASK_TYPE_QUERY,
    "training_order_dual_window": ORIGINAL_DUAL_WINDOW_QUERY,
    "training_order_local_sampling_dual_window": LOCAL_SAMPLING_DUAL_WINDOW_QUERY,
    "training_order_age_dual_window": AGE_ONLY_DUAL_WINDOW_QUERY,
    "training_order_age_edu_dual_window": AGE_EDU_DUAL_WINDOW_QUERY,
    "training_order_age_edu_two_stage_dual_window": AGE_EDU_TWO_STAGE_DUAL_WINDOW_QUERY,
    "training_order_age_i1_completion_dual_window": AGE_I1_COMPLETION_DUAL_WINDOW_QUERY,
    "training_order_age_i2_completion_dual_window": AGE_I2_COMPLETION_DUAL_WINDOW_QUERY,
    "training_order_age_completed_dual_window": LAYER1_AGE_COMPLETION_DUAL_WINDOW_QUERY,
    "training_order_age_completed_two_stage_dual_window": LAYER1_AGE_COMPLETION_TWO_STAGE_DUAL_WINDOW_QUERY,
    "training_order_age_edu_completed_dual_window": LAYER2_EDUCATION_EXACT_DUAL_WINDOW_QUERY,
    "training_order_age_edu_task_completed_dual_window": LAYER3_ACTIVITY_TASK_TYPE_DUAL_WINDOW_QUERY,
}


ORIGINAL_STATISTICS_QUERY = """
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

RETURN
    count(*) AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()


APPROX_STATISTICS_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

WITH DISTINCT p, s1, g

MATCH (g)
--(i2:TaskInstance)
--(s2:TaskInstanceSet)
--(p2:Patient)

WHERE
    p <> p2 AND
    s2.`训练日期` IS NOT NULL AND
    date(s1.`训练日期`) >= date(s2.`训练日期`)

RETURN
    null AS totalPaths,
    count(DISTINCT g) AS gCount,
    count(DISTINCT p2) AS p2Count
""".strip()

GCOUNT_ONLY_STATISTICS_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(s1:TaskInstanceSet)
--(i1:TaskInstance)
--(g:Game)

WHERE
    s1.`训练日期` IS NOT NULL AND
    s1.`总分` IS NOT NULL AND
    date(s1.`训练日期`) >= date($start_date) AND
    date(s1.`训练日期`) < date($end_date)

RETURN
    null AS totalPaths,
    count(DISTINCT g) AS gCount,
    null AS p2Count
""".strip()

ORIGINAL_STATISTICS_QUERY = _require_taskset_total_score(ORIGINAL_STATISTICS_QUERY)
APPROX_STATISTICS_QUERY = _require_taskset_total_score(APPROX_STATISTICS_QUERY)
ORIGINAL_DUAL_WINDOW_STATISTICS_QUERY = _require_candidate_taskset_date_window(
    ORIGINAL_STATISTICS_QUERY
)
APPROX_DUAL_WINDOW_STATISTICS_QUERY = _require_candidate_taskset_date_window(
    APPROX_STATISTICS_QUERY
)
GCOUNT_ONLY_DUAL_WINDOW_STATISTICS_QUERY = GCOUNT_ONLY_STATISTICS_QUERY

PATIENT_PROFILE_EFFECTIVE_DATE_QUERY = """
MATCH (p:Patient {id: $patient_id})
--(profile_s:TaskInstanceSet)

WHERE
    p.`性别` IS NOT NULL AND
    profile_s.`训练日期` IS NOT NULL AND
    date(profile_s.`训练日期`) <= date($base_date)

WITH
    p,
    max(date(profile_s.`训练日期`)) AS effective_date

RETURN
    effective_date
""".strip()


STATISTICS_VARIANTS = {
    "patient_profile_effective_date": PATIENT_PROFILE_EFFECTIVE_DATE_QUERY,
    "stats_training_order_source_window": ORIGINAL_STATISTICS_QUERY,
    "stats_training_order_approx_group_source_window": APPROX_STATISTICS_QUERY,
    "stats_training_order_gcount_only_source_window": GCOUNT_ONLY_STATISTICS_QUERY,
    "stats_training_order_dual_window": ORIGINAL_DUAL_WINDOW_STATISTICS_QUERY,
    "stats_training_order_approx_group_dual_window": APPROX_DUAL_WINDOW_STATISTICS_QUERY,
    "stats_training_order_gcount_only_dual_window": GCOUNT_ONLY_DUAL_WINDOW_STATISTICS_QUERY,
}

ALL_VARIANTS = {**QUERY_VARIANTS, **STATISTICS_VARIANTS}
COMPARE_VARIANTS = {
    "compare_patient_exclusive_training_task_history_batch_by_date_window"
}


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Benchmark patient_game_patient path query variants."
    )
    parser.add_argument("--config", default=str(DEFAULT_CONFIG_PATH))
    parser.add_argument(
        "--patient-id",
        action="append",
        help=(
            "Patient id to benchmark. Can be passed multiple times. "
            f"Defaults to {DEFAULT_PATIENT_ID} when neither --patient-id nor "
            "--patient-id-file is provided."
        ),
    )
    parser.add_argument(
        "--patient-id-file",
        help="Text file containing one patient id per line. Empty lines and # comments are ignored.",
    )
    parser.add_argument(
        "--candidate-patient-id",
        action="append",
        help=(
            "Candidate patient id for batch candidate-history benchmarks. "
            "Can be passed multiple times. Defaults to --patient-id values."
        ),
    )
    parser.add_argument(
        "--candidate-patient-id-file",
        help="Text file containing candidate patient ids for batch candidate-history benchmarks.",
    )
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--base-date", default=DEFAULT_BASE_DATE)
    parser.add_argument("--age-window", type=int, default=DEFAULT_AGE_WINDOW)
    parser.add_argument(
        "--profile-candidate-training-window-days",
        type=int,
        default=DEFAULT_PROFILE_CANDIDATE_TRAINING_WINDOW_DAYS,
    )
    parser.add_argument("--per-g", type=int, default=DEFAULT_PER_G)
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Terminate one query variant after this many seconds.",
    )
    parser.add_argument(
        "--variant",
        action="append",
        choices=sorted([*ALL_VARIANTS, *COMPARE_VARIANTS]),
        help="Run one variant. Can be passed multiple times. Defaults to all variants.",
    )
    parser.add_argument(
        "--list-variants",
        action="store_true",
        help="Print available variants and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print selected Cypher queries without executing them.",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Directory for JSON benchmark output.",
    )
    return parser.parse_args()


def read_patient_ids(args: argparse.Namespace) -> list[str]:
    """Read patient ids from CLI arguments and an optional file."""
    patient_ids: list[str] = []
    if args.patient_id:
        patient_ids.extend(str(patient_id).strip() for patient_id in args.patient_id)

    if args.patient_id_file:
        path = Path(args.patient_id_file)
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    patient_ids.append(stripped)

    normalized = []
    seen = set()
    for patient_id in patient_ids or [DEFAULT_PATIENT_ID]:
        if patient_id and patient_id not in seen:
            normalized.append(patient_id)
            seen.add(patient_id)
    return normalized


def read_candidate_patient_ids(
    args: argparse.Namespace,
    *,
    fallback_patient_ids: list[str],
) -> list[str]:
    """Read candidate patient ids for batch history benchmarks."""
    candidate_patient_ids: list[str] = []
    if args.candidate_patient_id:
        candidate_patient_ids.extend(
            str(patient_id).strip() for patient_id in args.candidate_patient_id
        )

    if args.candidate_patient_id_file:
        path = Path(args.candidate_patient_id_file)
        with path.open("r", encoding="utf-8") as file:
            for line in file:
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    candidate_patient_ids.append(stripped)

    normalized = []
    seen = set()
    for patient_id in candidate_patient_ids or fallback_patient_ids:
        if patient_id and patient_id not in seen:
            normalized.append(patient_id)
            seen.add(patient_id)
    return normalized


def build_parameters(args: argparse.Namespace, patient_id: str) -> dict[str, object]:
    """Build Cypher parameters from parsed arguments."""
    return {
        "patient_id": str(patient_id),
        "start_date": str(args.start_date),
        "end_date": str(args.end_date),
        "per_g": int(args.per_g),
        "limit": int(args.limit),
        "base_date": str(args.base_date),
        "age_window": int(args.age_window),
        "profile_candidate_training_window_days": int(
            args.profile_candidate_training_window_days
        ),
    }


def build_batch_history_parameters(
    args: argparse.Namespace,
    candidate_patient_ids: list[str],
) -> dict[str, object]:
    """Build parameters for batch candidate-history benchmarks."""
    return {
        "patient_ids": [str(patient_id) for patient_id in candidate_patient_ids],
        "start_date": str(args.start_date),
        "end_date": str(args.end_date),
    }


def run_query_worker(
    config_path: str,
    variant: str,
    query: str,
    parameters: dict[str, object],
    queue: mp.Queue,
) -> None:
    """Run one query variant in a child process."""
    started_at = time.perf_counter()
    try:
        with Neo4jClient.from_config(config_path) as client:
            rows = client.run_query(query=query, parameters=parameters)
        elapsed_seconds = round(time.perf_counter() - started_at, 3)
        queue.put(
            {
                "variant": variant,
                "status": "completed",
                "row_count": len(rows),
                "elapsed_seconds": elapsed_seconds,
                "error": None,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive for external DB errors.
        elapsed_seconds = round(time.perf_counter() - started_at, 3)
        queue.put(
            {
                "variant": variant,
                "status": "failed",
                "row_count": None,
                "elapsed_seconds": elapsed_seconds,
                "error": str(exc),
            }
        )


def run_candidate_history_compare_worker(
    config_path: str,
    candidate_patient_ids: list[str],
    start_date: str,
    end_date: str,
    queue: mp.Queue,
) -> None:
    """Compare per-patient and batch candidate-history queries in one worker."""
    started_at = time.perf_counter()
    try:
        per_patient_results: list[dict[str, object]] = []
        individual_row_count = 0
        individual_started_at = time.perf_counter()
        with Neo4jClient.from_config(config_path) as client:
            for patient_id in candidate_patient_ids:
                patient_started_at = time.perf_counter()
                rows = client.run_query(
                    query=PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY,
                    parameters={
                        "patient_id": str(patient_id),
                        "start_date": str(start_date),
                        "end_date": str(end_date),
                    },
                )
                patient_elapsed_seconds = round(
                    time.perf_counter() - patient_started_at,
                    3,
                )
                individual_row_count += len(rows)
                per_patient_results.append(
                    {
                        "patient_id": str(patient_id),
                        "row_count": len(rows),
                        "elapsed_seconds": patient_elapsed_seconds,
                    }
                )
            individual_elapsed_seconds = round(
                time.perf_counter() - individual_started_at,
                3,
            )

            batch_started_at = time.perf_counter()
            batch_rows = client.run_query(
                query=PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BATCH_BY_DATE_WINDOW_QUERY,
                parameters={
                    "patient_ids": [str(patient_id) for patient_id in candidate_patient_ids],
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                },
            )
            batch_elapsed_seconds = round(time.perf_counter() - batch_started_at, 3)

        elapsed_seconds = round(time.perf_counter() - started_at, 3)
        queue.put(
            {
                "variant": (
                    "compare_patient_exclusive_training_task_history_batch_by_date_window"
                ),
                "status": "completed",
                "row_count": {
                    "individual": individual_row_count,
                    "batch": len(batch_rows),
                },
                "elapsed_seconds": elapsed_seconds,
                "individual_elapsed_seconds": individual_elapsed_seconds,
                "batch_elapsed_seconds": batch_elapsed_seconds,
                "candidate_patient_count": len(candidate_patient_ids),
                "per_patient_results": per_patient_results,
                "error": None,
            }
        )
    except Exception as exc:  # pragma: no cover - defensive for external DB errors.
        elapsed_seconds = round(time.perf_counter() - started_at, 3)
        queue.put(
            {
                "variant": (
                    "compare_patient_exclusive_training_task_history_batch_by_date_window"
                ),
                "status": "failed",
                "row_count": None,
                "elapsed_seconds": elapsed_seconds,
                "error": str(exc),
            }
        )


def run_variant(
    *,
    config_path: str,
    variant: str,
    query: str,
    parameters: dict[str, object],
    timeout_seconds: int,
) -> dict[str, object]:
    """Run one variant with a parent-side timeout."""
    context = mp.get_context("spawn")
    queue: mp.Queue = context.Queue()
    process = context.Process(
        target=run_query_worker,
        args=(config_path, variant, query, parameters, queue),
    )
    started_at = time.perf_counter()
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join(10)
        return {
            "variant": variant,
            "status": "timeout",
            "row_count": None,
            "elapsed_seconds": round(time.perf_counter() - started_at, 3),
            "error": f"Timed out after {timeout_seconds} seconds.",
        }

    if not queue.empty():
        return dict(queue.get())

    return {
        "variant": variant,
        "status": "failed",
        "row_count": None,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "error": f"Worker exited without result. exitcode={process.exitcode}",
    }


def run_candidate_history_compare_variant(
    *,
    config_path: str,
    candidate_patient_ids: list[str],
    start_date: str,
    end_date: str,
    timeout_seconds: int,
) -> dict[str, object]:
    """Run per-patient vs batch candidate-history comparison with timeout."""
    context = mp.get_context("spawn")
    queue: mp.Queue = context.Queue()
    process = context.Process(
        target=run_candidate_history_compare_worker,
        args=(
            config_path,
            candidate_patient_ids,
            start_date,
            end_date,
            queue,
        ),
    )
    started_at = time.perf_counter()
    process.start()
    process.join(timeout_seconds)

    if process.is_alive():
        process.terminate()
        process.join(10)
        return {
            "variant": (
                "compare_patient_exclusive_training_task_history_batch_by_date_window"
            ),
            "status": "timeout",
            "row_count": None,
            "elapsed_seconds": round(time.perf_counter() - started_at, 3),
            "candidate_patient_count": len(candidate_patient_ids),
            "error": f"Timed out after {timeout_seconds} seconds.",
        }

    if not queue.empty():
        return dict(queue.get())

    return {
        "variant": "compare_patient_exclusive_training_task_history_batch_by_date_window",
        "status": "failed",
        "row_count": None,
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "candidate_patient_count": len(candidate_patient_ids),
        "error": f"Worker exited without result. exitcode={process.exitcode}",
    }


def write_output(
    *,
    output_dir: str | Path,
    parameters: dict[str, object],
    selected_variants: list[str],
    results: list[dict[str, object]],
) -> Path:
    """Write benchmark results to a timestamped JSON file."""
    resolved_output_dir = Path(output_dir)
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    output_path = resolved_output_dir / f"patient_game_path_query_benchmark_{timestamp}.json"
    payload = {
        "created_at_utc": timestamp,
        "parameters": parameters,
        "variants": selected_variants,
        "results": results,
    }
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return output_path


def main() -> int:
    """Run selected query benchmarks."""
    args = parse_args()
    if args.list_variants:
        for variant in sorted(QUERY_VARIANTS):
            print(variant)
        for variant in sorted(STATISTICS_VARIANTS):
            print(variant)
        for variant in sorted(COMPARE_VARIANTS):
            print(variant)
        return 0

    selected_variants = args.variant or list(QUERY_VARIANTS)
    patient_ids = read_patient_ids(args)
    candidate_patient_ids = read_candidate_patient_ids(
        args,
        fallback_patient_ids=patient_ids,
    )

    if args.dry_run:
        for variant in selected_variants:
            print(f"\n--- {variant} ---")
            if variant in COMPARE_VARIANTS:
                print(PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BY_DATE_WINDOW_QUERY)
                print("\n--- batch query ---")
                print(PATIENT_EXCLUSIVE_TRAINING_TASK_HISTORY_BATCH_BY_DATE_WINDOW_QUERY)
            else:
                print(ALL_VARIANTS[variant])
        return 0

    results: list[dict[str, object]] = []
    for variant in selected_variants:
        if variant in COMPARE_VARIANTS:
            LOGGER.info(
                "Running candidate-history compare variant: candidate_patient_count=%s, variant=%s",
                len(candidate_patient_ids),
                variant,
            )
            result = run_candidate_history_compare_variant(
                config_path=args.config,
                candidate_patient_ids=candidate_patient_ids,
                start_date=str(args.start_date),
                end_date=str(args.end_date),
                timeout_seconds=args.timeout_seconds,
            )
            LOGGER.info(
                "Completed candidate-history compare variant: variant=%s, status=%s, row_count=%s, individual_elapsed_seconds=%s, batch_elapsed_seconds=%s",
                result["variant"],
                result["status"],
                result["row_count"],
                result.get("individual_elapsed_seconds"),
                result.get("batch_elapsed_seconds"),
            )
            results.append(result)
        elif variant == "patient_exclusive_training_task_history_batch_by_date_window":
            LOGGER.info(
                "Running batch candidate-history query variant: candidate_patient_count=%s, variant=%s",
                len(candidate_patient_ids),
                variant,
            )
            result = run_variant(
                config_path=args.config,
                variant=variant,
                query=ALL_VARIANTS[variant],
                parameters=build_batch_history_parameters(args, candidate_patient_ids),
                timeout_seconds=args.timeout_seconds,
            )
            result["candidate_patient_count"] = len(candidate_patient_ids)
            result["candidate_patient_ids"] = candidate_patient_ids
            LOGGER.info(
                "Completed batch candidate-history query variant: variant=%s, status=%s, row_count=%s, elapsed_seconds=%s",
                result["variant"],
                result["status"],
                result["row_count"],
                result["elapsed_seconds"],
            )
            results.append(result)

    for patient_id in patient_ids:
        parameters = build_parameters(args, patient_id)
        for variant in selected_variants:
            if (
                variant in COMPARE_VARIANTS
                or variant
                == "patient_exclusive_training_task_history_batch_by_date_window"
            ):
                continue
            LOGGER.info(
                "Running query variant: patient_id=%s, variant=%s",
                patient_id,
                variant,
            )
            result = run_variant(
                config_path=args.config,
                variant=variant,
                query=ALL_VARIANTS[variant],
                parameters=parameters,
                timeout_seconds=args.timeout_seconds,
            )
            result["patient_id"] = patient_id
            LOGGER.info(
                "Completed query variant: patient_id=%s, variant=%s, status=%s, row_count=%s, elapsed_seconds=%s",
                patient_id,
                result["variant"],
                result["status"],
                result["row_count"],
                result["elapsed_seconds"],
            )
            results.append(result)

    output_path = write_output(
        output_dir=args.output_dir,
        parameters={
            "patient_ids": patient_ids,
            "candidate_patient_ids": candidate_patient_ids,
            "start_date": str(args.start_date),
            "end_date": str(args.end_date),
            "per_g": int(args.per_g),
            "limit": int(args.limit),
            "timeout_seconds": int(args.timeout_seconds),
            "base_date": str(args.base_date),
            "age_window": int(args.age_window),
            "profile_candidate_training_window_days": int(
                args.profile_candidate_training_window_days
            ),
        },
        selected_variants=selected_variants,
        results=results,
    )
    print(json.dumps({"output_path": str(output_path), "results": results}, ensure_ascii=False, indent=2))
    return 0 if all(result["status"] == "completed" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
