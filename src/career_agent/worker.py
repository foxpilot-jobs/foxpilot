"""Durable database-backed worker with lease, heartbeat, and retry support.

Handles user-scoped background jobs (profile generation, scan, matching) and
shared ingestion runs.  Each background job is leased to a worker identified
by ``worker_id``.  A heartbeat thread extends the lease while the job executes.
If the worker crashes, the expired lease allows another worker (or a process
restart) to reclaim the job.

Failures are classified as ``retryable`` or ``permanent``:
- Retryable failures return the job to ``queued`` (up to ``max_attempts``).
- Permanent failures or exhausted retries move the job to ``dead_letter``.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from uuid import uuid4

from .config import load_config
from .services import CareerService, IngestionService
from .storage import JobStore

# -- Worker identity -------------------------------------------------------


def _worker_id() -> str:
    host = os.environ.get("HOSTNAME") or os.environ.get("RAILWAY_REPLICA_ID") or "local"
    return f"{host}-{os.getpid()}-{uuid4().hex[:8]}"


# -- Heartbeat -------------------------------------------------------------

HEARTBEAT_INTERVAL_SECONDS = 30
LEASE_DURATION_MINUTES = 5


class Heartbeat:
    """Background thread that extends a job's lease while it runs."""

    def __init__(
        self,
        database_url: str,
        job: dict,
        worker_id: str,
    ) -> None:
        self._database_url = database_url
        self._job_id = job["job_id"]
        self._user_id = job["user_id"]
        self._worker_id = worker_id
        self._stop = threading.Event()
        self._thread = threading.Thread(
            target=self._run, daemon=True, name=f"heartbeat-{self._job_id[:12]}"
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=5)

    def _run(self) -> None:
        while not self._stop.wait(HEARTBEAT_INTERVAL_SECONDS):
            try:
                with JobStore(self._database_url, user_id=self._user_id) as store:
                    ok = store.heartbeat_background_job(
                        self._job_id,
                        self._worker_id,
                        lease_duration_minutes=LEASE_DURATION_MINUTES,
                    )
                    if not ok:
                        # Lease was stolen or job is no longer running; stop heartbeat.
                        break
            except Exception:
                logging.getLogger(__name__).debug(
                    "Heartbeat failed for %s", self._job_id, exc_info=True
                )


# -- Job dispatch -----------------------------------------------------------


def _execute_job(config, job: dict) -> None:
    """Dispatch a claimed job to the appropriate service method."""
    service = CareerService(config, user_id=job["user_id"])
    kind = job["kind"]
    if kind == "profile_generation":
        service.run_profile_generation(job["job_id"])
    elif kind == "scan":
        service.run_scan_job(job["job_id"])
    elif kind == "matching":
        service.run_matching_job(job["job_id"])
    else:
        with JobStore(config.resolved_database_url, user_id=job["user_id"]) as store:
            store.update_background_job(
                job["job_id"],
                "failed",
                error=f"Unsupported job kind: {kind}",
                error_class="permanent",
            )


def _process_background_job(worker_id: str) -> bool:
    """Claim and execute one user-scoped background job.  Return True if work was done."""
    config = load_config()
    with JobStore(config.resolved_database_url) as store:
        job = store.claim_next_background_job(
            worker_id=worker_id,
            lease_duration_minutes=LEASE_DURATION_MINUTES,
        )
    if not job:
        return False

    heartbeat = Heartbeat(config.resolved_database_url, job, worker_id)
    heartbeat.start()
    try:
        _execute_job(config, job)
    finally:
        heartbeat.stop()
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


def process_one(worker_id: str | None = None) -> bool:
    """Process one unit of work — background job or ingestion run."""
    wid = worker_id or _worker_id()
    return _process_background_job(wid) or _process_ingestion_run()


def main() -> None:
    wid = _worker_id()
    print(f"[WORKER] Starting worker {wid}")
    while True:
        if not process_one(wid):
            time.sleep(2)


if __name__ == "__main__":
    main()
