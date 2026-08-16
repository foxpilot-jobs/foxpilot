"""Use-case services for the FoxPilot product."""

from __future__ import annotations

import hashlib
import json

from ..config import AppConfig
from ..llm import LLMError, create_provider
from ..matching import match_job
from ..profile import create_profile_from_text
from ..storage import JobStore


class CareerService:
    def __init__(self, config: AppConfig, user_id: str = "local-user") -> None:
        self.config = config
        self.user_id = user_id

    def _store(self) -> JobStore:
        return JobStore(self.config.resolved_database_url, user_id=self.user_id)

    def list_jobs(self, relevance: str | None = None) -> list[dict]:
        with self._store() as store:
            return store.list_jobs(relevance=relevance)

    def get_job(self, job_id: str) -> dict | None:
        with self._store() as store:
            return store.get_job(job_id)

    def list_matches(self) -> list[dict]:
        with self._store() as store:
            return store.list_matches()

    def get_application(self, job_id: str) -> dict | None:
        with self._store() as store:
            return store.get_application(job_id)

    def list_applications(self) -> list[dict]:
        with self._store() as store:
            return store.list_applications()

    def update_application(self, job_id: str, status: str, notes: str = "") -> dict:
        with self._store() as store:
            if not store.get_job(job_id):
                raise KeyError(job_id)
            store.save_application(job_id, status=status, notes=notes)
            application = store.get_application(job_id)
            if application is None:
                raise RuntimeError("Application state was not persisted")
            return application

    def save_profile(self, resume_text: str, resume_filename: str) -> dict:
        profile = create_profile_from_text(self.config, resume_text, persist=False)
        with self._store() as store:
            store.save_profile(resume_text, resume_filename, profile)
        return profile

    def get_profile(self) -> dict | None:
        with self._store() as store:
            profile = store.get_profile()
        if not profile:
            return None
        return {
            "resume_filename": profile["resume_filename"],
            "profile": profile["profile_json"],
            "created_at": profile["created_at"],
            "updated_at": profile["updated_at"],
        }

    def run_matching(self) -> dict[str, int]:
        with self._store() as store:
            profile_row = store.get_profile()
            if not profile_row:
                raise ValueError("Upload a resume before running matching")
            jobs = store.list_jobs(relevance="TARGET")
            provider = create_provider(self.config)
            analyzed = 0
            skipped = 0
            failed = 0
            for job in jobs:
                content = {
                    key: job.get(key) for key in ("title", "company", "location", "url", "description")
                }
                job_hash = hashlib.sha256(
                    json.dumps(content, sort_keys=True, ensure_ascii=False).encode("utf-8")
                ).hexdigest()
                cached = store.get_match(job["job_id"])
                if cached and cached.get("job_hash") == job_hash:
                    skipped += 1
                    continue
                try:
                    result = match_job(self.config, profile_row["profile_json"], job, provider=provider)
                    store.save_match(
                        job["job_id"],
                        job_hash,
                        self.config.llm_provider,
                        self.config.llm_model,
                        result,
                    )
                    analyzed += 1
                except (LLMError, ValueError):
                    failed += 1
            return {"total": len(jobs), "analyzed": analyzed, "skipped": skipped, "failed": failed}
