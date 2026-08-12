from career_agent.llm.base import LLMError, parse_json_response


def test_parse_json_response_accepts_json_fence() -> None:
    assert parse_json_response('```json\n{"ok": true}\n```') == {"ok": True}


def test_parse_json_response_rejects_non_object() -> None:
    try:
        parse_json_response("[]")
    except LLMError as error:
        assert "JSON object" in str(error)
    else:
        raise AssertionError("Expected LLMError")
