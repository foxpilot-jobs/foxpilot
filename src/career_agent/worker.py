"""Durable database-backed worker for production-shaped local deployments."""

from __future__ import annotations

import time

from .config import load_config
from .services import CareerService
from .storage import JobStore


def process_one() -> bool:
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
            store.update_background_job(job["job_id"], "failed", error=f"Unsupported job kind: {job['kind']}")
    return True


def main() -> None:
    while True:
        if not process_one():
            time.sleep(2)


if __name__ == "__main__":
    main()
