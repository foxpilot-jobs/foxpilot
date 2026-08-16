from career_agent.config import AppConfig
from career_agent.matching import match_job


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
