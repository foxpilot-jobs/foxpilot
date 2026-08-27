from __future__ import annotations

from unittest.mock import patch

from career_agent.config import load_config
from career_agent.sources.http_sources import SourceJob, fetch_configured_sources
from career_agent.storage import JobStore


def test_ingestion_tech_filtering_and_ambiguous_roles(tmp_path) -> None:
    db_path = tmp_path / "test_ingestion.db"

    dummy_raw_jobs = [
        SourceJob("mock", "1", "Senior Data Engineer", "Co A", "Remote", "http://job1", "Python SQL ETL"),
        SourceJob("mock", "2", "Graphic Designer", "Co B", "Remote", "http://job2", "Figma UI graphics"),
        SourceJob("mock", "3", "Product Support Jedi", "Co C", "Remote", "http://job3", "SaaS software troubleshooting"),
        SourceJob("mock", "4", "Data Labeling Specialists", "Co D", "Remote", "http://job4", "Annotating AI datasets"),
        SourceJob("mock", "5", "Business Systems Analyst", "Co E", "Remote", "http://job5", "SQL database queries"),
        SourceJob("mock", "6", "Technical Writer", "Co F", "Remote", "http://job6", "API documentation"),
        SourceJob("mock", "7", "Subway Sandwich Artist", "Co G", "Remote", "http://job7", "Making sandwiches"),
        SourceJob("mock", "8", "AP Accountant", "Co H", "Remote", "http://job8", "Managing ledger and invoices"),
    ]

    mock_source_config = {
        "remoteok": {"enabled": True},
        "remotive": {"enabled": True},
        "hacker_news": {"enabled": False},
        "arbeitnow": {"enabled": False},
        "jobicy": {"enabled": False},
    }

    with patch("career_agent.sources.http_sources.fetch_remoteok", return_value=dummy_raw_jobs), \
         patch("career_agent.sources.http_sources.fetch_remotive", return_value=[]), \
         patch("career_agent.sources.http_sources._load_source_config", return_value=mock_source_config), \
         patch("career_agent.sources.http_sources.load_config") as mock_config:

        config = load_config()
        config.database_url = f"sqlite:///{db_path}"
        mock_config.return_value = config

        # Perform first ingestion
        res = fetch_configured_sources(user_id="system", return_details=True)
        assert isinstance(res, dict)
        assert res["raw_fetched"] == 8
        assert res["tech_accepted"] == 6
        assert res["non_tech_rejected"] == 2
        assert res["jobs_upserted"] == 6

        # Verify database contents
        with JobStore(config.resolved_database_url) as store:
            jobs_page = store.list_jobs(include_inactive=False)
            db_jobs = jobs_page.get("items", []) if isinstance(jobs_page, dict) else jobs_page
            db_titles = [j["title"] for j in db_jobs]

            # Tech & ambiguous digital roles ingested
            assert "Senior Data Engineer" in db_titles
            assert "Graphic Designer" in db_titles
            assert "Product Support Jedi" in db_titles
            assert "Data Labeling Specialists" in db_titles
            assert "Business Systems Analyst" in db_titles
            assert "Technical Writer" in db_titles

            # Non-tech roles rejected before insertion
            assert "Subway Sandwich Artist" not in db_titles
            assert "AP Accountant" not in db_titles


def test_idempotent_ingestion_and_source_failure_isolation(tmp_path) -> None:
    db_path = tmp_path / "test_idempotent.db"

    dummy_raw_jobs = [
        SourceJob("remoteok", "101", "Full Stack Engineer", "Tech Co", "Remote", "http://job101", "Python React"),
    ]

    mock_source_config = {
        "remoteok": {"enabled": True},
        "remotive": {"enabled": True},
        "hacker_news": {"enabled": False},
        "arbeitnow": {"enabled": False},
        "jobicy": {"enabled": False},
    }

    with patch("career_agent.sources.http_sources.fetch_remoteok", return_value=dummy_raw_jobs), \
         patch("career_agent.sources.http_sources.fetch_remotive", side_effect=Exception("Source Timeout")), \
         patch("career_agent.sources.http_sources._load_source_config", return_value=mock_source_config), \
         patch("career_agent.sources.http_sources.load_config") as mock_config:

        config = load_config()
        config.database_url = f"sqlite:///{db_path}"
        mock_config.return_value = config

        # First run (Remotive fails, RemoteOK succeeds)
        res1 = fetch_configured_sources(user_id="system", return_details=True)
        assert res1["jobs_upserted"] == 1

        # Second run with same job (Verify idempotency and last_seen_at update, zero duplicates)
        res2 = fetch_configured_sources(user_id="system", return_details=True)
        assert res2["jobs_upserted"] == 1  # 0 inserted, 1 updated

        with JobStore(config.resolved_database_url) as store:
            jobs_page = store.list_jobs(include_inactive=False)
            db_jobs = jobs_page.get("items", []) if isinstance(jobs_page, dict) else jobs_page
            assert len(db_jobs) == 1
            assert db_jobs[0]["title"] == "Full Stack Engineer"
            assert db_jobs[0]["is_active"] is True
