from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from career_agent.config import AppConfig
from career_agent.storage import JobStore
from services.api.app import create_app


@pytest.fixture(autouse=True)
def local_auth_mode(monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    monkeypatch.delenv("FOXPILOT_API_TOKEN", raising=False)


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

    applications = client.get("/api/v1/applications")
    assert applications.status_code == 200
    assert applications.json()[0]["status"] == "applied"


def test_api_token_protects_data_endpoints(tmp_path: Path, monkeypatch) -> None:
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "token")
    monkeypatch.setenv("FOXPILOT_API_TOKEN", "test-token")
    client = TestClient(app)

    assert client.get("/api/v1/jobs").status_code == 401
    response = client.get(
        "/api/v1/jobs",
        headers={"Authorization": "Bearer test-token"},
    )
    assert response.status_code == 200


def test_api_exposes_local_identity(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("FOXPILOT_API_TOKEN", raising=False)
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "local")
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config

    response = TestClient(app).get("/api/v1/me")

    assert response.status_code == 200
    assert response.json() == {
        "user_id": "local-user",
        "email": "local@foxpilot.local",
    }


def test_api_token_identity_is_stable(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "token")
    monkeypatch.setenv("FOXPILOT_API_TOKEN", "test-token")
    monkeypatch.setenv("FOXPILOT_TOKEN_USER_ID", "staging-user")
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config

    response = TestClient(app).get(
        "/api/v1/me",
        headers={"Authorization": "Bearer test-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"user_id": "staging-user", "email": None}


def test_native_auth_register_session_and_logout(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "native")
    monkeypatch.setenv("FOXPILOT_ENV", "local")
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    registration = client.post(
        "/api/v1/auth/register",
        json={"email": "Nis@Example.com", "password": "correct horse battery staple"},
    )
    assert registration.status_code == 201
    assert "HttpOnly" in registration.headers["set-cookie"]
    assert registration.json()["email"] == "nis@example.com"
    assert registration.json()["email_verified"] is False

    authenticated = client.get("/api/v1/auth/me")
    assert authenticated.status_code == 200
    assert authenticated.json()["email"] == "nis@example.com"

    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "nis@example.com", "password": "correct horse battery staple"},
    )
    assert duplicate.status_code == 409

    assert client.post("/api/v1/auth/logout").status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "nis@example.com", "password": "correct horse battery staple"},
    )
    assert login.status_code == 200
    assert client.get("/api/v1/auth/me").status_code == 200


def test_native_auth_uses_cross_site_cookie_for_hosted_staging(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "native")
    monkeypatch.setenv("FOXPILOT_ENV", "staging")
    monkeypatch.setenv("FOXPILOT_PUBLIC_URL", "https://foxpilot.vercel.app")
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config

    response = TestClient(app).post(
        "/api/v1/auth/register",
        json={"email": "hosted@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 201
    cookie = response.headers["set-cookie"].lower()
    assert "secure" in cookie
    assert "samesite=none" in cookie


def test_native_auth_rejects_wrong_password(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "native")
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    client = TestClient(app)
    client.post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )

    response = client.post(
        "/api/v1/auth/login",
        json={"email": "user@example.com", "password": "wrong password here"},
    )
    assert response.status_code == 401


def test_registration_rejects_common_breached_password(tmp_path: Path) -> None:
    app = create_app()
    app.state.service.config = AppConfig(data_dir=tmp_path)

    response = TestClient(app).post(
        "/api/v1/auth/register",
        json={"email": "user@example.com", "password": "password1234"},
    )

    assert response.status_code == 422
    assert "less common" in response.json()["detail"]


def test_registration_is_rate_limited(tmp_path: Path) -> None:
    app = create_app()
    app.state.service.config = AppConfig(data_dir=tmp_path)
    client = TestClient(app)

    responses = [
        client.post(
            "/api/v1/auth/register",
            json={"email": f"user-{index}@example.com", "password": "unique passphrase 123"},
        )
        for index in range(6)
    ]

    assert [response.status_code for response in responses[:5]] == [201] * 5
    assert responses[5].status_code == 429
    assert responses[5].headers["retry-after"] == "60"


def test_native_auth_rejects_cross_origin_mutation(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "native")
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config

    response = TestClient(app).post(
        "/api/v1/auth/register",
        headers={"Origin": "https://malicious.example"},
        json={"email": "user@example.com", "password": "correct horse battery staple"},
    )

    assert response.status_code == 403
    assert response.json() == {"detail": "Request origin is not allowed"}


def test_profile_upload_and_retrieval(tmp_path: Path, monkeypatch) -> None:
    profile = {
        "summary": "Data engineer",
        "years_of_experience": 5,
        "current_or_recent_roles": ["Data Engineer"],
    }
    monkeypatch.setattr(
        "services.api.app.extract_resume_text_from_bytes",
        lambda _content, _filename: "Resume text",
    )
    monkeypatch.setattr(
        "career_agent.services.career.create_profile_from_text",
        lambda *_args, **_kwargs: profile,
    )
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    upload = client.post(
        "/api/v1/profile/resume",
        files={"file": ("resume.pdf", b"pdf-bytes", "application/pdf")},
    )

    assert upload.status_code == 202
    assert upload.json()["kind"] == "profile_generation"
    assert upload.json()["job_id"]
    retrieved = client.get("/api/v1/profile")
    assert retrieved.status_code == 200
    assert retrieved.json()["resume_filename"] == "resume.pdf"
    assert retrieved.json()["profile"] == profile


def test_profile_matching_requires_uploaded_profile(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config

    response = TestClient(app).post("/api/v1/profile/match")

    assert response.status_code == 422
    assert "Upload a resume" in response.json()["detail"]


def test_google_start_requires_configuration(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "")
    app = create_app()
    app.state.service.config = AppConfig(data_dir=tmp_path)

    response = TestClient(app).get("/api/v1/auth/google/start")

    assert response.status_code == 503
    assert "not configured" in response.json()["detail"]


def test_google_callback_links_user_and_creates_session(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "native")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "client-secret")
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    start = client.get("/api/v1/auth/google/start", follow_redirects=False)
    state_cookie = start.cookies["foxpilot_google_state"]
    state, nonce = state_cookie.split(".", 1)

    class TokenResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"id_token": "signed-token"}

    monkeypatch.setattr("services.api.app.httpx.post", lambda *_args, **_kwargs: TokenResponse())
    monkeypatch.setattr(
        "services.api.app.id_token.verify_oauth2_token",
        lambda *_args, **_kwargs: {
            "sub": "google-subject",
            "email": "google@example.com",
            "email_verified": True,
            "nonce": nonce,
        },
    )

    callback = client.get(
        f"/api/v1/auth/google/callback?code=auth-code&state={state}",
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert callback.headers["location"].endswith("/app")
    assert client.get("/api/v1/auth/me").json()["email"] == "google@example.com"
