from __future__ import annotations

from pathlib import Path

from career_agent.config import AppConfig
from career_agent.llm.base import LLMRateLimitError
from career_agent.services.career import CareerService
from career_agent.storage.database import JobStore, compute_preference_hash
from career_agent.work_arrangement import is_job_location_eligible
from filter_jobs import classify_job


def test_1_extracted_target_roles_populate_initial_preferences(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    with JobStore(database, user_id="user-init") as store:
        store.save_profile(
            "Resume text",
            "resume.pdf",
            {
                "summary": "Full Stack Dev",
                "target_roles": ["Software Engineer", "Data Engineer", "Full Stack Engineer", "Product Manager"],
            },
        )
        prefs = store.get_workspace_preferences()
        assert prefs["target_roles"] == ["Software Engineer", "Data Engineer", "Full Stack Engineer", "Product Manager"]
        assert prefs["work_arrangement"] == "any"
        assert prefs["preferred_locations"] == []


def test_2_and_3_user_can_remove_and_add_target_roles(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    with JobStore(database, user_id="user-edit") as store:
        store.save_profile(
            "Resume text",
            "resume.pdf",
            {"target_roles": ["Software Engineer", "Product Manager"]},
        )
        store.update_workspace_preferences(
            target_roles=["Software Engineer", "Backend Engineer"],
            work_arrangement="remote",
            preferred_locations=["Location A"],
        )
        prefs = store.get_workspace_preferences()
        assert prefs["target_roles"] == ["Software Engineer", "Backend Engineer"]
        assert "Product Manager" not in prefs["target_roles"]


def test_4_5_6_7_saved_preferences_authoritative_and_profile_intact(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    with JobStore(database, user_id="user-auth") as store:
        extracted_profile = {
            "summary": "Product leadership on Taskopus SaaS",
            "skills": ["Python", "Product Roadmap"],
            "projects": ["Taskopus - Built SaaS app"],
            "target_roles": ["Software Engineer", "Product Manager"],
        }
        store.save_profile("Resume text", "resume.pdf", extracted_profile)

        store.update_workspace_preferences(
            target_roles=["Software Engineer"],
            work_arrangement="any",
            preferred_locations=[],
        )

        db_prof = store.get_profile()["profile_json"]
        assert db_prof["target_roles"] == ["Software Engineer", "Product Manager"]
        assert "Taskopus" in db_prof["projects"][0]

        store.save_profile("Updated resume text", "resume_v2.pdf", extracted_profile)
        prefs_after = store.get_workspace_preferences()
        assert prefs_after["target_roles"] == ["Software Engineer"]

        pm_job = {"title": "Product Manager", "company": "SaaS Inc", "location": "Remote"}
        status = classify_job(pm_job, profile=extracted_profile, workspace_preferences=prefs_after)
        assert status == "OUT_OF_SCOPE"


def test_8_onsite_job_in_preferred_location_eligible() -> None:
    job = {"title": "Software Engineer", "work_type": "Onsite", "location": "Location A, Region 1"}
    assert is_job_location_eligible(job, "any", ["Location A", "Location B"]) is True


def test_9_onsite_job_outside_preferred_locations_out_of_scope() -> None:
    job = {"title": "Software Engineer", "work_type": "Onsite", "location": "Location C, Region 2"}
    assert is_job_location_eligible(job, "any", ["Location A", "Location B"]) is False


def test_10_hybrid_job_in_preferred_location_eligible() -> None:
    job = {"title": "Software Engineer", "work_type": "Hybrid", "location": "Location B, Region 1"}
    assert is_job_location_eligible(job, "hybrid", ["Location A", "Location B"]) is True


def test_11_hybrid_job_outside_preferred_locations_out_of_scope() -> None:
    job = {"title": "Software Engineer", "work_type": "Hybrid", "location": "Location C, Region 2"}
    assert is_job_location_eligible(job, "hybrid", ["Location A", "Location B"]) is False


def test_12_13_14_15_remote_jobs_never_restricted_by_company_hq_location() -> None:
    # Remote in preferred location
    job_12 = {"title": "Software Engineer", "work_type": "Remote", "location": "Location A"}
    assert is_job_location_eligible(job_12, "any", ["Location A"]) is True

    # Remote with unrelated company HQ metadata (Location B, candidate in Location A)
    job_hq = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B"}
    assert is_job_location_eligible(job_hq, "remote", ["Location A"]) is True
    assert is_job_location_eligible(job_hq, "any", ["Location A"]) is True

    # Remote with no location / missing location
    job_14 = {"title": "Software Engineer", "work_type": "Remote", "location": None}
    assert is_job_location_eligible(job_14, "any", ["Location A"]) is True

    # Remote with "Anywhere" / "Worldwide"
    job_15a = {"title": "Software Engineer", "work_type": "Remote", "location": "Anywhere"}
    assert is_job_location_eligible(job_15a, "any", ["Location A"]) is True


def test_explicit_remote_hq_vs_geographic_restriction_cases_1_to_7() -> None:
    # CASE 1: Work arrangement="any", preferred_locations=["Location A, Country A"], Remote job with location="Location B, Country B", description="Remote - anywhere" -> ELIGIBLE
    case1_job = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "Remote - anywhere"}
    assert is_job_location_eligible(case1_job, work_arrangement="any", preferred_locations=["Location A, Country A"]) is True

    # CASE 2: Work arrangement="any", preferred_locations=["Location A, Country A"], Remote job with location="Location B, Country B", description="Remote - Country B only" -> OUT_OF_SCOPE
    case2_job = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "Remote - Country B only"}
    assert is_job_location_eligible(case2_job, work_arrangement="any", preferred_locations=["Location A, Country A"]) is False

    # CASE 3: Work arrangement="remote", preferred_locations=["Location A, Country A"], Remote job with location="Location B, Country B", description="Remote - Country B only" -> OUT_OF_SCOPE
    case3_job = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "Remote - Country B only"}
    assert is_job_location_eligible(case3_job, work_arrangement="remote", preferred_locations=["Location A, Country A"]) is False

    # CASE 4: Work arrangement="remote", preferred_locations=["Location A, Country A"], Remote job with location="Location B, Country B", description="Fully remote, work from anywhere" -> ELIGIBLE
    case4_job = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "Fully remote, work from anywhere"}
    assert is_job_location_eligible(case4_job, work_arrangement="remote", preferred_locations=["Location A, Country A"]) is True

    # CASE 5: Work arrangement="remote", preferred_locations=["Location A, Country A"], Remote job with location="Location B, Country B", description="Remote position. Must reside in Country A." -> ELIGIBLE
    case5_job = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "Remote position. Must reside in Country A."}
    assert is_job_location_eligible(case5_job, work_arrangement="remote", preferred_locations=["Location A, Country A"]) is True

    # CASE 6: Work arrangement="remote", preferred_locations=["Location A, Country A"], Remote job with location="Location B, Country B", description="Remote position. Must reside in Country B." -> OUT_OF_SCOPE
    case6_job = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "Remote position. Must reside in Country B."}
    assert is_job_location_eligible(case6_job, work_arrangement="remote", preferred_locations=["Location A, Country A"]) is False

    # CASE 7: Work arrangement="any", preferred_locations=["Location A, Country A"], Remote job with location="Location B, Country B", description="Engineering role at tech company." (no restriction) -> ELIGIBLE
    case7_job = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "Engineering role at tech company."}
    assert is_job_location_eligible(case7_job, work_arrangement="any", preferred_locations=["Location A, Country A"]) is True


def test_audit_5_real_countries_generic_restriction_parsing() -> None:
    # 1. Japan ("Remote - Japan only")
    jp_job = {"title": "Backend Dev", "work_type": "Remote", "location": "San Francisco, CA", "description": "Remote - Japan only"}
    assert is_job_location_eligible(jp_job, "remote", ["Tokyo, Japan"]) is True
    assert is_job_location_eligible(jp_job, "remote", ["Toronto, Canada"]) is False

    # 2. Singapore ("Must reside in Singapore")
    sg_job = {"title": "DevOps Engineer", "work_type": "Remote", "location": "London, UK", "description": "Must reside in Singapore"}
    assert is_job_location_eligible(sg_job, "remote", ["Singapore"]) is True
    assert is_job_location_eligible(sg_job, "remote", ["Berlin, Germany"]) is False

    # 3. Ireland ("Remote - Ireland only")
    ie_job = {"title": "Software Engineer", "work_type": "Remote", "location": "New York, NY", "description": "Remote - Ireland only"}
    assert is_job_location_eligible(ie_job, "remote", ["Dublin, Ireland"]) is True
    assert is_job_location_eligible(ie_job, "remote", ["Sydney, Australia"]) is False

    # 4. Brazil ("Must reside in Brazil")
    br_job = {"title": "Data Engineer", "work_type": "Remote", "location": "Austin, TX", "description": "Must reside in Brazil"}
    assert is_job_location_eligible(br_job, "remote", ["São Paulo, Brazil"]) is True
    assert is_job_location_eligible(br_job, "remote", ["Toronto, Canada"]) is False

    # 5. France ("Remote - France only")
    fr_job = {"title": "Full Stack Dev", "work_type": "Remote", "location": "Seattle, WA", "description": "Remote - France only"}
    assert is_job_location_eligible(fr_job, "remote", ["Paris, France"]) is True
    assert is_job_location_eligible(fr_job, "remote", ["Tokyo, Japan"]) is False


def test_audit_extended_applicant_restriction_phrasings() -> None:
    # "Applicants must be located in Country A"
    job1 = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "Applicants must be located in Country A"}
    assert is_job_location_eligible(job1, "remote", ["Location A, Country A"]) is True
    assert is_job_location_eligible(job1, "remote", ["Location B, Country B"]) is False

    # "Available only in Country A"
    job2 = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "Position available only in Country A"}
    assert is_job_location_eligible(job2, "remote", ["Location A, Country A"]) is True
    assert is_job_location_eligible(job2, "remote", ["Location B, Country B"]) is False

    # "Open to candidates in Country A"
    job3 = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "Role open to candidates in Country A"}
    assert is_job_location_eligible(job3, "remote", ["Location A, Country A"]) is True
    assert is_job_location_eligible(job3, "remote", ["Location B, Country B"]) is False

    # "globally distributed"
    job4 = {"title": "Software Engineer", "work_type": "Remote", "location": "Location B, Country B", "description": "We are a globally distributed team hiring anywhere."}
    assert is_job_location_eligible(job4, "remote", ["Location A, Country A"]) is True


def test_16_multiple_preferred_locations_work() -> None:
    job = {"title": "Software Engineer", "work_type": "Onsite", "location": "Location C, Region 3"}
    assert is_job_location_eligible(job, "onsite", ["Location A", "Location B", "Location C"]) is True


def test_17_empty_preferred_locations_no_restriction() -> None:
    onsite = {"title": "Software Engineer", "work_type": "Onsite", "location": "Location A"}
    hybrid = {"title": "Software Engineer", "work_type": "Hybrid", "location": "Location B"}
    remote = {"title": "Software Engineer", "work_type": "Remote", "location": "Anywhere"}

    assert is_job_location_eligible(onsite, "any", []) is True
    assert is_job_location_eligible(hybrid, "hybrid", []) is True
    assert is_job_location_eligible(remote, "remote", []) is True


def test_18_19_work_arrangement_any_semantics() -> None:
    prefs = ["Location A", "Location B"]
    remote_anywhere = {"title": "Software Engineer", "work_type": "Remote", "location": "Anywhere"}
    onsite_loc_a = {"title": "Software Engineer", "work_type": "Onsite", "location": "Location A"}
    onsite_loc_c = {"title": "Software Engineer", "work_type": "Onsite", "location": "Location C"}

    assert is_job_location_eligible(remote_anywhere, "any", prefs) is True
    assert is_job_location_eligible(onsite_loc_a, "any", prefs) is True
    assert is_job_location_eligible(onsite_loc_c, "any", prefs) is False


def test_20_21_22_work_arrangement_explicit_modes() -> None:
    remote_job = {"title": "Software Engineer", "work_type": "Remote", "location": "Anywhere"}
    onsite_job = {"title": "Software Engineer", "work_type": "Onsite", "location": "Location A"}
    hybrid_job = {"title": "Software Engineer", "work_type": "Hybrid", "location": "Location A"}

    assert is_job_location_eligible(onsite_job, "remote", ["Location A"]) is False
    assert is_job_location_eligible(hybrid_job, "remote", ["Location A"]) is False
    assert is_job_location_eligible(remote_job, "remote", ["Location A"]) is True

    assert is_job_location_eligible(remote_job, "onsite", ["Location A"]) is False
    assert is_job_location_eligible(hybrid_job, "onsite", ["Location A"]) is False
    assert is_job_location_eligible(onsite_job, "onsite", ["Location A"]) is True

    assert is_job_location_eligible(remote_job, "hybrid", ["Location A"]) is False
    assert is_job_location_eligible(onsite_job, "hybrid", ["Location A"]) is False
    assert is_job_location_eligible(hybrid_job, "hybrid", ["Location A"]) is True


def test_23_unknown_location_onsite_handled_conservatively() -> None:
    onsite_no_loc = {"title": "Software Engineer", "work_type": "Onsite", "location": ""}
    assert is_job_location_eligible(onsite_no_loc, "any", ["Location A"]) is False


def test_24_location_matching_case_and_format_tolerant() -> None:
    job = {"title": "Software Engineer", "work_type": "Onsite", "location": "LOCATION A, REGION 1"}
    assert is_job_location_eligible(job, "onsite", ["location a"]) is True


def test_26_workspace_isolation(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    with JobStore(database, user_id="user-iso") as store:
        ws_a = store.create_workspace("Workspace A")["workspace_id"]
        ws_b = store.create_workspace("Workspace B")["workspace_id"]

        store.update_workspace_preferences(["Software Engineer"], "remote", ["Location A"], workspace_id=ws_a)
        store.update_workspace_preferences(["Data Engineer"], "onsite", ["Location B"], workspace_id=ws_b)

        p_a = store.get_workspace_preferences(workspace_id=ws_a)
        p_b = store.get_workspace_preferences(workspace_id=ws_b)

        assert p_a["target_roles"] == ["Software Engineer"]
        assert p_a["preferred_locations"] == ["Location A"]

        assert p_b["target_roles"] == ["Data Engineer"]
        assert p_b["preferred_locations"] == ["Location B"]


def test_27_28_29_30_match_cache_preference_hash(tmp_path: Path) -> None:
    database = tmp_path / "test.sqlite3"
    with JobStore(database, user_id="user-cache") as store:
        ws_id = store.create_workspace("Default")["workspace_id"]
        p1 = store.update_workspace_preferences(["Software Engineer"], "remote", ["Location A"], workspace_id=ws_id)
        h1 = compute_preference_hash(p1["target_roles"], p1["work_arrangement"], p1["preferred_locations"])

        job_id = store.upsert_job({"source": "t", "source_job_id": "j1", "title": "Software Engineer", "company": "C", "description": "D"})
        store.save_match(job_id, "jh1", "prov", "mod", {"match_score": 95}, preference_hash=h1, workspace_id=ws_id)

        assert store.get_match(job_id, preference_hash=h1, workspace_id=ws_id) is not None

        p2 = store.update_workspace_preferences(["Data Engineer"], "remote", ["Location A"], workspace_id=ws_id)
        h2 = compute_preference_hash(p2["target_roles"], p2["work_arrangement"], p2["preferred_locations"])
        assert h1 != h2
        assert store.get_match(job_id, preference_hash=h2, workspace_id=ws_id) is None

        p3 = store.update_workspace_preferences(["Software Engineer"], "remote", ["Location B"], workspace_id=ws_id)
        h3 = compute_preference_hash(p3["target_roles"], p3["work_arrangement"], p3["preferred_locations"])
        assert store.get_match(job_id, preference_hash=h3, workspace_id=ws_id) is None

        p4 = store.update_workspace_preferences(["Software Engineer"], "onsite", ["Location A"], workspace_id=ws_id)
        h4 = compute_preference_hash(p4["target_roles"], p4["work_arrangement"], p4["preferred_locations"])
        assert store.get_match(job_id, preference_hash=h4, workspace_id=ws_id) is None


def test_31_to_36_gemini_calls_and_429_protection(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(database_url=f"sqlite:///{tmp_path / 'gemini.sqlite3'}")
    service = CareerService(config, user_id="user-gemini")

    with service._store() as store:
        store.save_profile("Resume text", "resume.pdf", {"target_roles": ["Software Engineer"]})
        ws_prefs = store.update_workspace_preferences(["Software Engineer"], "remote", ["Location A"])

        pm_job = {"title": "Product Manager", "company": "Co", "location": "Remote", "description": "PM"}
        assert classify_job(pm_job, workspace_preferences=ws_prefs) == "OUT_OF_SCOPE"

        onsite_bad_loc = {"title": "Software Engineer", "work_type": "Onsite", "location": "Location B", "company": "Co", "description": "Dev"}
        assert classify_job(onsite_bad_loc, workspace_preferences=ws_prefs) == "OUT_OF_SCOPE"

        remote_no_loc = {"title": "Software Engineer", "work_type": "Remote", "location": None, "company": "Co", "description": "Dev"}
        assert classify_job(remote_no_loc, workspace_preferences=ws_prefs) == "TARGET"

        calls = []
        def mock_match_job(*args, **kwargs):
            calls.append(args)
            return {"match_score": 90, "recommendation": "APPLY"}

        monkeypatch.setattr("career_agent.services.career.match_job", mock_match_job)

        _ = store.upsert_job({"source": "g", "source_job_id": "swe1", "title": "Software Engineer", "company": "Co", "location": "Remote", "description": "Dev"})
        _ = service.run_matching()
        assert len(calls) == 1

        _ = service.run_matching()
        assert len(calls) == 1

        _ = store.upsert_job({"source": "g", "source_job_id": "swe2", "title": "Software Engineer", "company": "Co2", "location": "Remote", "description": "Dev2"})
        bg_job_id = service.queue_matching()
        def mock_429(*args, **kwargs):
            raise LLMRateLimitError("429 RESOURCE_EXHAUSTED", retry_after_seconds=60)

        monkeypatch.setattr("career_agent.services.career.match_job", mock_429)

        try:
            service.run_matching_job(bg_job_id)
        except Exception:  # noqa: BLE001, S110
            pass

        bg_job = store.get_background_job(bg_job_id)
        assert bg_job["status"] == "queued"
        assert bg_job["error_class"] == "retryable"
