"""Use-case services for the FoxPilot product."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from uuid import uuid4

from filter_jobs import classify_job

from ..config import AppConfig
from ..llm import LLMError, create_provider
from ..matching import match_job
from ..profile import create_profile_from_text
from ..storage import JobStore
from .ingestion import IngestionService


class CareerService:
    def __init__(self, config: AppConfig, user_id: str = "local-user") -> None:
        self.config = config
        self.user_id = user_id

    def _store(self) -> JobStore:
        return JobStore(self.config.resolved_database_url, user_id=self.user_id)

    def list_jobs(
        self, relevance: str | None = None, include_inactive: bool = False
    ) -> list[dict]:
        with self._store() as store:
            return store.list_jobs(
                relevance=relevance, include_inactive=include_inactive
            )

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

    def get_profile(self) -> dict:
        with self._store() as store:
            profile = store.get_profile()
        if not profile:
            return {
                "resume_filename": "",
                "profile": {},
                "created_at": None,
                "updated_at": None,
            }
        return {
            "resume_filename": profile.get("resume_filename", ""),
            "profile": profile.get("profile_json") or {},
            "created_at": profile.get("created_at"),
            "updated_at": profile.get("updated_at"),
        }

    def queue_profile_generation(self, resume_text: str, resume_filename: str) -> str:
        job_id = str(uuid4())
        resume_hash = hashlib.sha256(resume_text.encode("utf-8")).hexdigest()
        with self._store() as store:
            existing = store.get_profile()
            if (
                existing
                and existing["resume_text"] == resume_text
                and existing["profile_json"]
            ):
                store.create_background_job(job_id, "profile_generation")
                store.update_background_job(
                    job_id, "completed", {"profile": existing["profile_json"]}
                )
                return job_id
            store.save_profile(resume_text, resume_filename, {})
            store.create_background_job(
                job_id,
                "profile_generation",
                {
                    "resume_hash": resume_hash,
                    "resume_text": resume_text,
                    "resume_filename": resume_filename,
                },
            )
        return job_id

    def run_profile_generation(self, job_id: str) -> None:
        try:
            with self._store() as store:
                job = store.get_background_job(job_id)
                profile_row = store.get_profile()
                if not job or not profile_row:
                    return
                if job["status"] == "completed":
                    return
                store.update_background_job(job_id, "running")
            job_payload = job.get("result_json") or {}
            resume_text = job_payload.get("resume_text", profile_row["resume_text"])
            resume_filename = job_payload.get(
                "resume_filename", profile_row["resume_filename"]
            )
            profile = create_profile_from_text(self.config, resume_text, persist=False)
            with self._store() as store:
                current = store.get_profile()
                if not current or current["resume_text"] != resume_text:
                    store.update_background_job(
                        job_id,
                        "completed",
                        {
                            "stale": True,
                            "message": "A newer resume upload superseded this job.",
                        },
                    )
                    return
                store.save_profile(resume_text, resume_filename, profile)
                store.update_background_job(job_id, "completed", {"profile": profile})
        except Exception as error:  # noqa: BLE001 - persist failure for polling clients
            with self._store() as store:
                store.update_background_job(job_id, "failed", error=str(error))

    def queue_matching(self) -> str:
        with self._store() as store:
            profile = store.get_profile()
            if not profile or not profile["profile_json"]:
                raise ValueError("Upload a resume before running matching")
            active = store.get_active_background_job("matching")
            if active:
                return active["job_id"]
            job_id = str(uuid4())
            store.create_background_job(job_id, "matching")
        return job_id

    def queue_scan(self) -> str:
        """Queue a job scan.

        The scan runs shared profile-independent ingestion to populate the
        public corpus, then records the result as a user-visible background
        job.  A profile is still required so that the user has something to
        match against once the corpus is populated, but the ingestion itself
        no longer filters by profile.
        """
        with self._store() as store:
            profile = store.get_profile()
            if not profile or not profile["profile_json"]:
                raise ValueError("Upload a resume before scanning for jobs")
            active = store.get_active_background_job("scan")
            if active:
                return active["job_id"]
            job_id = str(uuid4())
            store.create_background_job(job_id, "scan")
        return job_id

    def run_scan_job(self, job_id: str) -> None:
        """Execute a scan: run shared ingestion then update the background job."""
        try:
            with self._store() as store:
                job = store.get_background_job(job_id)
                if not job:
                    return
                store.update_background_job(job_id, "running")

            ingestion = IngestionService(self.config)
            run_id = ingestion.queue_run(
                trigger="user_scan",
                trigger_user_id=self.user_id,
            )
            ingestion.run_ingestion(run_id)
            run = ingestion.get_run(run_id)
            result = run.get("result") if run else {}
            total = result.get("jobs_upserted", 0) if isinstance(result, dict) else 0

            with self._store() as store:
                store.update_background_job(
                    job_id,
                    "completed",
                    {"new_jobs": total, "ingestion_run_id": run_id},
                )
        except Exception as error:  # noqa: BLE001 - persist failure for polling clients
            with self._store() as store:
                store.update_background_job(job_id, "failed", error=str(error))

    def get_background_job(self, job_id: str) -> dict | None:
        with self._store() as store:
            job = store.get_background_job(job_id)
        if not job:
            return None
        result = job["result_json"]
        if job["kind"] == "profile_generation" and isinstance(result, dict):
            result = {
                key: value for key, value in result.items() if key != "resume_text"
            }
        return {
            "job_id": job["job_id"],
            "kind": job["kind"],
            "status": job["status"],
            "result": result,
            "error": job["error"],
            "created_at": job["created_at"],
            "updated_at": job["updated_at"],
        }

    def run_matching_job(self, job_id: str) -> None:
        with self._store() as store:
            job = store.get_background_job(job_id)
            if not job:
                return
            store.update_background_job(job_id, "running")
        try:
            result = self.run_matching(
                progress=lambda value: self._update_matching_progress(job_id, value)
            )
            with self._store() as store:
                store.update_background_job(job_id, "completed", result)
        except Exception as error:  # noqa: BLE001 - persist failure for polling clients
            with self._store() as store:
                store.update_background_job(job_id, "failed", error=str(error))

    def _update_matching_progress(self, job_id: str, value: dict[str, int]) -> None:
        with self._store() as store:
            store.update_background_job(job_id, "running", value)

    def run_matching(
        self, progress: Callable[[dict[str, int]], None] | None = None
    ) -> dict[str, int]:
        with self._store() as store:
            profile_row = store.get_profile()
            if not profile_row:
                raise ValueError("Upload a resume before running matching")
            jobs = [
                job
                for job in store.list_jobs()
                if classify_job(job, profile_row["profile_json"]) == "TARGET"
            ]
            provider = create_provider(self.config)
            analyzed = 0
            skipped = 0
            failed = 0
            processed = 0
            for job in jobs:
                content = {
                    key: job.get(key)
                    for key in ("title", "company", "location", "url", "description")
                }
                job_hash = hashlib.sha256(
                    json.dumps(content, sort_keys=True, ensure_ascii=False).encode(
                        "utf-8"
                    )
                ).hexdigest()
                cached = store.get_match(job["job_id"])
                if cached and cached.get("job_hash") == job_hash:
                    skipped += 1
                    processed += 1
                    if progress:
                        progress({"processed": processed, "total": len(jobs)})
                    continue
                try:
                    result = match_job(
                        self.config, profile_row["profile_json"], job, provider=provider
                    )
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
                processed += 1
                if progress:
                    progress({"processed": processed, "total": len(jobs)})
            return {
                "total": len(jobs),
                "analyzed": analyzed,
                "skipped": skipped,
                "failed": failed,
            }
