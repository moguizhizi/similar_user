"""Tests for direct entity name resolution levels."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from src.similar_user.services.direct_entity_name_resolution import (
    DirectEntityNameResolver,
)


class DirectEntityNameResolverTest(unittest.TestCase):
    def test_resolve_prefers_neo4j_exact_matches(self) -> None:
        repository = Mock()
        repository.resolve_direct_entity_name.return_value = [
            {
                "entity_type": "disease",
                "entity_id": "AU_DIS_0002",
                "entity_name": "注意缺陷多动障碍",
            }
        ]

        result = DirectEntityNameResolver(repository).resolve_names(["注意缺陷多动障碍"])

        self.assertEqual(result["unresolved"], [])
        self.assertEqual(result["resolved"][0]["entity_id"], "AU_DIS_0002")
        self.assertEqual(result["resolved"][0]["resolution_level"], "neo4j_exact")
        repository.get_direct_entity_alias_index.assert_not_called()

    def test_resolve_uses_normalized_alias_index_after_exact_miss(self) -> None:
        repository = Mock()
        repository.resolve_direct_entity_name.return_value = []
        repository.get_direct_entity_alias_index.return_value = [
            {
                "entity_type": "disease",
                "entity_id": "AU_DIS_0002",
                "entity_name": "注意缺陷多动障碍",
                "alias_label": "ADHD",
            }
        ]

        result = DirectEntityNameResolver(repository).resolve_names([" a d h d "])

        self.assertEqual(result["unresolved"], [])
        self.assertEqual(result["resolved"][0]["entity_id"], "AU_DIS_0002")
        self.assertEqual(
            result["resolved"][0]["resolution_level"],
            "neo4j_alias_index",
        )

    def test_resolve_reports_unresolved_when_all_levels_miss(self) -> None:
        repository = Mock()
        repository.resolve_direct_entity_name.return_value = []
        repository.get_direct_entity_alias_index.return_value = []

        result = DirectEntityNameResolver(repository).resolve_names(["不存在疾病"])

        self.assertEqual(result["resolved"], [])
        self.assertEqual(
            result["unresolved"],
            [{"input_name": "不存在疾病", "reason": "not_found_in_kg"}],
        )


if __name__ == "__main__":
    unittest.main()
