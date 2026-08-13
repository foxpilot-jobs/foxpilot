from pathlib import Path

from fastapi.testclient import TestClient

from career_agent.config import AppConfig
from career_agent.storage import JobStore
from services.api.app import create_app


def test_api_health_and_jobs(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        store.upsert_job(
            {
                "source": "test",
                "source_job_id": "1",
                "title": "Data Engineer",
            }
        )

    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    assert client.get("/api/v1/health").json() == {"status": "ok"}
    assert client.get("/api/v1/health/live").json() == {"status": "alive"}
    assert client.get("/api/v1/health/ready").json() == {"status": "ready"}
    response = client.get("/api/v1/jobs")
    assert response.status_code == 200
    assert response.json()[0]["title"] == "Data Engineer"


def test_api_application_update(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        job_id = store.upsert_job(
            {"source": "test", "source_job_id": "1", "title": "Data Engineer"}
        )

    app = create_app()
    app.state.service.config = config
    client = TestClient(app)
    response = client.put(
        f"/api/v1/jobs/{job_id}/application",
        json={"status": "applied", "notes": "Submitted"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "applied"


def test_api_token_protects_data_endpoints(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    monkeypatch.setenv("FOXPILOT_API_TOKEN", "test-token")
    client = TestClient(app)

    assert client.get("/api/v1/jobs").status_code == 401
    response = client.get(
        "/api/v1/jobs",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200
