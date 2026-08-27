from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from career_agent.storage import JobStore
from career_agent.storage.database import job_listings_table, jobs_table


@pytest.fixture
def store(tmp_path: Path) -> JobStore:
    db_path = tmp_path / "test_lifecycle.db"
    return JobStore(f"sqlite:///{db_path}", user_id="test-user")


def create_sample_job(source: str, source_job_id: str, title: str = "Software Engineer") -> dict:
    return {
        "source": source,
        "source_job_id": source_job_id,
        "title": title,
        "company": "Acme Corp",
        "location": "Remote",
        "url": f"https://example.com/jobs/{source_job_id}",
        "description": "Building great scalable products",
        "visibility": "public",
    }


def test_successful_ingestion_and_reconciliation_resets_failures(store: JobStore) -> None:
    job = create_sample_job("remoteok", "101")
    store.bulk_upsert_jobs([job])

    # Simulate a successful fetch where job 101 is returned
    stats = store.reconcile_source_listings("remoteok", returned_source_job_ids={"101"}, miss_threshold=2)
    assert stats["archived_listings"] == 0
    assert stats["archived_jobs"] == 0

    with store.engine.connect() as conn:
        row = conn.execute(
            select(job_listings_table.c.availability_status, job_listings_table.c.check_failures).where(
                job_listings_table.c.source_job_id == "101"
            )
        ).first()
        assert row is not None
        assert row.availability_status == "active"
        assert row.check_failures == 0


def test_one_missed_run_remains_active(store: JobStore) -> None:
    job = create_sample_job("remoteok", "102")
    store.bulk_upsert_jobs([job])

    # Run 1: Job 102 is missing from returned jobs
    stats = store.reconcile_source_listings("remoteok", returned_source_job_ids=set(), miss_threshold=2)
    assert stats["archived_listings"] == 0
    assert stats["archived_jobs"] == 0

    with store.engine.connect() as conn:
        listing = conn.execute(
            select(job_listings_table.c.availability_status, job_listings_table.c.check_failures).where(
                job_listings_table.c.source_job_id == "102"
            )
        ).first()
        assert listing is not None
        assert listing.availability_status == "active"
        assert listing.check_failures == 1

        j = conn.execute(select(jobs_table.c.is_active)).first()
        assert j is not None
        assert j.is_active is True


def test_two_consecutive_missed_runs_archives_job(store: JobStore) -> None:
    job = create_sample_job("remoteok", "103")
    job_id = store.upsert_job(job)

    # Miss 1
    store.reconcile_source_listings("remoteok", returned_source_job_ids=set(), miss_threshold=2)

    # Miss 2 (triggers archival threshold)
    stats = store.reconcile_source_listings("remoteok", returned_source_job_ids=set(), miss_threshold=2)
    assert stats["archived_listings"] == 1
    assert stats["archived_jobs"] == 1

    with store.engine.connect() as conn:
        listing = conn.execute(
            select(job_listings_table.c.availability_status, job_listings_table.c.status_reason).where(
                job_listings_table.c.source_job_id == "103"
            )
        ).first()
        assert listing is not None
        assert listing.availability_status == "inactive"
        assert listing.status_reason == "missing_from_source_consecutive_runs"

        j = conn.execute(select(jobs_table.c.is_active).where(jobs_table.c.job_id == job_id)).first()
        assert j is not None
        assert j.is_active is False


def test_reappearance_of_archived_job_reactivates_cleanly(store: JobStore) -> None:
    job = create_sample_job("remoteok", "104")
    job_id = store.upsert_job(job)

    # Force 2 misses to archive
    store.reconcile_source_listings("remoteok", returned_source_job_ids=set(), miss_threshold=2)
    store.reconcile_source_listings("remoteok", returned_source_job_ids=set(), miss_threshold=2)

    with store.engine.connect() as conn:
        j_inactive = conn.execute(select(jobs_table.c.is_active).where(jobs_table.c.job_id == job_id)).first()
        assert j_inactive.is_active is False

    # Reappearance: Job 104 is returned again
    store.bulk_upsert_jobs([job])
    store.reconcile_source_listings("remoteok", returned_source_job_ids={"104"}, miss_threshold=2)

    with store.engine.connect() as conn:
        listing = conn.execute(
            select(job_listings_table.c.availability_status, job_listings_table.c.check_failures).where(
                job_listings_table.c.source_job_id == "104"
            )
        ).first()
        assert listing is not None
        assert listing.availability_status == "active"
        assert listing.check_failures == 0

        j_active = conn.execute(select(jobs_table.c.is_active).where(jobs_table.c.job_id == job_id)).first()
        assert j_active is not None
        assert j_active.is_active is True

        # Total job count must still be 1 (no duplicate rows created)
        total_jobs = conn.execute(select(jobs_table)).all()
        assert len(total_jobs) == 1


def test_multiple_sources_one_fails_one_succeeds(store: JobStore) -> None:
    job_a = create_sample_job("remoteok", "201")
    job_b = create_sample_job("remotive", "202")
    store.bulk_upsert_jobs([job_a, job_b])

    # RemoteOK succeeds and returns job 201
    store.reconcile_source_listings("remoteok", returned_source_job_ids={"201"}, miss_threshold=2)

    # Remotive fails (reconcile_source_listings is NOT called for remotive)
    # Verify job 202 from remotive is unchanged and remains active
    with store.engine.connect() as conn:
        listing_b = conn.execute(
            select(job_listings_table.c.availability_status, job_listings_table.c.check_failures).where(
                job_listings_table.c.source_job_id == "202"
            )
        ).first()
        assert listing_b is not None
        assert listing_b.availability_status == "active"
        assert listing_b.check_failures == 0


def test_archived_job_preserves_user_match(store: JobStore) -> None:
    job = create_sample_job("remoteok", "301")
    job_id = store.upsert_job(job)

    # Save a user match for this job
    store.save_match(
        job_id=job_id,
        job_hash="hash123",
        provider="openai",
        model="gpt-5.6",
        result={"match_score": 85, "recommendation": "CONSIDER"},
    )

    # Archive the job
    store.reconcile_source_listings("remoteok", returned_source_job_ids=set(), miss_threshold=2)
    store.reconcile_source_listings("remoteok", returned_source_job_ids=set(), miss_threshold=2)

    # Verify user match remains intact in database
    match = store.get_match(job_id)
    assert match is not None
    assert match["job_id"] == job_id
    assert match["match"]["match_score"] == 85
