"""Tests for the OpenAI-compatible LLM client."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from config.settings import LlmSettings, load_llm_settings
from src.similar_user.services.llm_client import LlmClient, LlmError


class FakeResponse:
    """Small response double for LLM client tests."""

    def __init__(
        self,
        *,
        status_code: int = 200,
        payload: object | None = None,
        text: str = "",
        json_error: Exception | None = None,
    ) -> None:
        self.status_code = status_code
        self.payload = payload
        self.text = text
        self.json_error = json_error

    def json(self) -> object:
        if self.json_error is not None:
            raise self.json_error
        return self.payload


class LlmClientTest(unittest.TestCase):
    def test_chat_posts_openai_compatible_payload(self) -> None:
        session = Mock()
        session.post.return_value = FakeResponse(
            payload={"choices": [{"message": {"content": "推荐说明"}}]}
        )
        client = LlmClient(
            LlmSettings(
                base_url="http://localhost:8000/",
                api_key="sk-test",
                model="qwen3_5",
            ),
            session=session,
        )

        result = client.chat(
            "生成推荐理由",
            system_prompt="你是推荐助手",
            temperature=0.2,
        )

        self.assertEqual(result, "推荐说明")
        session.post.assert_called_once_with(
            "http://localhost:8000/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer sk-test",
            },
            json={
                "model": "qwen3_5",
                "messages": [
                    {"role": "system", "content": "你是推荐助手"},
                    {"role": "user", "content": "生成推荐理由"},
                ],
                "temperature": 0.2,
                "stream": False,
            },
            timeout=60,
        )

    def test_chat_retries_retryable_http_errors(self) -> None:
        session = Mock()
        session.post.side_effect = [
            FakeResponse(status_code=500, text="server error"),
            FakeResponse(payload={"choices": [{"message": {"content": "ok"}}]}),
        ]
        sleep = Mock()
        client = LlmClient(
            LlmSettings(
                base_url="http://localhost:8000",
                model="qwen3_5",
                max_retries=2,
                backoff_factor=1.5,
            ),
            session=session,
            sleep=sleep,
        )

        self.assertEqual(client.chat("hello"), "ok")
        self.assertEqual(session.post.call_count, 2)
        sleep.assert_called_once_with(1.5)

    def test_chat_does_not_retry_non_retryable_http_errors(self) -> None:
        session = Mock()
        session.post.return_value = FakeResponse(status_code=401, text="unauthorized")
        client = LlmClient(
            LlmSettings(base_url="http://localhost:8000", model="qwen3_5"),
            session=session,
            sleep=Mock(),
        )

        with self.assertRaisesRegex(LlmError, "HTTP error"):
            client.chat("hello")

        self.assertEqual(session.post.call_count, 1)

    def test_chat_retries_timeout(self) -> None:
        session = Mock()
        session.post.side_effect = [
            requests.Timeout("timed out"),
            FakeResponse(payload={"choices": [{"message": {"content": "ok"}}]}),
        ]
        client = LlmClient(
            LlmSettings(
                base_url="http://localhost:8000",
                model="qwen3_5",
                max_retries=2,
            ),
            session=session,
            sleep=Mock(),
        )

        self.assertEqual(client.chat("hello"), "ok")
        self.assertEqual(session.post.call_count, 2)

    def test_chat_raises_for_invalid_response_shape(self) -> None:
        session = Mock()
        session.post.return_value = FakeResponse(payload={"choices": []})
        client = LlmClient(
            LlmSettings(base_url="http://localhost:8000", model="qwen3_5"),
            session=session,
        )

        with self.assertRaisesRegex(LlmError, "Invalid LLM response format"):
            client.chat("hello")

    def test_chat_messages_validates_messages(self) -> None:
        client = LlmClient(
            LlmSettings(base_url="http://localhost:8000", model="qwen3_5"),
            session=Mock(),
        )

        with self.assertRaisesRegex(ValueError, "messages"):
            client.chat_messages([])

        with self.assertRaisesRegex(ValueError, "content"):
            client.chat_messages([{"role": "user", "content": "   "}])

    def test_load_llm_settings_uses_yaml_and_env_api_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "settings.yaml"
            config_path.write_text(
                "\n".join(
                    [
                        "llm:",
                        "  base_url: http://localhost:8000",
                        "  api_key: yaml-key",
                        "  model: qwen3_5",
                        "  timeout: 30",
                        "  max_retries: 2",
                        "  backoff_factor: 2",
                    ]
                ),
                encoding="utf-8",
            )

            with patch.dict("os.environ", {"SIMILAR_USER_LLM_API_KEY": "env-key"}):
                settings = load_llm_settings(config_path)

        self.assertEqual(settings.base_url, "http://localhost:8000")
        self.assertEqual(settings.api_key, "env-key")
        self.assertEqual(settings.model, "qwen3_5")
        self.assertEqual(settings.timeout, 30)
        self.assertEqual(settings.max_retries, 2)
        self.assertEqual(settings.backoff_factor, 2.0)


if __name__ == "__main__":
    unittest.main()
