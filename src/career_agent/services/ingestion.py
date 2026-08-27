"""Shared ingestion service — populates the public job corpus without a user profile."""

from __future__ import annotations

from uuid import uuid4

from ..config import AppConfig
from ..sources import fetch_configured_sources
from ..storage import JobStore


class IngestionService:
    """Operates on the shared job corpus. Not user-scoped."""

    def __init__(self, config: AppConfig) -> None:
        self.config = config

    def _store(self) -> JobStore:
        return JobStore(self.config.resolved_database_url)

    def queue_run(
        self,
        trigger: str = "api",
        trigger_user_id: str | None = None,
        source_filter: dict | None = None,
    ) -> str:
        """Create a queued ingestion run, reusing an active one if present."""
        with self._store() as store:
            active = store.get_active_ingestion_run()
            if active:
                return active["run_id"]
            run_id = str(uuid4())
            store.create_ingestion_run(
                run_id,
                trigger=trigger,
                trigger_user_id=trigger_user_id,
                source_filter=source_filter,
            )
        return run_id

    def run_ingestion(self, run_id: str) -> None:
        """Execute the ingestion run: fetch all public sources without profile filtering."""
        try:
            with self._store() as store:
                run = store.get_ingestion_run(run_id)
                if not run:
                    return
                if run["status"] not in ("queued", "running"):
                    return
                store.update_ingestion_run(run_id, "running")

            res = fetch_configured_sources(None, "system")
            result = res if isinstance(res, dict) else {"jobs_upserted": res}

            with self._store() as store:
                store.update_ingestion_run(
                    run_id,
                    "completed",
                    result=result,
                )
        except Exception as error:  # noqa: BLE001 - persist failure for polling clients
            with self._store() as store:
                store.update_ingestion_run(run_id, "failed", error=str(error))

    def get_run(self, run_id: str) -> dict | None:
        """Return a serialisable ingestion run record."""
        with self._store() as store:
            run = store.get_ingestion_run(run_id)
        if not run:
            return None
        return {
            "run_id": run["run_id"],
            "status": run["status"],
            "trigger": run["trigger"],
            "trigger_user_id": run["trigger_user_id"],
            "result": run["result_json"],
            "error": run["error"],
            "created_at": run["created_at"],
            "updated_at": run["updated_at"],
        }
