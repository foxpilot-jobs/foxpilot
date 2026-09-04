"""Provider contract shared by local and hosted models."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class LLMError(RuntimeError):
    """An actionable provider or model failure."""


class LLMTimeoutError(LLMError):
    """The provider did not complete within its configured request timeout."""


class LLMRateLimitError(LLMError):
    """The provider rate-limited or exhausted request/token quota (e.g. 429)."""

    def __init__(self, message: str, retry_after_seconds: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_seconds = retry_after_seconds


def is_rate_limit_error(error: Exception) -> bool:
    """Return True if an exception represents a 429 rate limit or quota exhaustion."""
    if isinstance(error, LLMRateLimitError):
        return True
    msg = str(error).lower()
    return any(
        hint in msg
        for hint in (
            "429",
            "rate limit",
            "rate_limit",
            "resourceexhausted",
            "resource_exhausted",
            "too_many_requests",
            "quota",
        )
    )


class LLMProvider(ABC):
    @abstractmethod
    def complete_json(self, prompt: str, response_schema: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return one validated JSON object for a prompt."""


def parse_json_response(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.removeprefix("```json").removeprefix("```")
        cleaned = cleaned.removesuffix("```").strip()

    import json

    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError as error:
        raise LLMError(f"The model returned invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise LLMError("The model returned JSON, but not a JSON object.")
    return value
