"""Versioned HTTP API for the local and future hosted web clients."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

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
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from pypdf.errors import PdfReadError
from sqlalchemy.exc import IntegrityError

from career_agent.config import load_config
from career_agent.email import configured as email_configured
from career_agent.email import send_email
from career_agent.llm import LLMError
from career_agent.profile import extract_resume_text_from_bytes
from career_agent.services import CareerService
from career_agent.storage import JobStore

from .auth import (
    SESSION_COOKIE,
    AuthContext,
    clear_session_cookie,
    consume_auth_token,
    create_auth_token,
    create_session,
    get_user_by_email,
    hash_password,
    normalize_email,
    require_api_access,
    set_session_cookie,
    verify_password,
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


def create_app() -> FastAPI:
    app = FastAPI(
        title="FoxPilot API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    allowed_origins = [
        origin.strip()
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
        allow_headers=["Content-Type"],
    )
    app.state.service = CareerService(load_config())

    @app.middleware("http")
    async def protect_native_unsafe_requests(request: Request, call_next):
        unsafe_method = request.method in {"POST", "PUT", "PATCH", "DELETE"}
        native_mode = os.getenv("FOXPILOT_AUTH_MODE", "").lower() == "native"
        origin = request.headers.get("origin")
        if unsafe_method and native_mode and origin and origin not in allowed_origins:
            return JSONResponse(status_code=403, content={"detail": "Request origin is not allowed"})
        return await call_next(request)

    def service() -> CareerService:
        return app.state.service

    def user_service(current_user: AuthContext = Depends(require_api_access)) -> CareerService:
        return CareerService(app.state.service.config, user_id=current_user.user_id)

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
            raise HTTPException(status_code=503, detail="Database is not ready") from error
        return {"status": "ready"}

    @app.post("/api/v1/auth/register", response_model=AuthUser, status_code=201)
    def register(credentials: AuthCredentials, request: Request, response: Response) -> AuthUser:
        email = normalize_email(credentials.email)
        if "@" not in email or email.startswith("@") or email.endswith("@"):
            raise HTTPException(status_code=422, detail="Enter a valid email address")
        if get_user_by_email(request, email):
            raise HTTPException(status_code=409, detail="An account already exists for this email")
        production = os.getenv("FOXPILOT_ENV", "local") == "production"
        if production and not email_configured():
            raise HTTPException(status_code=503, detail="Email delivery is not configured")

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
                verification_token = create_auth_token(store, user_id, "email_verification")
                public_url = os.getenv("FOXPILOT_PUBLIC_URL", "http://localhost:8080")
                send_email(
                    email,
                    "Verify your FoxPilot email",
                    f"Verify your FoxPilot account: {public_url}/verify-email?token={verification_token}",
                )
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
    def login(credentials: AuthCredentials, request: Request, response: Response) -> AuthUser:
        user = get_user_by_email(request, credentials.email)
        if not user or not verify_password(credentials.password, user.get("password_hash")):
            raise HTTPException(status_code=401, detail="Email or password is incorrect")
        store = JobStore(app.state.service.config.resolved_database_url)
        try:
            token = create_session(store, user["user_id"])
        finally:
            store.close()
        set_session_cookie(response, token, os.getenv("FOXPILOT_ENV", "local") == "production")
        return _auth_user_response(user)

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
        if user.user_id == "local-user":
            return AuthUser(user_id=user.user_id, email=user.email or "", email_verified=True)
        database_user = get_user_by_email(request, user.email or "")
        if not database_user:
            raise HTTPException(status_code=401, detail="User account is unavailable")
        return _auth_user_response(database_user)

    @app.post("/api/v1/auth/verify-email", response_model=AuthUser)
    def verify_email(payload: AuthToken, request: Request, response: Response) -> AuthUser:
        store = JobStore(app.state.service.config.resolved_database_url)
        try:
            token = consume_auth_token(store, payload.token, "email_verification")
            if not token:
                raise HTTPException(status_code=400, detail="Verification link is invalid or expired")
            store.mark_email_verified(token["user_id"])
            user = store.get_user(token["user_id"])
            session_token = create_session(store, token["user_id"])
        finally:
            store.close()
        if not user:
            raise HTTPException(status_code=400, detail="User account is unavailable")
        set_session_cookie(response, session_token, os.getenv("FOXPILOT_ENV", "local") == "production")
        return _auth_user_response(user)

    @app.post("/api/v1/auth/request-password-reset", status_code=202)
    def request_password_reset(payload: PasswordResetRequest, request: Request) -> None:
        email = normalize_email(payload.email)
        user = get_user_by_email(request, email)
        if user and email_configured():
            store = JobStore(app.state.service.config.resolved_database_url)
            try:
                reset_token = create_auth_token(store, user["user_id"], "password_reset")
                public_url = os.getenv("FOXPILOT_PUBLIC_URL", "http://localhost:8080")
                send_email(
                    email,
                    "Reset your FoxPilot password",
                    f"Reset your FoxPilot password: {public_url}/reset-password?token={reset_token}",
                )
            finally:
                store.close()

    @app.post("/api/v1/auth/reset-password", response_model=AuthUser)
    def reset_password(payload: PasswordReset, request: Request, response: Response) -> AuthUser:
        store = JobStore(app.state.service.config.resolved_database_url)
        try:
            token = consume_auth_token(store, payload.token, "password_reset")
            if not token:
                raise HTTPException(status_code=400, detail="Reset link is invalid or expired")
            store.update_password(token["user_id"], hash_password(payload.password))
            store.revoke_user_sessions(token["user_id"])
            user = store.get_user(token["user_id"])
            session_token = create_session(store, token["user_id"])
        finally:
            store.close()
        if not user:
            raise HTTPException(status_code=400, detail="User account is unavailable")
        set_session_cookie(response, session_token, os.getenv("FOXPILOT_ENV", "local") == "production")
        return _auth_user_response(user)

    @app.post("/api/v1/profile/resume", status_code=202)
    async def upload_resume(
        background_tasks: BackgroundTasks,
        file: UploadFile = File(...),
        career_service: CareerService = Depends(user_service),
    ) -> dict:
        filename = Path(file.filename or "resume.pdf").name
        if not filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=422, detail="Resume uploads must be PDF files")
        content = await file.read(MAX_RESUME_BYTES + 1)
        if len(content) > MAX_RESUME_BYTES:
            raise HTTPException(status_code=413, detail="Resume file must be 10 MB or smaller")
        try:
            resume_text = extract_resume_text_from_bytes(content, filename)
            if not resume_text.strip():
                raise ValueError("The uploaded PDF did not contain readable text")
            job_id = career_service.queue_profile_generation(resume_text, filename)
            background_tasks.add_task(career_service.run_profile_generation, job_id)
        except (PdfReadError, ValueError) as error:
            raise HTTPException(status_code=422, detail=str(error)) from error
        except LLMError as error:
            raise HTTPException(
                status_code=502,
                detail=f"Unable to create a profile from the configured LLM provider: {error}",
            ) from error
        return {"job_id": job_id, "kind": "profile_generation", "status": "queued", "resume_filename": filename}

    @app.get("/api/v1/profile")
    def get_profile(career_service: CareerService = Depends(user_service)) -> dict:
        profile = career_service.get_profile()
        if profile is None:
            raise HTTPException(status_code=404, detail="No resume profile has been uploaded")
        return profile

    @app.get("/api/v1/profile/jobs/{job_id}")
    def get_profile_job(job_id: str, career_service: CareerService = Depends(user_service)) -> dict:
        job = career_service.get_background_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Background job not found")
        return job

    @app.post("/api/v1/profile/match", status_code=202)
    def run_profile_matching(
        background_tasks: BackgroundTasks,
        career_service: CareerService = Depends(user_service),
    ) -> dict:
        try:
            job_id = career_service.queue_matching()
            background_tasks.add_task(career_service.run_matching_job, job_id)
            return {"job_id": job_id, "kind": "matching", "status": "queued"}
        except ValueError as error:
            raise HTTPException(status_code=422, detail=str(error)) from error

    @app.get("/api/v1/me")
    def current_identity(current_user: AuthContext = Depends(require_api_access)) -> dict:
        return {
            "user_id": current_user.user_id,
            "email": current_user.email,
        }

    @app.get("/api/v1/jobs")
    def list_jobs(
        career_service: CareerService = Depends(user_service),
        relevance: str | None = Query(default=None, pattern="^(TARGET|REVIEW|EXCLUDE)$"),
    ) -> list[dict]:
        return career_service.list_jobs(relevance=relevance)

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
