"""OpenAI-compatible LLM client."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import requests

from config.settings import DEFAULT_CONFIG_PATH, LlmSettings, load_llm_settings

from ..utils.logger import get_logger


LOGGER = get_logger(__name__)
MAX_ERROR_BODY_CHARS = 500


@dataclass
class LlmError(Exception):
    """Error raised for LLM request and response failures."""

    message: str
    code: str | None = None
    status_code: int | None = None
    retryable: bool = False
    original_error: Exception | None = None
    response_body: str | None = None

    def __str__(self) -> str:
        text = f"[{self.code}] {self.message}" if self.code else self.message
        if self.status_code is not None:
            text = f"{text} (status={self.status_code})"
        return text


class LlmClient:
    """Small OpenAI-compatible chat-completions client."""

    def __init__(
        self,
        settings: LlmSettings,
        *,
        session: requests.Session | None = None,
        sleep: Any = time.sleep,
    ) -> None:
        self.settings = settings
        self.session = session or requests.Session()
        self._sleep = sleep

    @classmethod
    def from_config(cls, config_path: str | Path = DEFAULT_CONFIG_PATH) -> "LlmClient":
        """Create an LLM client from repository YAML settings."""
        return cls(load_llm_settings(config_path))

    def chat(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Send one user prompt and return the assistant content."""
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt must be a non-empty string.")

        messages: list[dict[str, str]] = []
        if system_prompt is not None:
            if not isinstance(system_prompt, str) or not system_prompt.strip():
                raise ValueError("system_prompt must be a non-empty string when set.")
            messages.append({"role": "system", "content": system_prompt.strip()})
        messages.append({"role": "user", "content": prompt.strip()})
        return self.chat_messages(messages, temperature=temperature)

    def chat_messages(
        self,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.7,
    ) -> str:
        """Send chat-completion messages and return the assistant content."""
        self._validate_messages(messages)
        payload = {
            "model": self.settings.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }
        data = self._post(payload)
        return self._extract_content(data)

    def _post(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.settings.base_url.rstrip('/')}/v1/chat/completions"
        last_error: LlmError | None = None

        for attempt in range(1, self.settings.max_retries + 1):
            try:
                response = self.session.post(
                    url,
                    headers=self._build_headers(),
                    json=payload,
                    timeout=self.settings.timeout,
                )
                if response.status_code >= 400:
                    raise self._build_http_error(response)

                try:
                    data = response.json()
                except ValueError as exc:
                    raise LlmError(
                        message="Invalid JSON response from LLM.",
                        code="INVALID_JSON",
                        retryable=False,
                        original_error=exc,
                    ) from exc

                if not isinstance(data, dict):
                    raise LlmError(
                        message="Invalid LLM response payload.",
                        code="INVALID_RESPONSE",
                        retryable=False,
                    )

                LOGGER.debug(
                    "LLM call succeeded: model=%s attempt=%s",
                    self.settings.model,
                    attempt,
                )
                return data

            except requests.Timeout as exc:
                last_error = LlmError(
                    message="LLM request timed out.",
                    code="TIMEOUT",
                    retryable=True,
                    original_error=exc,
                )
            except requests.RequestException as exc:
                last_error = LlmError(
                    message="Network error when calling LLM.",
                    code="NETWORK_ERROR",
                    retryable=True,
                    original_error=exc,
                )
            except LlmError as exc:
                last_error = exc

            if not last_error.retryable:
                LOGGER.error("Non-retryable LLM error: %s", last_error)
                raise last_error
            if attempt < self.settings.max_retries:
                sleep_seconds = self.settings.backoff_factor**attempt
                LOGGER.warning(
                    "Retryable LLM error on attempt %s/%s: %s",
                    attempt,
                    self.settings.max_retries,
                    last_error,
                )
                self._sleep(sleep_seconds)

        raise last_error or LlmError(message="Unknown LLM failure.", code="UNKNOWN")

    def _build_headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.settings.api_key:
            headers["Authorization"] = f"Bearer {self.settings.api_key}"
        return headers

    @staticmethod
    def _build_http_error(response: requests.Response) -> LlmError:
        response_body = _truncate_text(response.text, MAX_ERROR_BODY_CHARS)
        return LlmError(
            message="HTTP error from LLM.",
            code="HTTP_ERROR",
            status_code=response.status_code,
            retryable=response.status_code == 429 or response.status_code >= 500,
            response_body=response_body,
        )

    @staticmethod
    def _extract_content(data: dict[str, Any]) -> str:
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmError(
                message="Invalid LLM response format.",
                code="INVALID_RESPONSE",
                retryable=False,
                original_error=exc,
            ) from exc

        if not isinstance(content, str):
            raise LlmError(
                message="Invalid LLM response content.",
                code="INVALID_RESPONSE",
                retryable=False,
            )
        return content

    @staticmethod
    def _validate_messages(messages: list[dict[str, str]]) -> None:
        if not isinstance(messages, list) or not messages:
            raise ValueError("messages must be a non-empty list.")
        for message in messages:
            if not isinstance(message, dict):
                raise ValueError("Each message must be a mapping.")
            role = message.get("role")
            content = message.get("content")
            if not isinstance(role, str) or not role.strip():
                raise ValueError("Each message role must be a non-empty string.")
            if not isinstance(content, str) or not content.strip():
                raise ValueError("Each message content must be a non-empty string.")


def _truncate_text(text: str, max_chars: int) -> str:
    """Return a compact response body snippet for diagnostics."""
    if len(text) <= max_chars:
        return text
    return f"{text[:max_chars]}..."
