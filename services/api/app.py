"""Versioned HTTP API for the local and future hosted web clients."""

from __future__ import annotations

import os

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from career_agent.config import load_config
from career_agent.services import CareerService

from .auth import require_api_access


class ApplicationUpdate(BaseModel):
    status: str = Field(pattern="^(saved|applied|interviewing|rejected|offered)$")
    notes: str = Field(default="", max_length=10_000)


def create_app() -> FastAPI:
    app = FastAPI(
        title="FoxPilot API",
        version="0.1.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    allowed_origins = os.getenv(
        "CAREER_AGENT_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in allowed_origins if origin.strip()],
        allow_credentials=False,
        allow_methods=["GET", "POST", "PUT"],
        allow_headers=["Content-Type"],
    )
    app.state.service = CareerService(load_config())

    def service() -> CareerService:
        return app.state.service

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

    @app.get("/api/v1/jobs")
    def list_jobs(
        career_service: CareerService = Depends(service),
        _: None = Depends(require_api_access),
        relevance: str | None = Query(default=None, pattern="^(TARGET|REVIEW|EXCLUDE)$"),
    ) -> list[dict]:
        return career_service.list_jobs(relevance=relevance)

    @app.get("/api/v1/jobs/{job_id}")
    def get_job(
        job_id: str,
        career_service: CareerService = Depends(service),
        _: None = Depends(require_api_access),
    ) -> dict:
        job = career_service.get_job(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return job

    @app.get("/api/v1/matches")
    def list_matches(
        career_service: CareerService = Depends(service),
        _: None = Depends(require_api_access),
    ) -> list[dict]:
        return career_service.list_matches()

    @app.get("/api/v1/jobs/{job_id}/application")
    def get_application(
        job_id: str,
        career_service: CareerService = Depends(service),
        _: None = Depends(require_api_access),
    ) -> dict | None:
        if career_service.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail="Job not found")
        return career_service.get_application(job_id)

    @app.put("/api/v1/jobs/{job_id}/application")
    def update_application(
        job_id: str,
        update: ApplicationUpdate,
        career_service: CareerService = Depends(service),
        _: None = Depends(require_api_access),
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
