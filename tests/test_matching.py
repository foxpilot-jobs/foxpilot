from career_agent.config import AppConfig
from career_agent.matching import build_match_prompt, match_job


class RetryingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def complete_json(self, prompt: str, response_schema=None) -> dict:
        self.calls += 1
        if self.calls == 1:
            return {"match_score": 80}
        return {
            "match_score": 80,
            "recommendation": "CONSIDER",
            "reasons": ["Relevant experience"],
            "matching_skills": ["Python"],
            "missing_skills": [],
            "experience_match": "reasonable",
            "concerns": [],
        }


def test_matching_retries_schema_violation() -> None:
    provider = RetryingProvider()
    result = match_job(
        AppConfig(),
        {"skills": ["Python"]},
        {"title": "Data Engineer", "description": "Python"},
        provider=provider,
    )
    assert result["recommendation"] == "CONSIDER"
    assert provider.calls == 2


def test_match_prompt_is_compact_and_bounded() -> None:
    prompt = build_match_prompt(
        {"skills": ["Python"]},
        {
            "title": "Data Engineer",
            "company": "Example",
            "description": "x" * 20_000,
            "source_payload": {"large": "private source payload"},
        },
    )

    assert "[description truncated]" in prompt
    assert "private source payload" not in prompt
