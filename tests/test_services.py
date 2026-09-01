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


def test_profile_generation_reuses_identical_resume(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    service = CareerService(config, user_id="user-a")
    with JobStore(config.database_path, user_id="user-a") as store:
        store.save_profile("Resume text", "resume.pdf", {"summary": "Existing"})
    monkeypatch.setattr(
        "career_agent.services.career.create_profile_from_text",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("LLM should not run")),
    )

    job_id = service.queue_profile_generation("Resume text", "renamed.pdf")
    service.run_profile_generation(job_id)

    job = service.get_background_job(job_id)
    assert job is not None
    assert job["status"] == "completed"
    assert job["result"] == {"profile": {"summary": "Existing"}}


def test_matching_queue_reuses_active_job(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.save_profile("Resume text", "resume.pdf", {"skills": ["Python"]})

    service = CareerService(config, user_id="user-a")
    first = service.queue_matching()
    second = service.queue_matching()

    assert first == second


def test_matching_queue_recovers_stale_job(tmp_path: Path) -> None:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    from career_agent.storage.database import background_jobs_table

    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.save_profile("Resume text", "resume.pdf", {"skills": ["Python"]})
        stale_time = datetime.now(UTC) - timedelta(minutes=15)
        store.create_background_job("old-stale-job", "matching")
        with store.engine.begin() as conn:
            conn.execute(
                update(background_jobs_table)
                .where(background_jobs_table.c.job_id == "old-stale-job")
                .values(status="running", updated_at=stale_time)
            )

    service = CareerService(config, user_id="user-a")
    new_job_id = service.queue_matching(max_stale_seconds=600)

    assert new_job_id != "old-stale-job"
    old_job = service.get_background_job("old-stale-job")
    assert old_job["status"] == "failed"
    assert old_job["error_class"] == "stale"


def test_scan_uses_saved_profile_and_persists_result(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.save_profile(
            "Resume text",
            "resume.pdf",
            {"current_or_recent_roles": ["Data Engineer"]},
        )

    calls = []
    monkeypatch.setattr(
        "career_agent.services.ingestion.fetch_configured_sources",
        lambda profile, user_id: calls.append((profile, user_id)) or 4,
    )
    service = CareerService(config, user_id="user-a")

    job_id = service.queue_scan()
    service.run_scan_job(job_id)

    # Ingestion runs without profile (shared corpus) but records the result
    assert calls == [(None, "system")]
    result = service.get_background_job(job_id)["result"]
    assert result["new_jobs"] == 4
    assert "ingestion_run_id" in result


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
    assert classify_job(
        {
            "source": "hackernews",
            "title": "Hiring thread mentioning a Software Engineer opportunity",
        },
        {"current_or_recent_roles": ["Software Engineer"]},
    ) == "REVIEW"


def test_get_profile_returns_default_resource_when_no_resume(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    service = CareerService(config, user_id="new-user-no-resume")
    profile = service.get_profile()
    assert profile == {
        "resume_filename": "",
        "profile": {},
        "created_at": None,
        "updated_at": None,
        "workspace_id": None,
    }
