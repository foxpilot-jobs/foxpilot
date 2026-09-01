"""Create the configured LLM provider."""

from __future__ import annotations

from ..config import AppConfig
from .base import LLMError, LLMProvider
from .gemini import GeminiProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider


def create_provider(config: AppConfig) -> LLMProvider:
    provider = config.llm_provider.lower()
    if provider in ("gemini", "google"):
        return GeminiProvider(model=config.llm_model)
    if provider == "ollama":
        return OllamaProvider(
            model=config.llm_model,
            base_url=config.ollama_base_url,
        )
    if provider == "openai":
        return OpenAIProvider(model=config.llm_model)
    raise LLMError(
        f"Unsupported LLM_PROVIDER={config.llm_provider!r}. Use `gemini`, `openai`, or `ollama`."
    )
