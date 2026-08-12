"""SQLite repository for jobs, matches, and application state."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Self


def utc_now() -> str:
    return datetime.now(UTC).isoformat()


class JobStore:
    def __init__(self, path: Path) -> None:
        self.path = path.expanduser().resolve()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self._initialize()

    def _initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS jobs (
                job_id TEXT PRIMARY KEY,
                source TEXT NOT NULL,
                source_job_id TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                company TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                description TEXT NOT NULL DEFAULT '',
                first_published TEXT,
                work_type TEXT,
                payload_json TEXT NOT NULL,
                local_relevance TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(source, source_job_id)
            );

            CREATE TABLE IF NOT EXISTS matches (
                job_id TEXT PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
                job_hash TEXT NOT NULL,
                provider TEXT NOT NULL,
                model TEXT NOT NULL,
                result_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS applications (
                job_id TEXT PRIMARY KEY REFERENCES jobs(job_id) ON DELETE CASCADE,
                status TEXT NOT NULL DEFAULT 'saved',
                notes TEXT NOT NULL DEFAULT '',
                applied_at TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_jobs_relevance ON jobs(local_relevance);
            CREATE INDEX IF NOT EXISTS idx_jobs_updated ON jobs(updated_at);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    @staticmethod
    def job_id(job: dict) -> str:
        source = job.get("source", "unknown")
        source_job_id = job.get("source_job_id")
        if source_job_id:
            return f"{source}_{source_job_id}"
        return f"{source}_{job.get('company', 'unknown')}_{job.get('title', 'unknown')}"

    def upsert_job(self, job: dict) -> str:
        job_id = self.job_id(job)
        now = utc_now()
        payload = json.dumps(job, ensure_ascii=False, default=str)
        self.connection.execute(
            """
            INSERT INTO jobs (
                job_id, source, source_job_id, title, company, location, url,
                description, first_published, work_type, payload_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                title = excluded.title,
                company = excluded.company,
                location = excluded.location,
                url = excluded.url,
                description = excluded.description,
                first_published = excluded.first_published,
                work_type = excluded.work_type,
                payload_json = excluded.payload_json,
                updated_at = excluded.updated_at
            """,
            (
                job_id,
                job.get("source", "unknown"),
                str(job.get("source_job_id", job_id)),
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("url", ""),
                job.get("description", ""),
                job.get("first_published"),
                job.get("work_type"),
                payload,
                now,
                now,
            ),
        )
        self.connection.commit()
        return job_id

    def import_legacy_jobs(self, directory: Path) -> int:
        imported = 0
        for path in sorted(directory.glob("*.json")):
            try:
                job = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(job, dict):
                    self.upsert_job(job)
                    imported += 1
            except (OSError, json.JSONDecodeError):
                continue
        return imported

    def get_job(self, job_id: str) -> dict | None:
        row = self.connection.execute(
            "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return self._job_from_row(row) if row else None

    def list_jobs(self, relevance: str | None = None) -> list[dict]:
        if relevance:
            rows = self.connection.execute(
                "SELECT * FROM jobs WHERE local_relevance = ? ORDER BY updated_at DESC",
                (relevance,),
            ).fetchall()
        else:
            rows = self.connection.execute(
                "SELECT * FROM jobs ORDER BY updated_at DESC"
            ).fetchall()
        return [self._job_from_row(row) for row in rows]

    def set_relevance(self, job_id: str, relevance: str) -> None:
        self.connection.execute(
            "UPDATE jobs SET local_relevance = ?, updated_at = ? WHERE job_id = ?",
            (relevance, utc_now(), job_id),
        )
        self.connection.commit()

    def save_match(
        self,
        job_id: str,
        job_hash: str,
        provider: str,
        model: str,
        result: dict,
    ) -> None:
        now = utc_now()
        self.connection.execute(
            """
            INSERT INTO matches (job_id, job_hash, provider, model, result_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                job_hash = excluded.job_hash,
                provider = excluded.provider,
                model = excluded.model,
                result_json = excluded.result_json,
                updated_at = excluded.updated_at
            """,
            (job_id, job_hash, provider, model, json.dumps(result, ensure_ascii=False), now, now),
        )
        self.connection.commit()

    def get_match(self, job_id: str) -> dict | None:
        row = self.connection.execute(
            "SELECT * FROM matches WHERE job_id = ?", (job_id,)
        ).fetchone()
        if not row:
            return None
        return {
            "job_id": row["job_id"],
            "job_hash": row["job_hash"],
            "provider": row["provider"],
            "model": row["model"],
            "match": json.loads(row["result_json"]),
        }

    def save_application(
        self,
        job_id: str,
        status: str = "saved",
        notes: str = "",
    ) -> None:
        if status not in {"saved", "applied", "interviewing", "rejected", "offered"}:
            raise ValueError(f"Unsupported application status: {status}")
        self.connection.execute(
            """
            INSERT INTO applications (job_id, status, notes, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(job_id) DO UPDATE SET
                status = excluded.status,
                notes = excluded.notes,
                updated_at = excluded.updated_at
            """,
            (job_id, status, notes, utc_now()),
        )
        self.connection.commit()

    @staticmethod
    def _job_from_row(row: sqlite3.Row) -> dict:
        job = json.loads(row["payload_json"])
        job["job_id"] = row["job_id"]
        job["local_relevance"] = row["local_relevance"]
        return job
