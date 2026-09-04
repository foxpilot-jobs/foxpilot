"""Use-case services for the FoxPilot product."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import uuid4

from filter_jobs import classify_job

from ..config import AppConfig
from ..llm import LLMError, create_provider, is_rate_limit_error
from ..matching import match_job
from ..profile import create_profile_from_text
from ..storage import JobStore
from ..storage.database import compute_preference_hash
from ..worker_errors import classify_error
from .ingestion import IngestionService


class CareerService:
    def __init__(self, config: AppConfig, user_id: str = "local-user") -> None:
        self.config = config
        self.user_id = user_id

    def _store(self) -> JobStore:
        return JobStore(self.config.resolved_database_url, user_id=self.user_id)

    def get_workspace_preferences(self, workspace_id: str | None = None) -> dict:
        with self._store() as store:
            return store.get_workspace_preferences(workspace_id)

    def update_workspace_preferences(
        self,
        target_roles: list[str],
        work_arrangement: str,
        preferred_locations: list[str],
        workspace_id: str | None = None,
    ) -> dict:
        with self._store() as store:
            return store.update_workspace_preferences(
                target_roles, work_arrangement, preferred_locations, workspace_id
            )

    def list_jobs(self, **kwargs) -> dict:
        with self._store() as store:
            return store.list_jobs(**kwargs)

    def get_job(self, job_id: str) -> dict | None:
        with self._store() as store:
            return store.get_job(job_id)

    def get_job_detail(self, job_id: str) -> dict | None:
        with self._store() as store:
            job = store.get_job(job_id)
            if job is None:
                return None
            return {
                **job,
                "match": (store.get_match(job_id) or {}).get("match"),
                "application": store.get_application(job_id),
            }

    def list_matches(self, **kwargs) -> dict:
        with self._store() as store:
            return store.list_matches(**kwargs)

    def get_application(self, job_id: str) -> dict | None:
        with self._store() as store:
            return store.get_application(job_id)

    def list_applications(self, **kwargs) -> dict:
        with self._store() as store:
            return store.list_applications(**kwargs)

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
                "workspace_id": None,
            }
        return {
            "resume_filename": profile.get("resume_filename", ""),
            "profile": profile.get("profile_json") or {},
            "created_at": profile.get("created_at"),
            "updated_at": profile.get("updated_at"),
            "workspace_id": profile.get("workspace_id"),
        }

    def list_workspaces(self) -> list[dict]:
        with self._store() as store:
            return store.list_workspaces()

    def create_workspace(self, name: str) -> dict:
        with self._store() as store:
            return store.create_workspace(name)

    def rename_workspace(self, workspace_id: str, name: str) -> bool:
        with self._store() as store:
            return store.rename_workspace(workspace_id, name)

    def switch_workspace(self, workspace_id: str) -> bool:
        with self._store() as store:
            return store.switch_workspace(workspace_id)

    def delete_workspace(self, workspace_id: str) -> bool:
        with self._store() as store:
            return store.delete_workspace(workspace_id)

    def delete_profile(self) -> bool:
        with self._store() as store:
            return store.delete_profile()

    def delete_resume(self) -> bool:
        with self._store() as store:
            return store.delete_resume()

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
                if not job:
                    return
                ws_id = job.get("workspace_id")
                profile_row = store.get_profile(workspace_id=ws_id)
                if not profile_row:
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
                current = store.get_profile(workspace_id=ws_id)
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
                store.save_profile(
                    resume_text, resume_filename, profile, workspace_id=ws_id
                )
                store.update_background_job(job_id, "completed", {"profile": profile})
        except Exception as error:  # noqa: BLE001 - persist failure for polling clients
            ec = classify_error(error)
            with self._store() as store:
                if ec == "retryable":
                    store.fail_background_job_retryable(
                        job_id,
                        str(error),
                        backoff_seconds=getattr(error, "retry_after_seconds", None),
                    )
                else:
                    store.update_background_job(
                        job_id, "failed", error=str(error), error_class="permanent"
                    )

    def queue_matching(self, max_stale_seconds: int = 600) -> str:
        with self._store() as store:
            profile = store.get_profile()
            if not profile or not profile["profile_json"]:
                raise ValueError("Upload a resume before running matching")
            active = store.get_active_background_job("matching")
            if active:
                now = datetime.now(UTC)
                updated_at = active.get("updated_at") or active.get("created_at") or now
                if updated_at.tzinfo is None:
                    updated_at = updated_at.replace(tzinfo=UTC)
                age_seconds = (now - updated_at).total_seconds()
                if age_seconds > max_stale_seconds:
                    store.update_background_job(
                        active["job_id"],
                        "failed",
                        error="Job execution timed out or stalled.",
                        error_class="stale",
                    )
                else:
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

            # Propagate ingestion failure to the scan background job.
            if run and run.get("status") == "failed":
                raise RuntimeError(run.get("error") or "Ingestion run failed")

            result = run.get("result") if run else {}
            total = result.get("jobs_upserted", 0) if isinstance(result, dict) else 0

            with self._store() as store:
                store.update_background_job(
                    job_id,
                    "completed",
                    {"new_jobs": total, "ingestion_run_id": run_id},
                )
        except Exception as error:  # noqa: BLE001 - persist failure for polling clients
            ec = classify_error(error)
            with self._store() as store:
                if ec == "retryable":
                    store.fail_background_job_retryable(
                        job_id,
                        str(error),
                        backoff_seconds=getattr(error, "retry_after_seconds", None),
                    )
                else:
                    store.update_background_job(
                        job_id, "failed", error=str(error), error_class="permanent"
                    )

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
            "error_class": job.get("error_class"),
            "attempt": job.get("attempt", 0),
            "max_attempts": job.get("max_attempts", 3),
            "progress": job.get("progress_json"),
            "started_at": job.get("started_at"),
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
            ec = classify_error(error)
            with self._store() as store:
                if ec == "retryable":
                    store.fail_background_job_retryable(
                        job_id,
                        str(error),
                        backoff_seconds=getattr(error, "retry_after_seconds", None),
                    )
                else:
                    store.update_background_job(
                        job_id, "failed", error=str(error), error_class="permanent"
                    )

    def _update_matching_progress(self, job_id: str, value: dict[str, int]) -> None:
        with self._store() as store:
            store.update_background_job(job_id, "running", progress=value)

    def run_matching(
        self, progress: Callable[[dict[str, int]], None] | None = None
    ) -> dict[str, int]:
        with self._store() as store:
            profile_row = store.get_profile()
            if not profile_row:
                raise ValueError("Upload a resume before running matching")
            workspace_id = profile_row.get("workspace_id")
            ws_prefs = store.get_workspace_preferences(workspace_id=workspace_id)
            current_pref_hash = compute_preference_hash(
                ws_prefs["target_roles"],
                ws_prefs["work_arrangement"],
                ws_prefs["preferred_locations"],
            )
            all_jobs = store.list_jobs(limit=10000)["items"]
            jobs = [
                job
                for job in all_jobs
                if classify_job(
                    job,
                    profile=profile_row["profile_json"],
                    workspace_preferences=ws_prefs,
                )
                == "TARGET"
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
                cached = store.get_match(
                    job["job_id"],
                    preference_hash=current_pref_hash,
                    workspace_id=workspace_id,
                )
                if (
                    cached
                    and cached.get("job_hash") == job_hash
                    and cached.get("preference_hash") == current_pref_hash
                ):
                    skipped += 1
                    processed += 1
                    if progress:
                        progress({"processed": processed, "total": len(jobs)})
                    continue
                try:
                    try:
                        result = match_job(
                            self.config,
                            profile_row["profile_json"],
                            job,
                            provider=provider,
                            workspace_preferences=ws_prefs,
                        )
                    except TypeError:
                        result = match_job(
                            self.config,
                            profile_row["profile_json"],
                            job,
                            provider=provider,
                        )
                    store.save_match(
                        job["job_id"],
                        job_hash,
                        self.config.llm_provider,
                        self.config.llm_model,
                        result,
                        preference_hash=current_pref_hash,
                        workspace_id=workspace_id,
                    )
                    analyzed += 1
                except LLMError as error:
                    if is_rate_limit_error(error):
                        raise
                    failed += 1
                except ValueError:
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
