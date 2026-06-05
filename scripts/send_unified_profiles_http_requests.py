"""Send unified profile JSONL rows to the FastAPI prediction endpoint."""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import json
from pathlib import Path
import sys
import time
from typing import Any

import requests


DEFAULT_INPUT = Path("data/unified_input/unified_patient_profiles_2026-05-25_shuffled.jsonl")
DEFAULT_URL = "http://127.0.0.1:8000/training-task/predict"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Send unified patient profiles to the FastAPI prediction endpoint."
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT), help="Input JSONL file.")
    parser.add_argument("--url", default=DEFAULT_URL, help="FastAPI endpoint URL.")
    parser.add_argument("--workers", type=int, default=4, help="Concurrent workers.")
    parser.add_argument(
        "--mode",
        choices=("thread", "process"),
        default="thread",
        help="Concurrency backend. Threads are usually better for HTTP IO.",
    )
    parser.add_argument("--timeout", type=float, default=300.0, help="Request timeout seconds.")
    parser.add_argument("--limit", type=int, help="Only send the first N rows after --start.")
    parser.add_argument("--start", type=int, default=0, help="Skip the first N rows.")
    parser.add_argument(
        "--output",
        default="data/http_requests/unified_prediction_responses.jsonl",
        help="Output JSONL file for request results.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build payloads and write them without sending HTTP requests.",
    )
    return parser.parse_args()


def iter_payloads(path: str | Path, *, start: int = 0, limit: int | None = None):
    emitted = 0
    with Path(path).open("r", encoding="utf-8") as file:
        for index, line in enumerate(file):
            if index < start:
                continue
            if limit is not None and emitted >= limit:
                break
            stripped = line.strip()
            if not stripped:
                continue
            row = json.loads(stripped)
            yield build_http_payload(row, row_index=index)
            emitted += 1


def build_http_payload(row: dict[str, Any], *, row_index: int) -> dict[str, Any]:
    raw_profile = row.get("raw_profile")
    payload = dict(raw_profile) if isinstance(raw_profile, dict) else {}

    source = row.get("source")
    source = source if isinstance(source, dict) else {}
    user_id = payload.get("user_id") or source.get("raw_user_id") or row.get("patient_id")
    if user_id is None:
        raise ValueError(f"Missing user_id at row {row_index + 1}.")
    payload["user_id"] = user_id

    if "sicksName" not in payload and isinstance(row.get("disease_names"), list):
        payload["sicksName"] = row["disease_names"]
    payload.setdefault("unlock_train", {})
    return {
        "row_index": row_index,
        "patient_id": row.get("patient_id"),
        "payload": payload,
    }


def send_one(item: dict[str, Any], *, url: str, timeout: float, dry_run: bool) -> dict[str, Any]:
    started_at = time.perf_counter()
    if dry_run:
        return {
            "row_index": item["row_index"],
            "patient_id": item.get("patient_id"),
            "status": "dry_run",
            "elapsed_seconds": 0.0,
            "request": item["payload"],
        }

    try:
        response = requests.post(url, json=item["payload"], timeout=timeout)
        try:
            body: Any = response.json()
        except ValueError:
            body = response.text
        return {
            "row_index": item["row_index"],
            "patient_id": item.get("patient_id"),
            "status": "ok" if response.ok else "http_error",
            "http_status": response.status_code,
            "elapsed_seconds": round(time.perf_counter() - started_at, 3),
            "response": body,
        }
    except Exception as exc:
        return {
            "row_index": item["row_index"],
            "patient_id": item.get("patient_id"),
            "status": "request_error",
            "elapsed_seconds": round(time.perf_counter() - started_at, 3),
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }


def write_jsonl(path: str | Path, rows: list[dict[str, Any]]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as file:
        for row in sorted(rows, key=lambda item: int(item["row_index"])):
            file.write(json.dumps(row, ensure_ascii=False, default=str) + "\n")


def main() -> int:
    args = parse_args()
    if args.workers <= 0:
        raise ValueError("--workers must be positive.")
    if args.start < 0:
        raise ValueError("--start must be non-negative.")
    if args.limit is not None and args.limit <= 0:
        raise ValueError("--limit must be positive when supplied.")

    items = list(iter_payloads(args.input, start=args.start, limit=args.limit))
    executor_cls = ThreadPoolExecutor if args.mode == "thread" else ProcessPoolExecutor
    results: list[dict[str, Any]] = []
    started_at = time.perf_counter()

    with executor_cls(max_workers=args.workers) as executor:
        futures = [
            executor.submit(
                send_one,
                item,
                url=args.url,
                timeout=args.timeout,
                dry_run=args.dry_run,
            )
            for item in items
        ]
        for completed_count, future in enumerate(as_completed(futures), start=1):
            result = future.result()
            results.append(result)
            print(
                json.dumps(
                    {
                        "completed": completed_count,
                        "total": len(items),
                        "row_index": result.get("row_index"),
                        "patient_id": result.get("patient_id"),
                        "status": result.get("status"),
                        "http_status": result.get("http_status"),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )

    write_jsonl(args.output, results)
    summary = {
        "total": len(results),
        "ok": sum(1 for item in results if item.get("status") == "ok"),
        "failed": sum(1 for item in results if item.get("status") not in {"ok", "dry_run"}),
        "dry_run": sum(1 for item in results if item.get("status") == "dry_run"),
        "elapsed_seconds": round(time.perf_counter() - started_at, 3),
        "output": args.output,
    }
    print(json.dumps(summary, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
