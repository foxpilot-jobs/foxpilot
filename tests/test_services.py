from pathlib import Path

from career_agent.config import AppConfig
from career_agent.services import CareerService
from career_agent.storage import JobStore
from filter_jobs import classify_job


def test_run_matching_uses_user_profile_and_caches_results(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        job_id = store.upsert_job(
            {"source": "test", "source_job_id": "1", "title": "Data Engineer"}
        )
        store.set_relevance(job_id, "TARGET")
        store.save_profile(
            "Resume text",
            "resume.pdf",
            {"skills": ["Python"], "target_roles": ["Data Engineer"]},
        )

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
    progress = []
    first = service.run_matching(progress=progress.append)
    second = service.run_matching()

    assert first == {"total": 1, "analyzed": 1, "skipped": 0, "failed": 0}
    assert second == {"total": 1, "analyzed": 0, "skipped": 1, "failed": 0}
    assert calls == [
        ({"skills": ["Python"], "target_roles": ["Data Engineer"]}, job_id)
    ]
    assert progress[-1] == {"processed": 1, "total": 1}


def test_profile_generation_updates_background_job(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    service = CareerService(config, user_id="user-a")
    monkeypatch.setattr(
        "career_agent.services.career.create_profile_from_text",
        lambda *_args, **_kwargs: {"summary": "Data engineer"},
    )

    job_id = service.queue_profile_generation("Resume text", "resume.pdf")
    service.run_profile_generation(job_id)

    job = service.get_background_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job["result"] == {"profile": {"summary": "Data engineer"}}


def test_matching_queue_reuses_active_job(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.save_profile("Resume text", "resume.pdf", {"skills": ["Python"]})

    service = CareerService(config, user_id="user-a")
    first = service.queue_matching()
    second = service.queue_matching()

    assert first == second


def test_profile_aware_relevance_rejects_generic_roles_without_profile_fit() -> None:
    profile = {
        "target_roles": ["Frontend Engineer"],
        "current_or_recent_roles": ["Software Engineer"],
        "skills": ["React", "TypeScript"],
    }

    assert classify_job(
        {
            "title": "Senior Frontend Engineer",
            "description": "Build React and TypeScript products.",
        },
        profile,
    ) == "TARGET"
    assert classify_job(
        {
            "title": "Data Engineer",
            "description": "Build data pipelines with Spark and SQL.",
        },
        profile,
    ) == "REVIEW"
    assert classify_job(
        {
            "title": "Solutions Architect",
            "description": "Work with AWS, Python, and SQL customers.",
        },
        {
            "current_or_recent_roles": ["Data Engineer"],
            "skills": {"data_engineering": ["Python", "SQL"]},
        },
    ) == "REVIEW"
