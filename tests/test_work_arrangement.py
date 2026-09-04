from __future__ import annotations

from career_agent.work_arrangement import (
    is_job_location_eligible,
    parse_work_arrangement,
)
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
    assert wa.work_mode == "onsite"
    assert "On-site" in wa.display_label or "Berlin" in wa.display_label


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
    # Explicit applicant restriction (US Only) excludes India candidate
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


def test_reclassified_unknown_patterns() -> None:
    # 1. Dedicated remote job sources
    jobicy_job = {"source": "jobicy", "title": "Software Engineer", "location": "USA", "description": "Backend python role"}
    assert parse_work_arrangement(jobicy_job).work_mode == "remote"

    # 2. ATS listing with physical office location defaulting to onsite
    ats_onsite = {"source": "greenhouse", "title": "Aero Software Developer", "location": "Location A, Country A", "description": "Engineering role"}
    assert parse_work_arrangement(ats_onsite).work_mode == "onsite"

    # 3. Expanded remote keywords
    remote_first = {"source": "ashby", "title": "Frontend Engineer", "location": "Location A", "description": "We are a remote-first engineering team."}
    assert parse_work_arrangement(remote_first).work_mode == "remote"

    # 4. Expanded hybrid keywords
    hybrid_flex = {"source": "arbeitnow", "title": "Data Architect", "location": "Location B", "description": "Flexible working arrangement available."}
    assert parse_work_arrangement(hybrid_flex).work_mode == "hybrid"


def test_missing_location_with_explicit_country_restriction() -> None:
    job = {"title": "Software Engineer", "work_type": "Hybrid", "location": "", "description": "Hybrid position. Applicants must reside in Canada."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "hybrid"
    assert wa.remote_countries == ["Canada"]
    assert wa.display_label == "🔀 Hybrid · Canada"


def test_missing_location_with_only_employer_hq_metadata() -> None:
    job = {"title": "Software Engineer", "work_type": "Hybrid", "location": "", "description": "Company HQ in San Francisco, USA. Building SaaS features."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "hybrid"
    assert wa.remote_countries == []
    assert wa.display_label == "🔀 Hybrid"


def test_hybrid_job_with_no_geographic_information() -> None:
    job = {"title": "Data Analyst", "work_type": "Hybrid", "location": "", "description": "Analytics role. Hybrid 2 days per week."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "hybrid"
    assert wa.remote_countries == []
    assert wa.display_label == "🔀 Hybrid"


def test_remote_job_whose_company_hq_is_in_different_country() -> None:
    job = {"title": "Backend Developer", "work_type": "Remote", "location": "San Francisco, CA", "description": "Work remotely. Company HQ in San Francisco, USA."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.remote_countries == []
    assert wa.display_label == "🏠 Remote"
    assert is_job_location_eligible(job, "remote", ["Toronto, Canada"]) is True
    assert is_job_location_eligible(job, "any", ["Location A, Country A"]) is True


def test_remote_worldwide_job_with_populated_company_location() -> None:
    job = {"title": "Full Stack Engineer", "work_type": "Remote", "location": "London, UK", "description": "Work anywhere in the world. Company HQ in London, UK."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.remote_scope == "worldwide"
    assert wa.remote_countries == []
    assert wa.display_label == "🌎 Remote · Worldwide"
    assert is_job_location_eligible(job, "remote", ["Location A, Country A"]) is True


def test_precedence_1_remote_desc_with_populated_office_location() -> None:
    job = {"title": "Software Engineer", "location": "Location A, Country A", "description": "100% remote position."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"


def test_precedence_2_hybrid_desc_with_populated_office_location() -> None:
    job = {"title": "Software Engineer", "location": "Location B, Country B", "description": "Hybrid work model, 2 days in office."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "hybrid"


def test_precedence_3_onsite_desc_with_populated_location() -> None:
    job = {"title": "Software Engineer", "location": "Location C, Country C", "description": "Onsite role, must work in-person at office."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "onsite"


def test_precedence_4_remote_desc_mentioning_occasional_office_visits() -> None:
    job = {"title": "Backend Developer", "location": "Location D, Country D", "description": "This is a remote position with occasional office visits."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"


def test_precedence_5_hybrid_desc_mentioning_company_hq() -> None:
    job = {"title": "Product Manager", "location": "Location E, Country E", "description": "Hybrid role. Company HQ in Location A, Country A."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "hybrid"
    assert wa.remote_countries == []


def test_precedence_6_no_work_mode_text_with_physical_location() -> None:
    job = {"title": "Software Engineer", "location": "Location F, Country F", "description": "Building microservices using Java and AWS."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "onsite"


def test_precedence_7_no_work_mode_text_with_empty_location() -> None:
    job = {"title": "Software Engineer", "location": "", "description": "Building microservices using Java and AWS."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "unknown"
    assert wa.display_label == "❓ Work mode unknown"


def test_precedence_8_dedicated_remote_source_with_geographic_region() -> None:
    job = {"source": "remoteok", "title": "DevOps Engineer", "location": "APAC / Asia", "description": "Cloud infra role."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert "Asia" in wa.remote_regions
    assert wa.remote_scope == "region_specific"
    assert wa.display_label == "🌏 Remote · Asia"


def test_precedence_9_explicit_applicant_restriction_must_reside_in_country() -> None:
    job = {"title": "Backend Dev", "location": "Remote", "description": "Must reside in Canada."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.remote_countries == ["Canada"]


def test_precedence_10_employer_hq_in_country_without_applicant_restriction() -> None:
    job = {"title": "Backend Dev", "location": "Remote", "description": "Work remotely. Company HQ in San Francisco, USA."}
    wa = parse_work_arrangement(job)
    assert wa.work_mode == "remote"
    assert wa.remote_countries == []
