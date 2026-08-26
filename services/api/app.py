"""Versioned HTTP API for the local and future hosted web clients."""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlencode

import httpx
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    HTTPException,
    Query,
    Request,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pydantic import BaseModel, Field
from pypdf.errors import PdfReadError
from sqlalchemy.exc import IntegrityError

from career_agent.config import load_config
from career_agent.email import configured as email_configured
from career_agent.email import send_email
from career_agent.llm import LLMError
from career_agent.profile import extract_resume_text_from_bytes
from career_agent.services import CareerService, IngestionService
from career_agent.storage import JobStore, dispose_all_engines, initialize_database

from .auth import (
    SESSION_COOKIE,
    AuthContext,
    clear_session_cookie,
    consume_auth_token,
    create_auth_token,
    create_session,
    get_user_by_email,
    hash_password,
    hosted_cookie,
    is_breached_password,
    normalize_email,
    require_api_access,
    set_session_cookie,
    verify_password,
)
from .security import InMemoryRateLimiter

GOOGLE_STATE_COOKIE = "foxpilot_google_state"
GOOGLE_STATE_MAX_AGE = 600


def _google_configured() -> bool:
    client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET", "").strip()
    return (
        bool(client_id and client_secret)
        and not client_id.startswith("your-")
        and not client_secret.startswith("your-")
    )


class ApplicationUpdate(BaseModel):
    status: str = Field(pattern="^(saved|applied|interviewing|rejected|offered)$")
    notes: str = Field(default="", max_length=10_000)


class AuthCredentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=12, max_length=256)


class AuthUser(BaseModel):
    user_id: str
    email: str
    email_verified: bool
    session_created: bool = True


class AuthToken(BaseModel):
    token: str = Field(min_length=20)


class PasswordReset(AuthToken):
    password: str = Field(min_length=12, max_length=256)


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)


MAX_RESUME_BYTES = 10 * 1024 * 1024


def _auth_user_response(user: dict) -> AuthUser:
    return AuthUser(
        user_id=user["user_id"],
        email=user["email"],
        email_verified=bool(user["email_verified"]),
    )


def _google_redirect_uri() -> str:
    return os.getenv(
        "GOOGLE_REDIRECT_URI",
        f"{os.getenv('FOXPILOT_PUBLIC_URL', 'http://localhost:8080').rstrip('/')}/api/v1/auth/google/callback",
    )


def _google_failure(message: str) -> RedirectResponse:
    return RedirectResponse(
        url=f"{os.getenv('FOXPILOT_PUBLIC_URL', 'http://localhost:8080').rstrip('/')}/login?oauth_error={message}",
        status_code=303,
    )


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        initialize_database(application.state.service.config.resolved_database_url)
        if os.getenv("FOXPILOT_WORKER_MODE", "inline").lower() != "external":
            with JobStore(
                application.state.service.config.resolved_database_url
            ) as store:
                store.recover_interrupted_background_jobs()
        yield
        dispose_all_engines()

    app = FastAPI(
        title="FoxPilot API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    allowed_origins = [
        origin.strip().rstrip("/")
        for origin in os.getenv(
            "CAREER_AGENT_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    app.state.service = CareerService(load_config())
    app.state.ingestion_service = IngestionService(load_config())
    app.state.rate_limiter = InMemoryRateLimiter()

    @app.middleware("http")
    async def protect_native_unsafe_requests(request: Request, call_next):
        unsafe_method = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        native_mode = os.getenv("FOXPILOT_AUTH_MODE", "").lower() == "native"
        origin = request.headers.get("origin")
        if unsafe_method and native_mode and origin and origin not in allowed_origins:
            return JSONResponse(
                status_code=403, content={"detail": "Request origin is not allowed"}
            )
        return await call_next(request)

    @app.middleware("http")
    async def measure_endpoint_performance(request: Request, call_next):
        path = request.url.path
        monitored = {
            "/api/v1/auth/me",
            "/api/v1/profile",
            "/api/v1/jobs",
            "/api/v1/matches",
            "/api/v1/applications",
        }
        if path not in monitored:
            return await call_next(request)

        from career_agent.storage.database import _REQUEST_TIMINGS

        ctx = {
            "auth_ms": 0.0,
            "queries": [],
            "events": [],
        }
        token = _REQUEST_TIMINGS.set(ctx)
        t_start = time.perf_counter()
        ctx["events"].append(("middleware_start", t_start))
        try:
            response = await call_next(request)
            t_end = time.perf_counter()
            ctx["events"].append(("middleware_end", t_end))
            total_ms = (t_end - t_start) * 1000

            events = ctx.get("events", [])
            timeline_lines = []
            for ev in events:
                rel_ms = (ev[1] - t_start) * 1000
                name = ev[0]
                extra = " ".join(str(x) for x in ev[2:]) if len(ev) > 2 else ""
                timeline_lines.append(f"  +{rel_ms:7.2f} ms | {name} {extra}".rstrip())

            report_text = (
                f"\n============================================================\n"
                f"[HIGH-RES TIMELINE BREAKDOWN] {request.method} {path} -> Status {response.status_code}\n"
                f"  - Total Request Time: {total_ms:.2f} ms\n"
                + "\n".join(timeline_lines)
                + "\n"
                "============================================================\n"
            )
            logger.info(report_text)
            print(report_text, flush=True)
            return response
        finally:
            _REQUEST_TIMINGS.reset(token)

    def service() -> CareerService:
        return app.state.service

    def user_service(
        current_user: AuthContext = Depends(require_api_access),
    ) -> CareerService:
        return CareerService(app.state.service.config, user_id=current_user.user_id)

    def enforce_rate_limit(request: Request, bucket: str, limit: int) -> None:
        client = request.headers.get("x-real-ip") or (
            request.client.host if request.client else "unknown"
        )
        if not app.state.rate_limiter.allow(f"{bucket}:{client}", limit):
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again shortly.",
                headers={"Retry-After": "60"},
            )

    def run_in_process() -> bool:
        return os.getenv("FOXPILOT_WORKER_MODE", "inline").lower() != "external"

    @app.get("/api/v1/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/api/v1/health/live")
    def liveness() -> dict[str, str]:
        return {"status": "alive"}

    @app.get("/api/v1/health/ready")
    def readiness(career_service: CareerService = Depends(service)) -> dict[str, str]:
        try:
            career_service.list_jobs()
        except Exception as error:
            raise HTTPException(
                status_code=503, detail="Database is not ready"
            ) from error
        return {"status": "ready"}

    @app.post("/api/v1/auth/register", response_model=AuthUser, status_code=201)
    def register(
        credentials: AuthCredentials, request: Request, response: Response
    ) -> AuthUser:
        enforce_rate_limit(request, "register", 5)
        email = normalize_email(credentials.email)
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise HTTPException(status_code=422, detail="Enter a valid email address")
        if is_breached_password(credentials.password):
            raise HTTPException(status_code=422, detail="Choose a less common password")
        if get_user_by_email(request, email):
            raise HTTPException(
                status_code=409, detail="An account already exists for this email"
            )
        production = os.getenv("FOXPILOT_ENV", "local") == "production"
        if production and not email_configured():
            raise HTTPException(
                status_code=503, detail="Email delivery is not configured"
            )

        user_id = f"user_{os.urandom(12).hex()}"
        store = JobStore(app.state.service.config.resolved_database_url)
        try:
            try:
                store.create_user(user_id, email, hash_password(credentials.password))
            except IntegrityError as error:
                raise HTTPException(
                    status_code=409,
                    detail="An account already exists for this email",
                ) from error
            if email_configured():
                verification_token = create_auth_token(
                    store, user_id, "email_verification"
                )
                public_url = os.getenv("FOXPILOT_PUBLIC_URL", "http://localhost:8080")
                try:
                    send_email(
                        email,
                        "Verify your FoxPilot email",
                        f"Verify your FoxPilot account: {public_url}/verify-email?token={verification_token}",
                    )
                except Exception as error:
                    logger.exception("Verification email delivery failed")
                    raise HTTPException(
                        status_code=503,
                        detail="Email delivery is temporarily unavailable. Try again later.",
                    ) from error
            token = create_session(store, user_id)
        finally:
            store.close()
        if not production:
            set_session_cookie(response, token, False)
        return AuthUser(
            user_id=user_id,
            email=email,
            email_verified=False,
            session_created=not production,
        )

    @app.post("/api/v1/auth/login", response_model=AuthUser)
    def login(
        credentials: AuthCredentials, request: Request, response: Response
    ) -> AuthUser:
        enforce_rate_limit(request, "login", 10)
        user = get_user_by_email(request, credentials.email)
        if not user or not verify_password(
            credentials.password, user.get("password_hash")
        ):
            raise HTTPException(
                status_code=401, detail="Email or password is incorrect"
            )
        store = JobStore(app.state.service.config.resolved_database_url)
        try:
            token = create_session(store, user["user_id"])
        finally:
            store.close()
        set_session_cookie(
            response, token, os.getenv("FOXPILOT_ENV", "local") == "production"
        )
        return _auth_user_response(user)

    @app.get("/api/v1/auth/google/start")
    def google_start(response: Response) -> RedirectResponse:
        client_id = os.getenv("GOOGLE_CLIENT_ID", "").strip()
        if not _google_configured():
            raise HTTPException(
                status_code=503,
                detail="Google sign-in is not configured with a real OAuth web client",
            )
        state = os.urandom(32).hex()
        nonce = secrets.token_urlsafe(32)
        params = {
            "client_id": client_id,
            "redirect_uri": _google_redirect_uri(),
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "nonce": nonce,
            "access_type": "offline",
            "prompt": "select_account",
        }
        redirect = RedirectResponse(
            url=f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}",
            status_code=303,
        )
        redirect.set_cookie(
            GOOGLE_STATE_COOKIE,
            f"{state}.{nonce}",
            max_age=GOOGLE_STATE_MAX_AGE,
            httponly=True,
            secure=hosted_cookie(
                os.getenv("FOXPILOT_ENV", "local").lower() == "production"
            ),
            samesite="none"
            if hosted_cookie(os.getenv("FOXPILOT_ENV", "local").lower() == "production")
            else "lax",
            path="/",
        )
        return redirect

    @app.get("/api/v1/auth/google/callback")
    def google_callback(
        request: Request, code: str | None = None, state: str | None = None
    ) -> RedirectResponse:
        expected_cookie = request.cookies.get(GOOGLE_STATE_COOKIE, "")
        expected_state, _, expected_nonce = expected_cookie.partition(".")
        if (
            not code
            or not state
            or not expected_state
            or not expected_nonce
            or not hmac.compare_digest(state, expected_state)
        ):
            return _google_failure("invalid_state")
        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
        if not _google_configured():
            return _google_failure("not_configured")
        try:
            token_response = httpx.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "code": code,
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "redirect_uri": _google_redirect_uri(),
                    "grant_type": "authorization_code",
                },
                timeout=15,
            )
            token_response.raise_for_status()
            token_payload = token_response.json()
            claims = id_token.verify_oauth2_token(
                token_payload["id_token"], google_requests.Request(), client_id
            )
            if not hmac.compare_digest(str(claims.get("nonce", "")), expected_nonce):
                return _google_failure("invalid_nonce")
            email = normalize_email(str(claims["email"]))
            subject = str(claims["sub"])
            if not claims.get("email_verified") or not email or not subject:
                return _google_failure("email_not_verified")
        except (httpx.HTTPError, KeyError, ValueError):
            return _google_failure("verification_failed")

        store = JobStore(app.state.service.config.resolved_database_url)
        try:
            user = store.get_user_by_auth_subject("google", subject)
            if not user:
                user = store.get_user_by_email(email)
                if user:
                    store.link_auth_subject(user["user_id"], "google", subject)
                    user = store.get_user(user["user_id"])
                else:
                    user_id = f"user_{os.urandom(12).hex()}"
                    store.create_user(user_id, email, None, "google", subject)
                    user = store.get_user(user_id)
            if not user:
                return _google_failure("account_unavailable")
            session_token = create_session(store, user["user_id"])
        finally:
            store.close()

        redirect = RedirectResponse(
            url=f"{os.getenv('FOXPILOT_PUBLIC_URL', 'http://localhost:8080').rstrip('/')}/app",
            status_code=303,
        )
        redirect.delete_cookie(GOOGLE_STATE_COOKIE, path="/")
        set_session_cookie(
            redirect,
            session_token,
            os.getenv("FOXPILOT_ENV", "local").lower() == "production",
        )
        return redirect

    @app.post("/api/v1/auth/logout", status_code=204)
    def logout(request: Request, response: Response) -> None:
        token = request.cookies.get(SESSION_COOKIE)
        if token:
            store = JobStore(app.state.service.config.resolved_database_url)
            try:
                store.revoke_session(hashlib.sha256(token.encode("utf-8")).hexdigest())
            finally:
                store.close()
        clear_session_cookie(response)

    @app.get("/api/v1/auth/me", response_model=AuthUser)
    def auth_me(request: Request) -> AuthUser:
        user = require_api_access(request)
        return AuthUser(
            user_id=user.user_id,
            email=user.email or "",
            email_verified=user.email_verified,
        )

    @app.post("/api/v1/auth/verify-email", response_model=AuthUser)
    def verify_email(
        payload: AuthToken, request: Request, response: Response
    ) -> AuthUser:
        store = JobStore(app.state.service.config.resolved_database_url)
        try:
            token = consume_auth_token(store, payload.token, "email_verification")
            if not token:
                raise HTTPException(
                    status_code=400, detail="Verification link is invalid or expired"
                )
            store.mark_email_verified(token["user_id"])
            user = store.get_user(token["user_id"])
            session_token = create_session(store, token["user_id"])
        finally:
            store.close()
        if not user:
            raise HTTPException(status_code=400, detail="User account is unavailable")
        set_session_cookie(
            response, session_token, os.getenv("FOXPILOT_ENV", "local") == "production"
        )
        return _auth_user_response(user)

    @app.post("/api/v1/auth/request-password-reset", status_code=202)
    def request_password_reset(payload: PasswordResetRequest, request: Request) -> None:
        enforce_rate_limit(request, "password-reset", 3)
        email = normalize_email(payload.email)
        user = get_user_by_email(request, email)
        if user and email_configured():
            store = JobStore(app.state.service.config.resolved_database_url)
            try:
                reset_token = create_auth_token(
                    store, user["user_id"], "password_reset"
                )
                public_url = os.getenv("FOXPILOT_PUBLIC_URL", "http://localhost:8080")
                send_email(
                    email,
                    "Reset your FoxPilot password",
                    f"Reset your FoxPilot password: {public_url}/reset-password?token={reset_token}",
                )
            finally:
                store.close()

    @app.post("/api/v1/auth/reset-password", response_model=AuthUser)
    def reset_password(
        payload: PasswordReset, request: Request, response: Response
    ) -> AuthUser:
        store = JobStore(app.state.service.config.resolved_database_url)
        try:
            token = consume_auth_token(store, payload.token, "password_reset")
            if not token:
                raise HTTPException(
                    status_code=400, detail="Reset link is invalid or expired"
                )
            store.update_password(token["user_id"], hash_password(payload.password))
            store.revoke_user_sessions(token["user_id"])
            user = store.get_user(token["user_id"])
            session_token = create_session(store, token["user_id"])
        finally:
            store.close()
        if not user:
            raise HTTPException(status_code=400, detail="User account is unavailable")
        set_session_cookie(
            response, session_token, os.getenv("FOXPILOT_ENV", "local") == "production"
        )
        return _auth_user_response(user)

    @app.post("/api/v1/profile/resume", status_code=202)
    async def upload_resume(
        background_tasks: BackgroundTasks,
        request: Request,
        file: UploadFile = File(...),
        career_service: CareerService = Depends(user_service),
    ) -> dict:
        enforce_rate_limit(request, "resume-upload", 5)
        filename = Path(file.filename or "resume.pdf").name
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(
                status_code=422, detail="Resume uploads must be PDF files"
            )
        content = await file.read(MAX_RESUME_BYTES + 1)
        if len(content) > MAX_RESUME_BYTES:
            raise HTTPException(
                status_code=413, detail="Resume file must be 10 MB or smaller"
            )
        try:
            resume_text = extract_resume_text_from_bytes(content, filename)
            if not resume_text.strip():
                raise ValueError("The uploaded PDF did not contain readable text")
            job_id = career_service.queue_profile_generation(resume_text, filename)
            if run_in_process():
                background_tasks.add_task(career_service.run_profile_generation, job_id)
        except (PdfReadError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except LLMError as error:
            raise HTTPException(
                status_code=502,
                detail=f"Unable to create a profile from the configured LLM provider: {error}",
            ) from error
        return {
            "job_id": job_id,
            "kind": "profile_generation",
            "status": "queued",
            "resume_filename": filename,
        }

    @app.get("/api/v1/profile")
    def get_profile(career_service: CareerService = Depends(user_service)) -> dict:
        return career_service.get_profile()

    @app.get("/api/v1/profile/jobs/{job_id}")
    def get_profile_job(
        job_id: str, career_service: CareerService = Depends(user_service)
    ) -> dict:
        job = career_service.get_background_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Background job not found")
        return job

    @app.post("/api/v1/profile/match", status_code=202)
    def run_profile_matching(
        background_tasks: BackgroundTasks,
        request: Request,
        career_service: CareerService = Depends(user_service),
    ) -> dict:
        enforce_rate_limit(request, "profile-matching", 5)
        try:
            job_id = career_service.queue_matching()
            if run_in_process():
                background_tasks.add_task(career_service.run_matching_job, job_id)
            return {"job_id": job_id, "kind": "matching", "status": "queued"}
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.post("/api/v1/jobs/scan", status_code=202)
    def scan_jobs(
        background_tasks: BackgroundTasks,
        request: Request,
        career_service: CareerService = Depends(user_service),
    ) -> dict:
        enforce_rate_limit(request, "job-scan", 3)
        try:
            job_id = career_service.queue_scan()
            if run_in_process():
                background_tasks.add_task(career_service.run_scan_job, job_id)
            return {"job_id": job_id, "kind": "scan", "status": "queued"}
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    # -- Shared ingestion (profile-independent corpus population) --

    @app.post("/api/v1/ingestion/runs", status_code=202)
    def start_ingestion_run(
        background_tasks: BackgroundTasks,
        request: Request,
        current_user: AuthContext = Depends(require_api_access),
    ) -> dict:
        enforce_rate_limit(request, "ingestion-run", 3)
        ingestion = app.state.ingestion_service
        run_id = ingestion.queue_run(
            trigger="api",
            trigger_user_id=current_user.user_id,
        )
        if run_in_process():
            background_tasks.add_task(ingestion.run_ingestion, run_id)
        return {"run_id": run_id, "status": "queued"}

    @app.get("/api/v1/ingestion/runs/{run_id}")
    def get_ingestion_run(
        run_id: str,
        _current_user: AuthContext = Depends(require_api_access),
    ) -> dict:
        run = app.state.ingestion_service.get_run(run_id)
        if run is None:
            raise HTTPException(status_code=404, detail="Ingestion run not found")
        return run

    @app.get("/api/v1/me")
    def current_identity(
        current_user: AuthContext = Depends(require_api_access),
    ) -> dict:
        return {
            "user_id": current_user.user_id,
            "email": current_user.email,
        }

    @app.get("/api/v1/jobs")
    def list_jobs(
        career_service: CareerService = Depends(user_service),
        relevance: str | None = Query(
            default=None, pattern="^(TARGET|REVIEW|EXCLUDE)$"
        ),
        include_inactive: bool = Query(default=False),
    ) -> list[dict]:
        return career_service.list_jobs(
            relevance=relevance, include_inactive=include_inactive
        )

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(
        job_id: str,
        career_service: CareerService = Depends(user_service),
    ) -> dict:
        job = career_service.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @app.get("/api/v1/matches")
    def list_matches(
        career_service: CareerService = Depends(user_service),
    ) -> list[dict]:
        return career_service.list_matches()

    @app.get("/api/v1/applications")
    def list_applications(
        career_service: CareerService = Depends(user_service),
    ) -> list[dict]:
        return career_service.list_applications()

    @app.get("/api/v1/jobs/{job_id}/application")
    def get_application(
        job_id: str,
        career_service: CareerService = Depends(user_service),
    ) -> dict | None:
        if career_service.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return career_service.get_application(job_id)

    @app.put("/api/v1/jobs/{job_id}/application")
    def update_application(
        job_id: str,
        update: ApplicationUpdate,
        career_service: CareerService = Depends(user_service),
    ) -> dict:
        try:
            return career_service.update_application(
                job_id,
                status=update.status,
                notes=update.notes,
            )
        except KeyError as error:
            raise HTTPException(status_code=404, detail="Job not found") from error

    return app


app = create_app()
logger = logging.getLogger(__name__)
