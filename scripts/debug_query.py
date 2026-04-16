"""Temporary script for debugging Cypher queries."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.utils.logger import get_logger


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
DEFAULT_QUERY = "RETURN 1 AS ok, 'neo4j connected' AS message"
LOGGER = get_logger(__name__)


def run_debug_query(
    config_path: str | Path = DEFAULT_CONFIG_PATH,
    query: str = DEFAULT_QUERY,
) -> list[dict[str, object]]:
    """Connect to Neo4j and run a small verification query."""
    with Neo4jClient.from_config(config_path) as client:
        return client.run_query(query)


def main() -> int:
    """Run a simple query and log JSON output for quick verification."""
    try:
        result = run_debug_query()
    except Exception as exc:
        LOGGER.exception("Neo4j query failed: %s", exc)
        return 1

    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
