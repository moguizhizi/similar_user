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

from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.utils.logger import get_logger


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
DEFAULT_OUTPUT_DIR = Path("logs/path_query_benchmarks")
DEFAULT_PATIENT_ID = "30050783"
DEFAULT_START_DATE = "2026-05-24"
DEFAULT_END_DATE = "2026-05-25"
DEFAULT_PER_G = 10
DEFAULT_LIMIT = 310
DEFAULT_TIMEOUT_SECONDS = 900
LOGGER = get_logger(__name__)


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


QUERY_VARIANTS = {
    "original": ORIGINAL_QUERY,
    "local_sampling": LOCAL_SAMPLING_QUERY,
    "layer1_age_completion": LAYER1_AGE_COMPLETION_QUERY,
    "layer2_education_exact": LAYER2_EDUCATION_EXACT_QUERY,
    "layer3_activity_task_type": LAYER3_ACTIVITY_TASK_TYPE_QUERY,
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


STATISTICS_VARIANTS = {
    "stats_original": ORIGINAL_STATISTICS_QUERY,
    "stats_approx_group": APPROX_STATISTICS_QUERY,
}

ALL_VARIANTS = {**QUERY_VARIANTS, **STATISTICS_VARIANTS}


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
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
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
        choices=sorted(ALL_VARIANTS),
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


def build_parameters(args: argparse.Namespace, patient_id: str) -> dict[str, object]:
    """Build Cypher parameters from parsed arguments."""
    return {
        "patient_id": str(patient_id),
        "start_date": str(args.start_date),
        "end_date": str(args.end_date),
        "per_g": int(args.per_g),
        "limit": int(args.limit),
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
        return 0

    selected_variants = args.variant or list(QUERY_VARIANTS)
    patient_ids = read_patient_ids(args)

    if args.dry_run:
        for variant in selected_variants:
            print(f"\n--- {variant} ---")
            print(ALL_VARIANTS[variant])
        return 0

    results: list[dict[str, object]] = []
    for patient_id in patient_ids:
        parameters = build_parameters(args, patient_id)
        for variant in selected_variants:
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
            "start_date": str(args.start_date),
            "end_date": str(args.end_date),
            "per_g": int(args.per_g),
            "limit": int(args.limit),
            "timeout_seconds": int(args.timeout_seconds),
        },
        selected_variants=selected_variants,
        results=results,
    )
    print(json.dumps({"output_path": str(output_path), "results": results}, ensure_ascii=False, indent=2))
    return 0 if all(result["status"] == "completed" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
