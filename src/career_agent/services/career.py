"""Use-case services for the FoxPilot product."""

from __future__ import annotations

from ..config import AppConfig
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
