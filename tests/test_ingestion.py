"""Tests for the shared ingestion service and API endpoints."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from career_agent.config import AppConfig
from career_agent.services.ingestion import IngestionService
from career_agent.storage import JobStore
from services.api.app import create_app

# -- IngestionService unit tests --


def test_queue_run_creates_ingestion_run(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    service = IngestionService(config)
    run_id = service.queue_run(trigger="test")
    run = service.get_run(run_id)

    assert run is not None
    assert run["run_id"] == run_id
    assert run["status"] == "queued"
    assert run["trigger"] == "test"
    assert run["trigger_user_id"] is None


def test_queue_run_reuses_active_run(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    service = IngestionService(config)
    first = service.queue_run(trigger="test")
    second = service.queue_run(trigger="test")

    assert first == second


def test_run_ingestion_completes(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    service = IngestionService(config)

    calls = []
    monkeypatch.setattr(
        "career_agent.services.ingestion.fetch_configured_sources",
        lambda profile, user_id: calls.append((profile, user_id)) or 7,
    )

    run_id = service.queue_run(trigger="test", trigger_user_id="user-a")
    service.run_ingestion(run_id)

    assert calls == [(None, "system")]
    run = service.get_run(run_id)
    assert run is not None
    assert run["status"] == "completed"
    assert run["result"] == {"jobs_upserted": 7}
    assert run["trigger_user_id"] == "user-a"


def test_run_ingestion_records_failure(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    service = IngestionService(config)

    def fail_fetch(**_kwargs):
        raise RuntimeError("source unavailable")

    monkeypatch.setattr(
        "career_agent.services.ingestion.fetch_configured_sources",
        lambda profile, user_id: (_ for _ in ()).throw(
            RuntimeError("source unavailable")
        ),
    )

    run_id = service.queue_run(trigger="test")
    service.run_ingestion(run_id)

    run = service.get_run(run_id)
    assert run is not None
    assert run["status"] == "failed"
    assert "source unavailable" in run["error"]


def test_get_run_returns_none_for_unknown_id(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    service = IngestionService(config)
    assert service.get_run("nonexistent") is None


def test_queue_run_allows_new_after_completion(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    service = IngestionService(config)

    monkeypatch.setattr(
        "career_agent.services.ingestion.fetch_configured_sources",
        lambda profile, user_id: 0,
    )

    first = service.queue_run(trigger="test")
    service.run_ingestion(first)

    second = service.queue_run(trigger="test")
    assert first != second


# -- CareerService scan delegates to IngestionService --


def test_scan_delegates_to_ingestion_service(tmp_path: Path, monkeypatch) -> None:
    from career_agent.services import CareerService

    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path, user_id="user-a") as store:
        store.save_profile(
            "Resume text",
            "resume.pdf",
            {"current_or_recent_roles": ["Data Engineer"]},
        )

    calls = []
    monkeypatch.setattr(
        "career_agent.services.ingestion.fetch_configured_sources",
        lambda profile, user_id: calls.append((profile, user_id)) or 3,
    )

    service = CareerService(config, user_id="user-a")
    job_id = service.queue_scan()
    service.run_scan_job(job_id)

    # Ingestion should run WITHOUT profile (profile=None)
    assert calls == [(None, "system")]
    bg_job = service.get_background_job(job_id)
    assert bg_job is not None
    assert bg_job["status"] == "completed"
    assert bg_job["result"]["new_jobs"] == 3
    assert "ingestion_run_id" in bg_job["result"]


# -- Storage layer tests --


def test_ingestion_run_crud(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        store.create_ingestion_run("run-1", trigger="api", trigger_user_id="user-a")
        run = store.get_ingestion_run("run-1")
        assert run is not None
        assert run["status"] == "queued"
        assert run["trigger"] == "api"
        assert run["trigger_user_id"] == "user-a"

        store.update_ingestion_run("run-1", "running")
        run = store.get_ingestion_run("run-1")
        assert run["status"] == "running"

        store.update_ingestion_run("run-1", "completed", result={"jobs_upserted": 5})
        run = store.get_ingestion_run("run-1")
        assert run["status"] == "completed"
        assert run["result_json"] == {"jobs_upserted": 5}


def test_get_active_ingestion_run(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        assert store.get_active_ingestion_run() is None

        store.create_ingestion_run("run-1", trigger="test")
        active = store.get_active_ingestion_run()
        assert active is not None
        assert active["run_id"] == "run-1"

        store.update_ingestion_run("run-1", "completed", result={})
        assert store.get_active_ingestion_run() is None


# -- API endpoint tests --


@pytest.fixture()
def local_auth(monkeypatch):
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    monkeypatch.delenv("FOXPILOT_API_TOKEN", raising=False)


def test_api_ingestion_run_lifecycle(tmp_path: Path, local_auth, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    monkeypatch.setattr(
        "career_agent.services.ingestion.fetch_configured_sources",
        lambda profile, user_id: 5,
    )
    monkeypatch.setenv("FOXPILOT_WORKER_MODE", "external")

    app = create_app()
    app.state.service.config = config
    app.state.ingestion_service = IngestionService(config)
    client = TestClient(app)

    response = client.post("/api/v1/ingestion/runs")
    assert response.status_code == 202
    body = response.json()
    assert "run_id" in body
    assert body["status"] == "queued"

    run_id = body["run_id"]

    # Execute the ingestion directly (simulating external worker)
    app.state.ingestion_service.run_ingestion(run_id)

    response = client.get(f"/api/v1/ingestion/runs/{run_id}")
    assert response.status_code == 200
    run = response.json()
    assert run["status"] == "completed"
    assert run["result"] == {"jobs_upserted": 5}
    assert run["trigger"] == "api"


def test_api_ingestion_run_not_found(tmp_path: Path, local_auth) -> None:
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    app.state.ingestion_service = IngestionService(config)
    client = TestClient(app)

    response = client.get("/api/v1/ingestion/runs/nonexistent")
    assert response.status_code == 404


def test_api_ingestion_run_reuses_active(
    tmp_path: Path, local_auth, monkeypatch
) -> None:
    config = AppConfig(data_dir=tmp_path)
    monkeypatch.setenv("FOXPILOT_WORKER_MODE", "external")

    app = create_app()
    app.state.service.config = config
    app.state.ingestion_service = IngestionService(config)
    client = TestClient(app)

    first = client.post("/api/v1/ingestion/runs").json()["run_id"]
    second = client.post("/api/v1/ingestion/runs").json()["run_id"]

    assert first == second
