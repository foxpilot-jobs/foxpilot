"""Optional OpenAI provider."""

from __future__ import annotations

import os
from typing import Any

from openai import OpenAI

from .base import LLMError, LLMProvider, parse_json_response


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str) -> None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise LLMError("OPENAI_API_KEY is required when LLM_PROVIDER=openai.")
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def complete_json(self, prompt: str) -> dict[str, Any]:
        try:
            response = self.client.responses.create(
                model=self.model,
                input=prompt,
            )
        except Exception as error:
            raise LLMError(f"OpenAI request failed: {error}") from error
        return parse_json_response(response.output_text)
