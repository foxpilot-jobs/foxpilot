from pathlib import Path

from career_agent.config import AppConfig
from career_agent.services import CareerService
from career_agent.storage import JobStore


def test_run_matching_uses_user_profile_and_caches_results(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        job_id = store.upsert_job(
            {"source": "test", "source_job_id": "1", "title": "Data Engineer"}
        )
        store.set_relevance(job_id, "TARGET")
        store.save_profile("Resume text", "resume.pdf", {"skills": ["Python"]})

    class Provider:
        pass

    calls = []
    monkeypatch.setattr("career_agent.services.career.create_provider", lambda _config: Provider())
    monkeypatch.setattr(
        "career_agent.services.career.match_job",
        lambda _config, profile, job, provider: calls.append((profile, job["job_id"]))
        or {
            "match_score": 85,
            "recommendation": "APPLY",
            "reasons": ["Relevant role"],
            "matching_skills": ["Python"],
            "missing_skills": [],
            "experience_match": "Strong",
            "concerns": [],
        },
    )

    service = CareerService(config, user_id="user-a")
    first = service.run_matching()
    second = service.run_matching()

    assert first == {"total": 1, "analyzed": 1, "skipped": 0, "failed": 0}
    assert second == {"total": 1, "analyzed": 0, "skipped": 1, "failed": 0}
    assert calls == [({"skills": ["Python"]}, job_id)]
