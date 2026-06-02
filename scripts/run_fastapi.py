"""Run the FastAPI prediction API locally."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

import uvicorn


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for local FastAPI startup."""
    parser = argparse.ArgumentParser(description="Run the similar_user FastAPI API.")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--workers", type=int, default=1)
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    uvicorn.run(
        "similar_user.api.fastapi_app:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
    )
