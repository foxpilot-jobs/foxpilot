from __future__ import annotations

from pathlib import Path

from career_agent.config import AppConfig
from career_agent.matching import build_match_prompt
from career_agent.services.career import CareerService
from career_agent.storage.database import JobStore, compute_preference_hash
from career_agent.work_arrangement import is_job_location_eligible
from filter_jobs import classify_job, is_target_role_compatible


def test_preferences_save_and_load(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    with JobStore(database, user_id="user-1") as store:
        prefs = store.get_workspace_preferences()
        assert prefs["target_roles"] == []
        assert prefs["work_arrangement"] == "any"
        assert prefs["preferred_locations"] == []

        updated = store.update_workspace_preferences(
            target_roles=["Software Engineer", "Data Engineer"],
            work_arrangement="remote",
            preferred_locations=["Hyderabad", "Bengaluru"],
        )
        assert updated["target_roles"] == ["Software Engineer", "Data Engineer"]
        assert updated["work_arrangement"] == "remote"
        assert updated["preferred_locations"] == ["Hyderabad", "Bengaluru"]

        loaded = store.get_workspace_preferences()
        assert loaded == updated


def test_preferences_workspace_isolation(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    with JobStore(database, user_id="user-1") as store:
        ws_a = store.create_workspace("Workspace A")["workspace_id"]
        ws_b = store.create_workspace("Workspace B")["workspace_id"]

        store.update_workspace_preferences(
            target_roles=["Software Engineer"],
            work_arrangement="remote",
            preferred_locations=["Hyderabad"],
            workspace_id=ws_a,
        )
        store.update_workspace_preferences(
            target_roles=["Product Manager"],
            work_arrangement="onsite",
            preferred_locations=["Bengaluru"],
            workspace_id=ws_b,
        )

        prefs_a = store.get_workspace_preferences(workspace_id=ws_a)
        prefs_b = store.get_workspace_preferences(workspace_id=ws_b)

        assert prefs_a["target_roles"] == ["Software Engineer"]
        assert prefs_a["work_arrangement"] == "remote"
        assert prefs_a["preferred_locations"] == ["Hyderabad"]

        assert prefs_b["target_roles"] == ["Product Manager"]
        assert prefs_b["work_arrangement"] == "onsite"
        assert prefs_b["preferred_locations"] == ["Bengaluru"]


def test_target_roles_add_and_remove(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    with JobStore(database, user_id="user-1") as store:
        store.update_workspace_preferences(
            target_roles=["Software Engineer", "Data Engineer"],
            work_arrangement="any",
            preferred_locations=[],
        )
        store.update_workspace_preferences(
            target_roles=["Software Engineer"],
            work_arrangement="any",
            preferred_locations=[],
        )
        loaded = store.get_workspace_preferences()
        assert loaded["target_roles"] == ["Software Engineer"]


def test_preference_hash_deterministic() -> None:
    h1 = compute_preference_hash(["Software Engineer", "Data Engineer"], "remote", ["Hyderabad", "Bengaluru"])
    h2 = compute_preference_hash(["data engineer", "SOFTWARE ENGINEER "], "REMOTE", [" BENGALURU", "hyderabad "])
    assert h1 == h2

    h3 = compute_preference_hash(["Software Engineer"], "remote", ["Hyderabad"])
    assert h1 != h3


def test_target_role_compatibility_matching() -> None:
    roles = ["Software Engineer"]
    assert is_target_role_compatible("Software Engineer", roles) is True
    assert is_target_role_compatible("Senior Software Engineer", roles) is True
    assert is_target_role_compatible("Software Engineer II", roles) is True
    assert is_target_role_compatible("Staff Software Engineer", roles) is True
    assert is_target_role_compatible("Backend Software Engineer", roles) is True
    assert is_target_role_compatible("Frontend Software Engineer", roles) is True
    assert is_target_role_compatible("Full Stack Software Engineer", roles) is True
    assert is_target_role_compatible("Software Development Engineer", roles) is True

    # Role boundary checks
    assert is_target_role_compatible("Product Manager", roles) is False
    assert is_target_role_compatible("Product Designer", roles) is False
    assert is_target_role_compatible("Data Scientist", roles) is False
    assert is_target_role_compatible("Data Analyst", roles) is False
    assert is_target_role_compatible("Marketing Manager", roles) is False


def test_data_engineer_compatibility_boundary() -> None:
    roles = ["Data Engineer"]
    assert is_target_role_compatible("Data Engineer", roles) is True
    assert is_target_role_compatible("Lead Data Engineer", roles) is True
    assert is_target_role_compatible("Data Scientist", roles) is False
    assert is_target_role_compatible("Data Analyst", roles) is False


def test_resume_taskopus_project_does_not_make_product_manager_target() -> None:
    profile = {
        "summary": "Full Stack Engineer with project management experience",
        "skills": ["Python", "Product Management", "Agile"],
        "projects": ["Taskopus - Led product strategy and architecture"],
        "target_roles": ["Software Engineer"],
    }
    ws_prefs = {
        "target_roles": ["Software Engineer"],
        "work_arrangement": "any",
        "preferred_locations": [],
    }
    pm_job = {
        "title": "Product Manager",
        "company": "Tech Corp",
        "location": "Hyderabad",
        "description": "Lead product management for Taskopus-like platform",
    }
    swe_job = {
        "title": "Senior Software Engineer",
        "company": "Tech Corp",
        "location": "Hyderabad",
        "description": "Python backend development",
    }

    assert classify_job(pm_job, profile, workspace_preferences=ws_prefs) == "OUT_OF_SCOPE"
    assert classify_job(swe_job, profile, workspace_preferences=ws_prefs) == "TARGET"


def test_location_filtering_remote_only() -> None:
    onsite_job = {
        "title": "Software Engineer",
        "location": "Bengaluru",
        "work_type": "Onsite",
        "description": "Must work in-office 5 days a week in Bengaluru",
    }
    remote_job = {
        "title": "Software Engineer",
        "location": "Remote - India",
        "work_type": "Remote",
        "description": "100% remote position",
    }

    assert is_job_location_eligible(onsite_job, work_arrangement="remote") is False
    assert is_job_location_eligible(remote_job, work_arrangement="remote") is True


def test_location_filtering_hyderabad_onsite_excludes_bengaluru() -> None:
    hyd_job = {
        "title": "Software Engineer",
        "location": "Hyderabad",
        "work_type": "Onsite",
        "description": "On-site office in Gachibowli, Hyderabad",
    }
    blr_job = {
        "title": "Software Engineer",
        "location": "Bengaluru",
        "work_type": "Onsite",
        "description": "On-site office in Indiranagar, Bengaluru",
    }

    assert is_job_location_eligible(hyd_job, work_arrangement="onsite", preferred_locations=["Hyderabad"]) is True
    assert is_job_location_eligible(blr_job, work_arrangement="onsite", preferred_locations=["Hyderabad"]) is False


def test_location_filtering_ambiguous_handled_conservatively() -> None:
    ambiguous_job = {
        "title": "Software Engineer",
        "location": "",
        "description": "Great engineering opportunities",
    }
    assert is_job_location_eligible(ambiguous_job, work_arrangement="onsite", preferred_locations=["Hyderabad"]) is False


def test_cache_invalidation_on_target_role_change(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    config = AppConfig(database_url=f"sqlite:///{database}")
    user_id = "user-cache-test"
    service = CareerService(config, user_id=user_id)

    with service._store() as store:
        store.save_profile(
            resume_text="Software engineer resume",
            resume_filename="resume.pdf",
            profile={"target_roles": ["Software Engineer"]},
        )
        job_id = store.upsert_job({
            "source": "linkedin",
            "source_job_id": "job-cache-1",
            "title": "Software Engineer",
            "company": "Acme",
            "location": "Remote",
            "description": "Python developer role",
        })

        # Save match with preference hash A
        store.update_workspace_preferences(["Software Engineer"], "any", [])
        ws_prefs_a = store.get_workspace_preferences()
        hash_a = compute_preference_hash(ws_prefs_a["target_roles"], ws_prefs_a["work_arrangement"], ws_prefs_a["preferred_locations"])
        store.save_match(job_id, "jobhash123", "gemini", "gemini-3.5-flash-lite", {"match_score": 85}, preference_hash=hash_a)

        # Match should be found when querying with hash_a
        assert store.get_match(job_id, preference_hash=hash_a) is not None

        # Change preference to Data Engineer
        store.update_workspace_preferences(["Data Engineer"], "any", [])
        ws_prefs_b = store.get_workspace_preferences()
        hash_b = compute_preference_hash(ws_prefs_b["target_roles"], ws_prefs_b["work_arrangement"], ws_prefs_b["preferred_locations"])
        assert hash_a != hash_b

        # Match query with hash_b MUST return None (cache miss!)
        assert store.get_match(job_id, preference_hash=hash_b) is None


def test_gemini_prompt_contains_explicit_preferences() -> None:
    profile = {"skills": ["Python", "SQL"], "summary": "Senior developer"}
    job = {"title": "Software Engineer", "company": "Acme", "description": "Backend dev"}
    ws_prefs = {
        "target_roles": ["Software Engineer", "Backend Engineer"],
        "work_arrangement": "remote",
        "preferred_locations": ["Hyderabad"],
    }

    prompt = build_match_prompt(profile, job, workspace_preferences=ws_prefs)
    assert "USER'S TARGET ROLES (Explicit workspace preferences):" in prompt
    assert "Software Engineer" in prompt
    assert "USER'S LOCATION PREFERENCES:" in prompt
    assert "Work Arrangement: remote" in prompt
    assert "Hyderabad" in prompt
    assert "The candidate profile describes qualifications and experience. It does not define the candidate's desired role." in prompt


def test_api_workspace_preferences_endpoints(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    monkeypatch.delenv("FOXPILOT_API_TOKEN", raising=False)
    from fastapi.testclient import TestClient

    from services.api.app import create_app

    database = tmp_path / "api_test.sqlite3"
    config = AppConfig(database_url=f"sqlite:///{database}")
    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    # Put preferences
    res = client.put(
        "/api/v1/workspace/preferences",
        json={
            "target_roles": ["Software Engineer"],
            "work_arrangement": "remote",
            "preferred_locations": ["Hyderabad"],
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["target_roles"] == ["Software Engineer"]
    assert data["work_arrangement"] == "remote"
    assert data["preferred_locations"] == ["Hyderabad"]

    # Get preferences
    get_res = client.get("/api/v1/workspace/preferences")
    assert get_res.status_code == 200
    assert get_res.json() == data

    # Validation error test (422)
    err_res = client.put(
        "/api/v1/workspace/preferences",
        json={
            "target_roles": "invalid_type",
            "work_arrangement": "invalid_arrangement",
            "preferred_locations": [],
        },
    )
    assert err_res.status_code == 422


def test_legacy_workspace_defaults_regression(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    monkeypatch.delenv("FOXPILOT_API_TOKEN", raising=False)
    from fastapi.testclient import TestClient

    from services.api.app import create_app

    database = tmp_path / "legacy_test.sqlite3"
    config = AppConfig(database_url=f"sqlite:///{database}")
    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    # Initial GET on legacy/new workspace must return 200 OK and default preferences
    res = client.get("/api/v1/workspace/preferences")
    assert res.status_code == 200
    data = res.json()
    assert data["target_roles"] == []
    assert data["work_arrangement"] == "any"
    assert data["preferred_locations"] == []

