from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from career_agent.config import AppConfig
from career_agent.llm import LLMError, create_provider
from career_agent.llm.gemini import GeminiProvider
from career_agent.llm.ollama import OllamaProvider
from career_agent.llm.openai import OpenAIProvider


def test_gemini_provider_instantiation_with_explicit_key() -> None:
    with patch("google.genai.Client") as mock_client:
        provider = GeminiProvider(model="gemini-2.5-flash", api_key="test-secret-key-123")
        assert provider.model == "gemini-2.5-flash"
        mock_client.assert_called_once_with(api_key="test-secret-key-123")


def test_gemini_provider_instantiation_with_env_key(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "env-secret-key-456")
    with patch("google.genai.Client") as mock_client:
        provider = GeminiProvider(model="gemini-2.5-flash")
        assert provider.model == "gemini-2.5-flash"
        mock_client.assert_called_once_with(api_key="env-secret-key-456")


def test_gemini_provider_instantiation_with_google_env_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.setenv("GOOGLE_API_KEY", "google-secret-key-789")
    with patch("google.genai.Client") as mock_client:
        provider = GeminiProvider(model="gemini-2.5-flash")
        assert provider.model == "gemini-2.5-flash"
        mock_client.assert_called_once_with(api_key="google-secret-key-789")


def test_gemini_provider_missing_api_key(monkeypatch) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    with pytest.raises(LLMError, match="GEMINI_API_KEY is required"):
        GeminiProvider(model="gemini-2.5-flash")


def test_gemini_provider_complete_json_success() -> None:
    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance

        mock_response = MagicMock()
        mock_response.text = '{"match_score": 92, "recommendation": "APPLY"}'
        mock_instance.models.generate_content.return_value = mock_response

        schema = {"type": "OBJECT", "properties": {"match_score": {"type": "INTEGER"}}}
        provider = GeminiProvider(model="gemini-2.5-flash", api_key="secret-key-xyz")
        res = provider.complete_json("Evaluate job match", response_schema=schema)

        assert res == {"match_score": 92, "recommendation": "APPLY"}

        mock_instance.models.generate_content.assert_called_once()
        kwargs = mock_instance.models.generate_content.call_args.kwargs
        assert kwargs["model"] == "gemini-2.5-flash"
        assert kwargs["contents"] == "Evaluate job match"
        assert kwargs["config"].response_mime_type == "application/json"
        assert kwargs["config"].response_schema == schema


def test_gemini_provider_complete_json_malformed_json_raises_llmerror() -> None:
    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_response = MagicMock()
        mock_response.text = "NOT JSON TEXT"
        mock_instance.models.generate_content.return_value = mock_response

        provider = GeminiProvider(model="gemini-2.5-flash", api_key="secret-key-xyz")
        with pytest.raises(LLMError, match="invalid JSON"):
            provider.complete_json("Prompt")


def test_gemini_provider_api_exception_sanitizes_key() -> None:
    with patch("google.genai.Client") as mock_client_cls:
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        secret_key = "AIzaSySecretApiKey12345"
        mock_instance.models.generate_content.side_effect = RuntimeError(
            f"Quota exceeded for key {secret_key}"
        )

        provider = GeminiProvider(model="gemini-2.5-flash", api_key=secret_key)
        with pytest.raises(LLMError) as exc_info:
            provider.complete_json("Prompt")

        err_text = str(exc_info.value)
        assert secret_key not in err_text
        assert "[REDACTED_API_KEY]" in err_text


def test_factory_creates_gemini_provider(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("google.genai.Client"):
        config = AppConfig(llm_provider="gemini", llm_model="gemini-3.6-flash")
        provider = create_provider(config)
        assert isinstance(provider, GeminiProvider)
        assert provider.model == "gemini-3.6-flash"


def test_factory_creates_google_alias_provider(monkeypatch) -> None:
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")
    with patch("google.genai.Client"):
        config = AppConfig(llm_provider="google", llm_model="gemini-1.5-flash")
        provider = create_provider(config)
        assert isinstance(provider, GeminiProvider)
        assert provider.model == "gemini-1.5-flash"


def test_factory_preserves_openai_and_ollama_providers(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    with patch("openai.OpenAI"):
        openai_config = AppConfig(llm_provider="openai", llm_model="gpt-4o-mini")
        assert isinstance(create_provider(openai_config), OpenAIProvider)

    ollama_config = AppConfig(llm_provider="ollama", llm_model="llama3.1:8b")
    assert isinstance(create_provider(ollama_config), OllamaProvider)
