from __future__ import annotations

from career_agent.work_arrangement import parse_work_arrangement
from filter_jobs import profile_matches_job


def test_remote_india() -> None:
    job = {"title": "Backend Engineer", "location": "Remote - India", "description": "Python API role."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.is_india_eligible is True
    assert "India" in wa.remote_countries
    assert "India eligible" in wa.display_label


def test_remote_worldwide() -> None:
    job = {"title": "Full Stack Engineer", "location": "Remote - Worldwide", "description": "Work from anywhere in the world."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.remote_scope == "worldwide"
    assert wa.is_india_eligible is True
    assert "Worldwide" in wa.display_label


def test_remote_asia() -> None:
    job = {"title": "DevOps Engineer", "location": "Remote (APAC / Asia)", "description": "Remote within Asia."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.is_india_eligible is True
    assert "Asia" in wa.remote_regions
    assert "Asia" in wa.display_label


def test_remote_us_only() -> None:
    job = {"title": "Software Engineer", "location": "Remote - US Only", "description": "Must be based in the United States."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.is_india_eligible is False
    assert "United States" in wa.remote_countries
    assert "US only" in wa.display_label


def test_remote_germany_only() -> None:
    job = {"title": "Data Architect", "location": "Remote - Germany", "description": "Remote position within Germany."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.is_india_eligible is False
    assert "Germany" in wa.remote_countries
    assert "Germany" in wa.display_label


def test_hybrid_germany() -> None:
    job = {"title": "Consultant Data & Analytics", "location": "Hybrid - München, Germany", "description": "Hybrid 2 days in office."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "hybrid"
    assert wa.is_india_eligible is False
    assert "Germany" in wa.remote_countries or "München" in wa.display_label
    assert "Hybrid" in wa.display_label


def test_onsite_germany() -> None:
    job = {"title": "Data Engineer", "location": "On-site - Berlin, Germany", "description": "In-office role in Berlin."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "onsite"
    assert wa.is_india_eligible is False
    assert "On-site" in wa.display_label


def test_location_present_but_work_mode_unspecified() -> None:
    job = {"title": "Senior Data Analyst", "location": "Berlin, Germany", "description": "Leading data analytics initiatives."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "unknown"
    assert wa.display_label.startswith("📍") or "Germany" in wa.display_label


def test_description_explicitly_mentioning_remote_eligibility() -> None:
    job = {"title": "Data Engineer", "location": "Global", "description": "This is a 100% remote role open to candidates worldwide."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.remote_scope == "worldwide"
    assert wa.is_india_eligible is True


def test_remote_job_country_restriction_embedded_in_freetext() -> None:
    job = {"title": "Backend Developer", "location": "Remote", "description": "We are looking for a Python developer. Candidates must reside in the US and have US work authorization."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.is_india_eligible is False
    assert "United States" in wa.remote_countries


def test_stage1_candidate_filter_excludes_ineligible_country_restricted_job() -> None:
    india_profile = {
        "locations": ["India", "Remote"],
        "target_roles": ["Backend Engineer"],
        "skills": ["Python", "SQL", "APIs"],
    }

    eligible_job = {
        "title": "Senior Backend Engineer",
        "location": "Remote - Worldwide",
        "description": "Python, SQL, REST APIs microservices.",
    }
    ineligible_job = {
        "title": "Senior Backend Engineer",
        "location": "Remote - US Only",
        "description": "Python, SQL, REST APIs microservices. Must be based in US.",
    }

    assert profile_matches_job(eligible_job, india_profile) is True
    assert profile_matches_job(ineligible_job, india_profile) is False


def test_legacy_job_without_work_arrangement_dict() -> None:
    # Simulates a legacy job stored before this feature without work_arrangement in payload_json
    legacy_job = {
        "job_id": "legacy_123",
        "title": "Senior Data Engineer",
        "company": "Tech Corp",
        "location": "Remote - India",
        "description": "Python, SQL ETL pipelines.",
    }
    # Direct parsing handles missing work_arrangement gracefully
    wa = parse_work_arrangement(legacy_job)
    assert wa.work_mode == "remote"
    assert wa.is_india_eligible is True

    # Pre-computed reuse works when present
    legacy_job["work_arrangement"] = wa.as_dict()
    wa_cached = parse_work_arrangement(legacy_job)
    assert wa_cached.display_label == wa.display_label

