"""Tests for Cypher query directory documentation."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CYPHER_QUERY_DIR = PROJECT_ROOT / "src/similar_user/data_access/cypher_queries"
QUERY_MODULES = (
    CYPHER_QUERY_DIR / "patient_dates.py",
    CYPHER_QUERY_DIR / "pattern_paths.py",
    CYPHER_QUERY_DIR / "pattern_statistics.py",
)
QUERY_README_PATH = CYPHER_QUERY_DIR / "README.md"


class CypherQueryDocsTest(unittest.TestCase):
    def test_query_readme_mentions_every_query_constant(self) -> None:
        readme = QUERY_README_PATH.read_text(encoding="utf-8")
        missing_queries = [
            query_name
            for query_name in _iter_query_constant_names()
            if query_name not in readme
        ]

        self.assertEqual(
            missing_queries,
            [],
            "Cypher query README is missing query constants.",
        )

    def test_end_date_filters_use_exclusive_upper_bound(self) -> None:
        offending_modules = []
        for module_path in QUERY_MODULES:
            text = module_path.read_text(encoding="utf-8")
            if "<= date($end_date)" in text:
                offending_modules.append(module_path.name)

        self.assertEqual(
            offending_modules,
            [],
            "Cypher end_date filters should use < date($end_date).",
        )


def _iter_query_constant_names() -> list[str]:
    query_names: list[str] = []
    for module_path in QUERY_MODULES:
        module = ast.parse(module_path.read_text(encoding="utf-8"))
        for node in module.body:
            if not isinstance(node, ast.Assign):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id.endswith("_QUERY"):
                    query_names.append(target.id)
    return sorted(query_names)


if __name__ == "__main__":
    unittest.main()
