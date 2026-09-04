"""Regression tests for Gemini 429 rate-limit handling, backoff, and fallback retries."""

from __future__ import annotations

import pytest

from career_agent.config import AppConfig
from career_agent.llm import LLMError, LLMProvider, LLMRateLimitError
from career_agent.matching import match_job
from career_agent.profile import create_profile_from_text
from career_agent.services import CareerService
from career_agent.storage import JobStore


class MockRateLimitProvider(LLMProvider):
    def __init__(self) -> None:
        self.call_count = 0

    def complete_json(self, prompt: str, response_schema=None):
        self.call_count += 1
        raise LLMRateLimitError("Gemini request failed: 429 RESOURCE_EXHAUSTED: Quota exceeded")


class MockSchemaErrorProvider(LLMProvider):
    def __init__(self) -> None:
        self.call_count = 0

    def complete_json(self, prompt: str, response_schema=None):
        self.call_count += 1
        if self.call_count == 1:
            raise LLMError("The model returned invalid JSON: Expecting value: line 1 column 1 (char 0)")
        return {
            "summary": "Software Engineer",
            "years_of_experience": 5,
            "current_or_recent_roles": ["Engineer"],
            "skills": ["Python"],
            "programming_languages": ["Python"],
            "data_and_ai_tools": [],
            "cloud_and_infrastructure": [],
            "databases": [],
            "analytics_and_bi_tools": [],
            "target_roles": ["Senior Engineer"],
            "target_locations": ["Remote"],
            "work_arrangement_preferences": ["Remote"],
            "salary_expectation": None,
            "industry_preferences": [],
            "industries": [],
            "education": [],
            "certifications": [],
            "projects": [],
        }


class MockMatchingSchemaErrorProvider(LLMProvider):
    def __init__(self) -> None:
        self.call_count = 0

    def complete_json(self, prompt: str, response_schema=None):
        self.call_count += 1
        if self.call_count == 1:
            raise LLMError("Invalid schema format")
        return {
            "match_score": 85,
            "recommendation": "APPLY",
            "reasons": ["Good fit"],
            "matching_skills": ["Python"],
            "missing_skills": [],
            "experience_match": "5 years",
            "concerns": [],
            "gap_analysis": [],
        }


def test_429_profile_generation_single_request_per_attempt(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path, database_url=f"sqlite:///{tmp_path}/test.db")
    provider = MockRateLimitProvider()

    with pytest.raises(LLMRateLimitError):
        create_profile_from_text(config, "Resume text...", provider=provider, persist=False)

    # Must make ONLY ONE call when a 429 occurs (no immediate fallback retry)
    assert provider.call_count == 1


def test_schema_json_errors_receive_fallback_retry(tmp_path) -> None:
    config = AppConfig(data_dir=tmp_path, database_url=f"sqlite:///{tmp_path}/test.db")
    
    # Profile generation schema error receives fallback retry
    profile_provider = MockSchemaErrorProvider()
    profile = create_profile_from_text(config, "Resume text...", provider=profile_provider, persist=False)
    assert profile_provider.call_count == 2
    assert profile["summary"] == "Software Engineer"

    # Matching schema error receives fallback retry
    matching_provider = MockMatchingSchemaErrorProvider()
    dummy_job = {
        "job_id": "job_1",
        "title": "Engineer",
        "company": "Tech Corp",
        "location": "Remote",
        "url": "https://example.com",
        "description": "Python job",
    }
    match = match_job(config, profile, dummy_job, provider=matching_provider)
    assert matching_provider.call_count == 2
    assert match["match_score"] == 85


def test_429_matching_run_halts_immediately_and_requeues(tmp_path, monkeypatch) -> None:
    db_url = f"sqlite:///{tmp_path}/test_matching.db"
    config = AppConfig(data_dir=tmp_path, database_url=db_url)
    store = JobStore(db_url, user_id="rate_limit_user")

    # 1. Setup profile and 3 target jobs
    store.save_profile(
        resume_text="Developer",
        resume_filename="resume.pdf",
        profile={
            "summary": "Python Developer",
            "skills": ["Python"],
            "programming_languages": ["Python"],
            "target_roles": ["Engineer"],
        },
    )
    store.bulk_upsert_jobs([
        {
            "source": "test",
            "source_job_id": "1",
            "title": "Senior Engineer",
            "company": "Acme",
            "location": "Remote",
            "description": "Python required",
        },
        {
            "source": "test",
            "source_job_id": "2",
            "title": "Lead Engineer",
            "company": "Beta",
            "location": "Remote",
            "description": "Python required",
        },
        {
            "source": "test",
            "source_job_id": "3",
            "title": "Principal Engineer",
            "company": "Gamma",
            "location": "Remote",
            "description": "Python required",
        },
    ])

    service = CareerService(config, user_id="rate_limit_user")
    job_id = service.queue_matching()

    rate_limit_provider = MockRateLimitProvider()
    monkeypatch.setattr(
        "career_agent.services.career.create_provider",
        lambda _cfg: rate_limit_provider,
    )

    # 2. Run matching job – should fail on the FIRST 429 and halt loop immediately
    service.run_matching_job(job_id)

    # Exactly 1 LLM call attempted across all 3 jobs (loop halted after 1st 429)
    assert rate_limit_provider.call_count == 1

    # 3. Check background job status – must be 'queued' with 'retryable' error_class
    bg_job = store.get_background_job(job_id)
    assert bg_job["status"] == "queued"
    assert bg_job["error_class"] == "retryable"
    assert bg_job["lease_expires_at"] is not None


def test_successful_matching_and_cache_behavior_unchanged(tmp_path, monkeypatch) -> None:
    db_url = f"sqlite:///{tmp_path}/test_cache.db"
    config = AppConfig(data_dir=tmp_path, database_url=db_url)
    store = JobStore(db_url, user_id="cache_user")

    store.save_profile(
        resume_text="Developer",
        resume_filename="resume.pdf",
        profile={
            "summary": "Python Developer",
            "skills": ["Python"],
            "target_roles": ["Engineer"],
        },
    )
    store.bulk_upsert_jobs([
        {
            "source": "test",
            "source_job_id": "100",
            "title": "Software Engineer",
            "company": "Delta",
            "location": "Remote",
            "description": "Python required",
        }
    ])

    call_counter = {"count": 0}

    class MockSuccessProvider(LLMProvider):
        def complete_json(self, prompt: str, response_schema=None):
            call_counter["count"] += 1
            return {
                "match_score": 90,
                "recommendation": "APPLY",
                "reasons": ["Matches skills"],
                "matching_skills": ["Python"],
                "missing_skills": [],
                "experience_match": "Good match",
                "concerns": [],
                "gap_analysis": [],
            }

    success_provider = MockSuccessProvider()
    monkeypatch.setattr(
        "career_agent.services.career.create_provider",
        lambda _cfg: success_provider,
    )

    service = CareerService(config, user_id="cache_user")

    # Run 1: Should analyze job (1 LLM call)
    res1 = service.run_matching()
    assert res1["analyzed"] == 1
    assert res1["skipped"] == 0
    assert call_counter["count"] == 1

    # Run 2: Cache hit! Should skip job (0 LLM calls)
    res2 = service.run_matching()
    assert res2["analyzed"] == 0
    assert res2["skipped"] == 1
    assert call_counter["count"] == 1  # Unchanged!
