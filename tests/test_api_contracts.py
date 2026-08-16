from pathlib import Path

from fastapi.testclient import TestClient

from career_agent.config import AppConfig
from career_agent.storage import JobStore
from services.api.app import create_app


def test_web_api_contracts_for_jobs_matches_profile_and_background_job(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        job_id = store.upsert_job(
            {
                "source": "test",
                "source_job_id": "1",
                "title": "Data Engineer",
                "company": "Example",
            }
        )
        store.set_relevance(job_id, "TARGET")
        store.save_match(
            job_id,
            "hash",
            "test-provider",
            "test-model",
            {
                "match_score": 88,
                "recommendation": "APPLY",
                "reasons": ["Relevant"],
                "matching_skills": ["Python"],
                "missing_skills": [],
                "experience_match": "Strong",
                "concerns": [],
            },
        )
        store.save_profile("Resume text", "resume.pdf", {"summary": "Engineer"})
        store.create_background_job("job-status", "matching")

    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    job = client.get("/api/v1/jobs").json()[0]
    match = client.get("/api/v1/matches").json()[0]
    profile = client.get("/api/v1/profile").json()
    background_job = client.get("/api/v1/profile/jobs/job-status").json()

    assert {"job_id", "title", "company", "source"} <= job.keys()
    assert {"job_id", "match"} <= match.keys()
    assert {"resume_filename", "profile", "created_at", "updated_at"} <= profile.keys()
    assert {"job_id", "kind", "status", "result", "error"} <= background_job.keys()
