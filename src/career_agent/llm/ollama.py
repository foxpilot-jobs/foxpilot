"""Ollama provider using its local HTTP API."""

from __future__ import annotations

from typing import Any

import httpx

from .base import LLMError, LLMProvider, LLMTimeoutError, parse_json_response


class OllamaProvider(LLMProvider):
    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434",
        timeout: float = 180.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def complete_json(
        self, prompt: str, response_schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "format": response_schema or "json",
            "options": {"temperature": 0, "num_predict": 384},
        }
        try:
            response = httpx.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout,
            )
            response.raise_for_status()
        except httpx.ConnectError as error:
            raise LLMError(
                "Ollama is not running. Start it with `ollama serve`, "
                f"then make sure `{self.model}` is installed with `ollama pull {self.model}`."
            ) from error
        except httpx.TimeoutException as error:
            raise LLMTimeoutError(
                f"Ollama did not finish within {self.timeout:.0f} seconds. "
                "Try a shorter resume or a faster model."
            ) from error
        except httpx.HTTPStatusError as error:
            detail = error.response.text[:500]
            raise LLMError(f"Ollama request failed ({error.response.status_code}): {detail}") from error
        except httpx.HTTPError as error:
            raise LLMError(f"Ollama request failed: {error}") from error

        try:
            content = response.json()["message"]["content"]
        except (KeyError, TypeError, ValueError) as error:
            raise LLMError("Ollama returned an unexpected response shape.") from error
        return parse_json_response(content)
