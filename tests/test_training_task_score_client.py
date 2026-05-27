"""Tests for the external training-task score client."""

from __future__ import annotations

import unittest

from src.similar_user.services.training_task_score_client import (
    TrainingTaskScoreClient,
    TrainingTaskScoreError,
    build_training_task_score_payload,
)


class TrainingTaskScoreClientTest(unittest.TestCase):
    def test_build_payload_maps_csv_ba_to_pre_score_ba(self) -> None:
        payload = build_training_task_score_payload(
            ["299", "300", "299"],
            ai_params={
                "ba": [0.5, 0.6],
                "sex": 1,
                "education": 2,
                "age": 30,
                "sicksName": [],
            },
        )

        self.assertEqual(
            payload,
            {
                "tt_list": ["299", "300"],
                "pre_score_ba": [0.5, 0.6],
                "sex": 1,
                "education": 2,
                "age": 30,
                "sicksName": [],
            },
        )

    def test_score_tasks_aligns_scores_with_task_ids(self) -> None:
        session = _FakeSession({"score": [55.58, 52.04]})
        client = TrainingTaskScoreClient(
            "http://example.test/training_task_score",
            session=session,
        )

        result = client.score_tasks(
            ["299", "300"],
            ai_params={
                "pre_score_ba": [0.5],
                "sex": 1,
                "education": 2,
                "age": 30,
                "sicksName": [],
            },
        )

        self.assertEqual(
            result,
            [
                {"task_id": "299", "score": 55.58},
                {"task_id": "300", "score": 52.04},
            ],
        )
        self.assertEqual(
            session.last_json["tt_list"],
            ["299", "300"],
        )

    def test_score_tasks_rejects_score_count_mismatch(self) -> None:
        client = TrainingTaskScoreClient(
            "http://example.test/training_task_score",
            session=_FakeSession({"score": [55.58]}),
        )

        with self.assertRaisesRegex(TrainingTaskScoreError, "count does not match"):
            client.score_tasks(
                ["299", "300"],
                ai_params={"pre_score_ba": [0.5]},
            )


class _FakeSession:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload
        self.last_json: dict[str, object] = {}

    def post(
        self,
        url: str,
        *,
        json: dict[str, object],
        timeout: float,
    ) -> "_FakeResponse":
        self.last_json = json
        return _FakeResponse(self.payload)


class _FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self.payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self.payload


if __name__ == "__main__":
    unittest.main()
