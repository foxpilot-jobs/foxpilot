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
    body = response.json()
    assert "items" in body
    assert "next_cursor" in body
    assert "total" in body
    assert body["items"][0]["title"] == "Data Engineer"


def test_api_job_detail_returns_user_context(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        job_id = store.upsert_job(
            {
                "source": "test",
                "source_job_id": "detail-1",
                "title": "Data Engineer",
                "company": "Example",
            }
        )
        store.save_match(
            job_id,
            "hash",
            "test-provider",
            "test-model",
            {"match_score": 88, "recommendation": "APPLY"},
        )
        store.save_application(job_id, status="saved", notes="Review this role")

    app = create_app()
    app.state.service.config = config
    response = TestClient(app).get(f"/api/v1/jobs/{job_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["job_id"] == job_id
    assert body["sources"][0]["source"] == "test"
    assert body["match"]["match_score"] == 88
    assert body["application"]["status"] == "saved"


def test_api_job_detail_returns_404_for_unknown_job(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config

    assert TestClient(app).get("/api/v1/jobs/missing").status_code == 404


def test_hosted_cors_preflight_accepts_configured_origin_with_trailing_slash(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("CAREER_AGENT_ALLOWED_ORIGINS", "https://foxpilot.vercel.app/")
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    response = client.options(
        "/api/v1/auth/login",
        headers={
            "Origin": "https://foxpilot.vercel.app",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert (
        response.headers["access-control-allow-origin"] == "https://foxpilot.vercel.app"
    )
    assert response.headers["access-control-allow-credentials"] == "true"


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
    assert applications.json()["items"][0]["status"] == "applied"


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


def test_native_auth_uses_cross_site_cookie_for_hosted_staging(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "native")
    monkeypatch.setenv("FOXPILOT_ENV", "staging")
    monkeypatch.setenv("FOXPILOT_PUBLIC_URL", "https://foxpilot.vercel.app")
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config

    response = TestClient(app).post(
        "/api/v1/auth/register",
        json={
            "email": "hosted@example.com",
            "password": "correct horse battery staple",
        },
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
            json={
                "email": f"user-{index}@example.com",
                "password": "unique passphrase 123",
            },
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


def test_google_callback_links_user_and_creates_session(
    tmp_path: Path, monkeypatch
) -> None:
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

    monkeypatch.setattr(
        "services.api.app.httpx.post", lambda *_args, **_kwargs: TokenResponse()
    )
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


def test_endpoint_latency_benchmarks(tmp_path: Path) -> None:
    import time

    config = AppConfig(data_dir=tmp_path)
    with JobStore(config.database_path) as store:
        for i in range(20):
            store.upsert_job(
                {"source": "bench", "source_job_id": str(i), "title": f"Role {i}"}
            )

    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    endpoints = [
        "/api/v1/auth/me",
        "/api/v1/jobs",
        "/api/v1/matches",
        "/api/v1/applications",
        "/api/v1/profile",
    ]

    timings = {}
    for path in endpoints:
        start = time.perf_counter()
        response = client.get(path)
        elapsed_ms = (time.perf_counter() - start) * 1000
        timings[path] = round(elapsed_ms, 2)
        assert response.status_code in {200, 404}

    print("\n[BENCHMARK ENDPOINT LATENCIES]:", timings)
    for path, elapsed_ms in timings.items():
        assert elapsed_ms < 200, (
            f"{path} took {elapsed_ms:.2f}ms which exceeds 200ms threshold"
        )


def test_get_profile_returns_200_for_new_authenticated_user_without_resume(
    tmp_path: Path,
) -> None:
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    response = client.get("/api/v1/profile")
    assert response.status_code == 200
    data = response.json()
    assert data["resume_filename"] == ""
    assert data["profile"] == {}
    assert data["created_at"] is None
    assert data["updated_at"] is None


def test_auth_me_single_query_and_session_behavior(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("FOXPILOT_AUTH_MODE", "native")
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    # Unauthenticated request returns 401
    assert client.get("/api/v1/auth/me").status_code == 401

    # Register user
    reg = client.post(
        "/api/v1/auth/register",
        json={"email": "singlequery@example.com", "password": "secure passphrase 1234"},
    )
    assert reg.status_code == 201

    executed_statements = []

    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        executed_statements.append(statement)

    from sqlalchemy import event

    with JobStore(config.database_path) as store:
        event.listen(store.engine, "before_cursor_execute", before_cursor_execute)
        try:
            response = client.get("/api/v1/auth/me")
            assert response.status_code == 200
            data = response.json()
            assert data["email"] == "singlequery@example.com"
            assert data["user_id"] == reg.json()["user_id"]
            # Verify exactly 1 query executed for /auth/me
            assert len(executed_statements) == 1
        finally:
            event.remove(store.engine, "before_cursor_execute", before_cursor_execute)


def test_get_active_profile_job_returns_200_with_null_when_no_active_job(tmp_path: Path) -> None:
    config = AppConfig(data_dir=tmp_path)
    app = create_app()
    app.state.service.config = config
    client = TestClient(app)

    # 1. No active job -> 200 OK with None / null
    res = client.get("/api/v1/profile/jobs/active/matching")
    assert res.status_code == 200
    assert res.json() is None

    # 2. Unsupported kind -> 400 Bad Request
    unsupported = client.get("/api/v1/profile/jobs/active/invalid_kind")
    assert unsupported.status_code == 400

    # 3. Active job exists -> 200 OK with job object
    with JobStore(config.database_path) as store:
        store.save_profile("Resume text", "resume.pdf", {"skills": ["Python"]})
        store.create_background_job("test-job-1", "matching")

    active_res = client.get("/api/v1/profile/jobs/active/matching")
    assert active_res.status_code == 200
    job = active_res.json()
    assert job is not None
    assert job["job_id"] == "test-job-1"
    assert job["status"] == "queued"
