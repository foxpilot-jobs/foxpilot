"""Create the configured LLM provider."""

from __future__ import annotations

from .base import LLMError, LLMProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider
from ..config import AppConfig


def create_provider(config: AppConfig) -> LLMProvider:
    provider = config.llm_provider.lower()
    if provider == "ollama":
        return OllamaProvider(
            model=config.llm_model,
            base_url=config.ollama_base_url,
        )
    if provider == "openai":
        return OpenAIProvider(model=config.llm_model)
    raise LLMError(
        f"Unsupported LLM_PROVIDER={config.llm_provider!r}. Use `ollama` or `openai`."
    )
