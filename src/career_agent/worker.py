"""Durable database-backed worker for production-shaped local deployments.

Handles user-scoped background jobs (profile generation, scan, matching) and
shared ingestion runs.  The two loops are interleaved: each iteration checks
for a pending background job first, then for a queued ingestion run.
"""

from __future__ import annotations

import time

from .config import load_config
from .services import CareerService, IngestionService
from .storage import JobStore


def _process_background_job() -> bool:
    """Claim and execute one user-scoped background job.  Return True if work was done."""
    config = load_config()
    with JobStore(config.resolved_database_url) as store:
        job = store.claim_next_background_job()
    if not job:
        return False

    service = CareerService(config, user_id=job["user_id"])
    if job["kind"] == "profile_generation":
        service.run_profile_generation(job["job_id"])
    elif job["kind"] == "scan":
        service.run_scan_job(job["job_id"])
    elif job["kind"] == "matching":
        service.run_matching_job(job["job_id"])
    else:
        with JobStore(config.resolved_database_url, user_id=job["user_id"]) as store:
            store.update_background_job(
                job["job_id"], "failed", error=f"Unsupported job kind: {job['kind']}"
            )
    return True


def _process_ingestion_run() -> bool:
    """Claim and execute one queued ingestion run.  Return True if work was done."""
    config = load_config()
    with JobStore(config.resolved_database_url) as store:
        run = store.get_active_ingestion_run()
    if not run or run["status"] != "queued":
        return False

    ingestion = IngestionService(config)
    ingestion.run_ingestion(run["run_id"])
    return True


def process_one() -> bool:
    """Process one unit of work — background job or ingestion run."""
    return _process_background_job() or _process_ingestion_run()


def main() -> None:
    while True:
        if not process_one():
            time.sleep(2)


if __name__ == "__main__":
    main()
