"""Tests for Neo4j reads used by direct path cache sync."""

from __future__ import annotations

import unittest
from unittest.mock import Mock

from similar_user.data_access.cypher_queries import (
    DISEASE_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY,
    DISEASE_TASKSET_PATIENT_CACHE_PATHS_QUERY,
)
from similar_user.data_access.kg_repository import KgRepository
from similar_user.domain.graph_schema import PathPattern


class DirectPathCacheRepositoryTest(unittest.TestCase):
    def test_get_direct_taskset_patient_cache_paths_uses_full_query(self) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_direct_taskset_patient_cache_paths(
            PathPattern.DISEASE_TASKSET_PATIENT
        )

        self.assertEqual(result, [{"row": {}}])
        mock_client.run_query.assert_called_once_with(
            query=DISEASE_TASKSET_PATIENT_CACHE_PATHS_QUERY,
            parameters={},
        )

    def test_get_direct_taskset_patient_cache_paths_uses_incremental_query(
        self,
    ) -> None:
        mock_client = Mock()
        mock_client.run_query.return_value = [{"row": {}}]
        repository = KgRepository(client=mock_client)

        result = repository.get_direct_taskset_patient_cache_paths(
            PathPattern.DISEASE_TASKSET_PATIENT,
            start_date="2026-05-01",
        )

        self.assertEqual(result, [{"row": {}}])
        mock_client.run_query.assert_called_once_with(
            query=DISEASE_TASKSET_PATIENT_CACHE_PATHS_BY_START_DATE_QUERY,
            parameters={"start_date": "2026-05-01"},
        )


if __name__ == "__main__":
    unittest.main()
