"""List source patients selected by a named eligibility rule."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"
for candidate in (PROJECT_ROOT, SRC_ROOT):
    candidate_str = str(candidate)
    if candidate_str not in sys.path:
        sys.path.insert(0, candidate_str)

from similar_user.data_access.kg_repository import KgRepository
from similar_user.data_access.neo4j_client import Neo4jClient
from similar_user.services.source_patient_selection import (
    SECONDARY_ABILITY_ANY_RULE,
    SourcePatientSelectionService,
)
from similar_user.services.user_service import UserService
from similar_user.utils.logger import get_logger


DEFAULT_CONFIG_PATH = Path("config/settings.yaml")
DEFAULT_OUTPUT_DIR = Path("data/source_patients")
LOGGER = get_logger(__name__)


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for source patient selection."""
    parser = argparse.ArgumentParser(
        description="List source patients selected by a named eligibility rule."
    )
    parser.add_argument(
        "--rule",
        default=SECONDARY_ABILITY_ANY_RULE,
        help="Registered source patient selection rule.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Output JSON path. Defaults to data/source_patients/<rule>.json.",
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_PATH),
        help="Path to the YAML config file.",
    )
    return parser.parse_args()


def list_source_patients(
    *,
    rule: str = SECONDARY_ABILITY_ANY_RULE,
    output_path: str | Path | None = None,
    config_path: str | Path = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    """Select source patients and save the result as JSON."""
    resolved_output_path = _resolve_output_path(rule, output_path)
    with Neo4jClient.from_config(config_path) as client:
        user_service = UserService(
            kg_repository=KgRepository(
                client=client,
                config_path=Path(config_path),
            )
        )
        selection_service = SourcePatientSelectionService(user_service=user_service)
        payload = selection_service.build_source_patient_payload(rule)

    resolved_output_path.parent.mkdir(parents=True, exist_ok=True)
    resolved_output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return payload


def main() -> int:
    """Write selected source patients to a JSON file."""
    args = parse_args()
    output_path = _resolve_output_path(args.rule, args.output)
    try:
        result = list_source_patients(
            rule=args.rule,
            output_path=output_path,
            config_path=args.config,
        )
    except Exception as exc:
        LOGGER.exception("List source patients failed: %s", exc)
        return 1

    LOGGER.info(
        "Wrote %s source patients for rule %s to %s",
        result["count"],
        result["rule"],
        output_path,
    )
    LOGGER.info(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def _resolve_output_path(rule: str, output_path: str | Path | None) -> Path:
    if output_path is not None:
        return Path(output_path)
    normalized_rule = rule.strip() if isinstance(rule, str) and rule.strip() else "rule"
    return DEFAULT_OUTPUT_DIR / f"{normalized_rule}.json"


if __name__ == "__main__":
    raise SystemExit(main())
