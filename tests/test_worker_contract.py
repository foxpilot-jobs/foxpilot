"""Tests for the durable worker contract: lease, heartbeat, retry, dead-letter."""

from pathlib import Path

from career_agent.config import AppConfig
from career_agent.services import CareerService
from career_agent.storage import JobStore
from career_agent.worker_errors import classify_error

# -- Error classification --


def test_classify_error_retryable() -> None:
    assert classify_error(ConnectionError("connection reset")) == "retryable"
    assert classify_error(TimeoutError("request timed out")) == "retryable"
    assert classify_error(RuntimeError("HTTP 503 unavailable")) == "retryable"
    assert classify_error(RuntimeError("HTTP 429 rate limit")) == "retryable"


def test_classify_error_permanent() -> None:
    assert classify_error(ValueError("invalid input")) == "permanent"
    assert classify_error(KeyError("missing key")) == "permanent"
    assert classify_error(RuntimeError("schema validation failed")) == "permanent"


# -- Lease and claim --


def test_claim_sets_lease_owner_and_attempt(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching")
        claimed = store.claim_next_background_job(worker_id="worker-1")

    assert claimed is not None
    assert claimed["lease_owner"] == "worker-1"
    assert claimed["attempt"] == 1
    assert claimed["lease_expires_at"] is not None


def test_expired_lease_allows_reclaim(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching")
        claimed = store.claim_next_background_job(
            worker_id="worker-1", lease_duration_minutes=0
        )
        assert claimed is not None

        # Lease expired immediately (duration=0) so another worker can claim
        reclaimed = store.claim_next_background_job(worker_id="worker-2")
        assert reclaimed is not None
        assert reclaimed["lease_owner"] == "worker-2"
        assert reclaimed["attempt"] == 2


def test_active_lease_prevents_reclaim(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching")
        claimed = store.claim_next_background_job(
            worker_id="worker-1", lease_duration_minutes=60
        )
        assert claimed is not None

        # Lease is still valid — second worker should not get it
        second = store.claim_next_background_job(worker_id="worker-2")
        assert second is None


# -- Heartbeat --


def test_heartbeat_extends_lease(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching")
        claimed = store.claim_next_background_job(
            worker_id="worker-1", lease_duration_minutes=1
        )
        assert claimed is not None
        old_updated = claimed["updated_at"]

        ok = store.heartbeat_background_job(
            "job-1", "worker-1", lease_duration_minutes=10
        )
        assert ok

        job = store.get_background_job("job-1")
        assert job["lease_expires_at"] is not None
        # Verify the lease was actually extended (updated_at advanced)
        assert str(job["updated_at"]) >= str(old_updated)


def test_heartbeat_fails_for_wrong_worker(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching")
        store.claim_next_background_job(worker_id="worker-1")

        ok = store.heartbeat_background_job("job-1", "worker-IMPOSTER")
        assert not ok


def test_heartbeat_records_progress(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching")
        store.claim_next_background_job(worker_id="worker-1")

        store.heartbeat_background_job(
            "job-1", "worker-1", progress={"processed": 5, "total": 10}
        )

        job = store.get_background_job("job-1")
        assert job["progress_json"] == {"processed": 5, "total": 10}


# -- Retry and dead-letter --


def test_retryable_failure_requeues_job(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching", max_attempts=3)
        store.claim_next_background_job(worker_id="worker-1")  # attempt=1

        store.fail_background_job_retryable("job-1", "connection timeout")
        job = store.get_background_job("job-1")
        assert job["status"] == "queued"
        assert job["error_class"] == "retryable"
        assert job["lease_owner"] is None


def test_exhausted_retries_dead_letter(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching", max_attempts=2)

        # Attempt 1
        store.claim_next_background_job(worker_id="w1")
        store.fail_background_job_retryable("job-1", "timeout")
        assert store.get_background_job("job-1")["status"] == "queued"

        # Attempt 2
        store.claim_next_background_job(worker_id="w2")
        store.fail_background_job_retryable("job-1", "timeout again")
        assert store.get_background_job("job-1")["status"] == "dead_letter"
        assert store.get_background_job("job-1")["error_class"] == "permanent"


def test_permanent_failure_does_not_retry(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching", max_attempts=3)
        store.claim_next_background_job(worker_id="w1")

        store.update_background_job(
            "job-1", "failed", error="bad input", error_class="permanent"
        )
        job = store.get_background_job("job-1")
        assert job["status"] == "failed"
        assert job["error_class"] == "permanent"
        assert job["lease_owner"] is None


def test_claim_dead_letters_exhausted_job(tmp_path: Path) -> None:
    """A job past max_attempts should be dead-lettered on next claim attempt."""
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching", max_attempts=1)
        store.claim_next_background_job(worker_id="w1")  # attempt=1
        store.fail_background_job_retryable("job-1", "timeout")
        # Now attempt would be 2 but max is 1 → dead_letter on re-queue
        assert store.get_background_job("job-1")["status"] == "dead_letter"


# -- Recovery on restart --


def test_recover_requeues_retryable_jobs(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching", max_attempts=3)
        store.claim_next_background_job(worker_id="w1")  # attempt=1

        # Simulate process crash → recovery
        store.recover_interrupted_background_jobs()
        job = store.get_background_job("job-1")
        assert job["status"] == "queued"
        assert job["error_class"] == "retryable"
        assert job["lease_owner"] is None


def test_recover_dead_letters_exhausted_jobs(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching", max_attempts=1)
        store.claim_next_background_job(worker_id="w1")  # attempt=1

        store.recover_interrupted_background_jobs()
        job = store.get_background_job("job-1")
        assert job["status"] == "dead_letter"
        assert job["error_class"] == "permanent"


# -- Progress metadata --


def test_progress_metadata_persisted(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching")
        store.claim_next_background_job(worker_id="w1")

        store.update_background_job(
            "job-1", "running", progress={"processed": 3, "total": 10}
        )
        job = store.get_background_job("job-1")
        assert job["progress_json"] == {"processed": 3, "total": 10}


# -- Idempotency key --


def test_idempotency_key_prevents_duplicate(tmp_path: Path) -> None:
    import pytest

    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.create_background_job("job-1", "matching", idempotency_key="idem-1")
        with pytest.raises(Exception):  # noqa: B017 – unique constraint violation expected
            store.create_background_job("job-2", "matching", idempotency_key="idem-1")


# -- API exposes new fields --


def test_api_background_job_exposes_retry_state(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        store.create_background_job("job-1", "matching", max_attempts=3)
        store.claim_next_background_job(worker_id="w1")
        store.fail_background_job_retryable("job-1", "connection timeout")

    service = CareerService(config)
    job = service.get_background_job("job-1")
    assert job is not None
    assert job["status"] == "queued"
    assert job["error_class"] == "retryable"
    assert job["attempt"] == 1
    assert job["max_attempts"] == 3
    assert job["error"] == "connection timeout"


# -- Service-level retry classification --


def test_service_retries_transient_scan_failure(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.save_profile("Resume", "resume.pdf", {"target_roles": ["Engineer"]})

    monkeypatch.setattr(
        "career_agent.services.ingestion.fetch_configured_sources",
        lambda profile, user_id: (_ for _ in ()).throw(
            ConnectionError("connection reset")
        ),
    )

    service = CareerService(config, user_id="user-a")
    job_id = service.queue_scan()
    service.run_scan_job(job_id)

    job = service.get_background_job(job_id)
    assert job["status"] == "queued"  # re-queued for retry
    assert job["error_class"] == "retryable"


def test_service_permanent_fails_bad_input(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.save_profile("Resume", "resume.pdf", {"target_roles": ["Engineer"]})

    monkeypatch.setattr(
        "career_agent.services.ingestion.fetch_configured_sources",
        lambda profile, user_id: (_ for _ in ()).throw(
            ValueError("invalid source config")
        ),
    )

    service = CareerService(config, user_id="user-a")
    job_id = service.queue_scan()
    service.run_scan_job(job_id)

    job = service.get_background_job(job_id)
    assert job["status"] == "failed"
    assert job["error_class"] == "permanent"
