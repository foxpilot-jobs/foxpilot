import pytest

from career_agent.storage.database import JobStore


@pytest.fixture
def store(tmp_path):
    db_path = tmp_path / "test_workspace_isolation.db"
    return JobStore(db_path, user_id="user_test_isolation")


def test_workspace_profile_isolation_and_scoping(store):
    # 1. Existing default profile creation
    store.save_profile(
        resume_text="Default Resume Content for Software Engineer",
        resume_filename="default_resume.pdf",
        profile={"summary": "Default profile summary", "skills": ["Python", "SQL"]},
    )
    default_profile = store.get_profile()
    assert default_profile is not None
    assert default_profile["resume_filename"] == "default_resume.pdf"
    assert default_profile["profile_json"]["summary"] == "Default profile summary"
    default_ws_id = default_profile["workspace_id"]

    # 2. Creating a new 'ai' workspace and saving a profile in 'ai'
    ai_ws = store.create_workspace(name="ai")
    ai_ws_id = ai_ws["workspace_id"]
    assert ai_ws_id != default_ws_id

    # Switch to 'ai' workspace
    store.switch_workspace(ai_ws_id)

    # Before saving profile in 'ai', get_profile() should return None
    assert store.get_profile() is None

    store.save_profile(
        resume_text="AI Resume Content for Machine Learning Engineer",
        resume_filename="ai_resume.pdf",
        profile={"summary": "AI profile summary", "skills": ["PyTorch", "LLMs"]},
    )
    ai_profile = store.get_profile()
    assert ai_profile is not None
    assert ai_profile["workspace_id"] == ai_ws_id
    assert ai_profile["resume_filename"] == "ai_resume.pdf"
    assert ai_profile["profile_json"]["summary"] == "AI profile summary"

    # 3. Uploading a second resume to 'ai' updates the existing 'ai' profile (does not duplicate row)
    store.save_profile(
        resume_text="Updated AI Resume Content v2",
        resume_filename="ai_resume_v2.pdf",
        profile={"summary": "Updated AI summary v2", "skills": ["PyTorch", "LLMs", "RAG"]},
    )
    updated_ai_profile = store.get_profile()
    assert updated_ai_profile["resume_filename"] == "ai_resume_v2.pdf"
    assert updated_ai_profile["profile_json"]["summary"] == "Updated AI summary v2"
    assert updated_ai_profile["workspace_id"] == ai_ws_id

    # 4. Switching back to Default returns the Default profile
    store.switch_workspace(default_ws_id)
    switched_default_profile = store.get_profile()
    assert switched_default_profile is not None
    assert switched_default_profile["workspace_id"] == default_ws_id
    assert switched_default_profile["resume_filename"] == "default_resume.pdf"
    assert switched_default_profile["profile_json"]["summary"] == "Default profile summary"


def test_background_jobs_workspace_scoping_and_isolation(store):
    # Setup Default workspace profile
    store.save_profile(
        resume_text="Default Resume",
        resume_filename="default.pdf",
        profile={"summary": "Default profile"},
    )
    workspaces = store.list_workspaces()
    default_ws = next(ws for ws in workspaces if ws["is_active"])

    # Create background job in Default workspace
    job_id_default = "job_default_123"
    store.create_background_job(job_id_default, "matching")

    job_default = store.get_background_job(job_id_default)
    assert job_default["workspace_id"] == default_ws["workspace_id"]

    # Switch to 'ai' workspace
    ai_ws = store.create_workspace(name="ai")
    store.switch_workspace(ai_ws["workspace_id"])
    store.save_profile(
        resume_text="AI Resume",
        resume_filename="ai.pdf",
        profile={"summary": "AI profile"},
    )

    # Active job query in 'ai' workspace should NOT return Default workspace's job
    active_job_in_ai = store.get_active_background_job("matching")
    assert active_job_in_ai is None

    # Create background job in 'ai' workspace
    job_id_ai = "job_ai_456"
    store.create_background_job(job_id_ai, "matching")

    active_job_in_ai = store.get_active_background_job("matching")
    assert active_job_in_ai is not None
    assert active_job_in_ai["job_id"] == job_id_ai
    assert active_job_in_ai["workspace_id"] == ai_ws["workspace_id"]

    # Switching back to Default returns Default workspace's job
    store.switch_workspace(default_ws["workspace_id"])
    active_job_in_default = store.get_active_background_job("matching")
    assert active_job_in_default is not None
    assert active_job_in_default["job_id"] == job_id_default
    assert active_job_in_default["workspace_id"] == default_ws["workspace_id"]


def test_matches_and_applications_workspace_isolation(store):
    # 1. Create a global job accessible by all workspaces
    shared_job_id = "test_shared_job_123"
    store.bulk_upsert_jobs(
        [
            {
                "source": "test",
                "source_job_id": "shared_job_123",
                "title": "Senior AI Staff Engineer",
                "company": "DeepMind",
                "location": "Remote",
                "description": "Building next-gen AI coding assistants",
            }
        ]
    )

    # 2. Setup Default workspace
    store.save_profile(
        resume_text="Software Engineer Resume",
        resume_filename="swe.pdf",
        profile={"summary": "Backend SWE"},
    )
    workspaces = store.list_workspaces()
    default_ws = next(ws for ws in workspaces if ws["is_active"])

    # Save match and application in Default
    store.save_match(
        job_id=shared_job_id,
        job_hash="hash_default",
        provider="gemini",
        model="gemini-3.5-flash-lite",
        result={"match_score": 95, "recommendation": "APPLY"},
    )
    store.save_application(job_id=shared_job_id, status="applied", notes="Applied on site")

    default_matches = store.list_matches()
    assert default_matches["total"] == 1
    assert default_matches["items"][0]["match"]["match_score"] == 95

    default_apps = store.list_applications()
    assert default_apps["total"] == 1
    assert default_apps["items"][0]["status"] == "applied"

    # 3. Create and switch to custom 'ai' workspace
    ai_ws = store.create_workspace(name="ai")
    store.switch_workspace(ai_ws["workspace_id"])

    # In 'ai', list_matches and list_applications must be completely isolated (0 items)
    ai_matches_empty = store.list_matches()
    assert ai_matches_empty["total"] == 0

    ai_apps_empty = store.list_applications()
    assert ai_apps_empty["total"] == 0

    # Save profile, match, and application for the SAME global job in 'ai'
    store.save_profile(
        resume_text="AI Research Scientist Resume",
        resume_filename="ai.pdf",
        profile={"summary": "AI Researcher"},
    )
    store.save_match(
        job_id=shared_job_id,
        job_hash="hash_ai",
        provider="gemini",
        model="gemini-3.5-flash-lite",
        result={"match_score": 65, "recommendation": "CONSIDER"},
    )
    store.save_application(job_id=shared_job_id, status="interviewing", notes="Round 1 interview")

    ai_matches = store.list_matches()
    assert ai_matches["total"] == 1
    assert ai_matches["items"][0]["match"]["match_score"] == 65

    ai_apps = store.list_applications()
    assert ai_apps["total"] == 1
    assert ai_apps["items"][0]["status"] == "interviewing"

    # 4. Switch back to Default workspace and verify complete isolation
    store.switch_workspace(default_ws["workspace_id"])

    default_matches_restored = store.list_matches()
    assert default_matches_restored["total"] == 1
    assert default_matches_restored["items"][0]["match"]["match_score"] == 95

    default_apps_restored = store.list_applications()
    assert default_apps_restored["total"] == 1
    assert default_apps_restored["items"][0]["status"] == "applied"
