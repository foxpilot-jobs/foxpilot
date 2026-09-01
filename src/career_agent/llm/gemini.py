"""Optional Google Gemini provider using the official google-genai SDK."""

from __future__ import annotations

import os
from typing import Any

from google import genai
from google.genai import types

from .base import LLMError, LLMProvider, parse_json_response


class GeminiProvider(LLMProvider):
    def __init__(self, model: str = "gemini-3.6-flash", api_key: str | None = None) -> None:
        key = api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not key:
            raise LLMError("GEMINI_API_KEY is required when LLM_PROVIDER=gemini.")
        try:
            self.client = genai.Client(api_key=key)
        except Exception as error:  # noqa: BLE001
            sanitized = str(error).replace(key, "[REDACTED_API_KEY]")
            raise LLMError(f"Failed to initialize Gemini client: {sanitized}") from None
        self.model = model
        self._api_key = key

    def complete_json(
        self, prompt: str, response_schema: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        config_kwargs: dict[str, Any] = {"response_mime_type": "application/json"}
        if response_schema is not None:
            config_kwargs["response_schema"] = response_schema
        config = types.GenerateContentConfig(**config_kwargs)
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=prompt,
                config=config,
            )
        except Exception as error:  # noqa: BLE001
            error_msg = str(error)
            if self._api_key and self._api_key in error_msg:
                error_msg = error_msg.replace(self._api_key, "[REDACTED_API_KEY]")
            raise LLMError(f"Gemini request failed: {error_msg}") from None

        text = response.text or ""
        if not text:
            raise LLMError("Gemini returned an empty response.")

        try:
            return parse_json_response(text)
        except LLMError as parse_err:
            err_msg = str(parse_err)
            if self._api_key and self._api_key in err_msg:
                err_msg = err_msg.replace(self._api_key, "[REDACTED_API_KEY]")
            raise LLMError(err_msg) from None
