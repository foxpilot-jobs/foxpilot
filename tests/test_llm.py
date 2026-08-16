import httpx

from career_agent.llm.base import LLMError, LLMTimeoutError, parse_json_response
from career_agent.llm.ollama import OllamaProvider


def test_parse_json_response_accepts_json_fence() -> None:
    assert parse_json_response('```json\n{"ok": true}\n```') == {"ok": True}


def test_parse_json_response_rejects_non_object() -> None:
    try:
        parse_json_response("[]")
    except LLMError as error:
        assert "JSON object" in str(error)
    else:
        raise AssertionError("Expected LLMError")


def test_ollama_timeout_is_not_retried_as_invalid_json(monkeypatch) -> None:
    def timeout(*_args, **_kwargs):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr("career_agent.llm.ollama.httpx.post", timeout)

    try:
        OllamaProvider("test-model").complete_json("{}")
    except LLMTimeoutError as error:
        assert "did not finish" in str(error)
    else:
        raise AssertionError("Expected LLMTimeoutError")
