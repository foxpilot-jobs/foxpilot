"""Portable SQL repository with SQLite as the local default."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    select,
    update,
)
from sqlalchemy.engine import Engine

metadata = MetaData()

jobs_table = Table(
    "jobs",
    metadata,
    Column("job_id", String, primary_key=True),
    Column("source", String, nullable=False),
    Column("source_job_id", String, nullable=False),
    Column("title", String, nullable=False, default=""),
    Column("company", String, nullable=False, default=""),
    Column("location", String, nullable=False, default=""),
    Column("url", String, nullable=False, default=""),
    Column("description", Text, nullable=False, default=""),
    Column("first_published", String),
    Column("work_type", String),
    Column("payload_json", JSON, nullable=False),
    Column("local_relevance", String),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("source", "source_job_id"),
)

matches_table = Table(
    "matches",
    metadata,
    Column("job_id", String, primary_key=True),
    Column("job_hash", String, nullable=False),
    Column("provider", String, nullable=False),
    Column("model", String, nullable=False),
    Column("result_json", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

applications_table = Table(
    "applications",
    metadata,
    Column("job_id", String, primary_key=True),
    Column("status", String, nullable=False, default="saved"),
    Column("notes", Text, nullable=False, default=""),
    Column("applied_at", DateTime(timezone=True)),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)


def utc_now() -> datetime:
    return datetime.now(UTC)


class JobStore:
    """Repository shared by CLI, API, and background workers."""

    def __init__(self, database: Path | str) -> None:
        if isinstance(database, Path):
            database_path = database.expanduser().resolve()
            database_path.parent.mkdir(parents=True, exist_ok=True)
            database_url = f"sqlite:///{database_path}"
        else:
            database_url = database
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(
            database_url,
            connect_args=connect_args,
            pool_pre_ping=True,
        )
        self._initialize()

    def _initialize(self) -> None:
        metadata.create_all(self.engine)
        if self.engine.dialect.name == "sqlite":
            with self.engine.begin() as connection:
                connection.exec_driver_sql("PRAGMA foreign_keys = ON")
                connection.exec_driver_sql("PRAGMA journal_mode = WAL")

    def close(self) -> None:
        self.engine.dispose()

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
        values = {
            "job_id": job_id,
            "source": job.get("source", "unknown"),
            "source_job_id": str(job.get("source_job_id", job_id)),
            "title": job.get("title", ""),
            "company": job.get("company", ""),
            "location": job.get("location", ""),
            "url": job.get("url", ""),
            "description": job.get("description", ""),
            "first_published": job.get("first_published"),
            "work_type": job.get("work_type"),
            "payload_json": job,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(jobs_table.c.job_id).where(jobs_table.c.job_id == job_id)
            ).first()
            if existing:
                connection.execute(
                    update(jobs_table).where(jobs_table.c.job_id == job_id).values(**values)
                )
            else:
                connection.execute(jobs_table.insert().values(created_at=now, **values))
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
        with self.engine.connect() as connection:
            row = connection.execute(
                select(jobs_table).where(jobs_table.c.job_id == job_id)
            ).mappings().first()
        return self._job_from_row(row) if row else None

    def list_jobs(self, relevance: str | None = None) -> list[dict]:
        query = select(jobs_table).order_by(jobs_table.c.updated_at.desc())
        if relevance:
            query = query.where(jobs_table.c.local_relevance == relevance)
        with self.engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [self._job_from_row(row) for row in rows]

    def set_relevance(self, job_id: str, relevance: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(jobs_table)
                .where(jobs_table.c.job_id == job_id)
                .values(local_relevance=relevance, updated_at=utc_now())
            )

    def save_match(
        self,
        job_id: str,
        job_hash: str,
        provider: str,
        model: str,
        result: dict,
    ) -> None:
        now = utc_now()
        values = {
            "job_id": job_id,
            "job_hash": job_hash,
            "provider": provider,
            "model": model,
            "result_json": result,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(matches_table.c.job_id).where(matches_table.c.job_id == job_id)
            ).first()
            if existing:
                connection.execute(
                    update(matches_table).where(matches_table.c.job_id == job_id).values(**values)
                )
            else:
                connection.execute(matches_table.insert().values(created_at=now, **values))

    def get_match(self, job_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(matches_table).where(matches_table.c.job_id == job_id)
            ).mappings().first()
        return self._match_from_row(row) if row else None

    def list_matches(self) -> list[dict]:
        query = (
            select(matches_table, jobs_table.c.payload_json)
            .join(jobs_table, jobs_table.c.job_id == matches_table.c.job_id)
            .order_by(matches_table.c.updated_at.desc())
        )
        with self.engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [
            {
                **self._match_from_row(row),
                "job": row["payload_json"],
            }
            for row in rows
        ]

    def save_application(self, job_id: str, status: str = "saved", notes: str = "") -> None:
        if status not in {"saved", "applied", "interviewing", "rejected", "offered"}:
            raise ValueError(f"Unsupported application status: {status}")
        now = utc_now()
        values = {"job_id": job_id, "status": status, "notes": notes, "updated_at": now}
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(applications_table.c.job_id).where(applications_table.c.job_id == job_id)
            ).first()
            if existing:
                connection.execute(
                    update(applications_table)
                    .where(applications_table.c.job_id == job_id)
                    .values(**values)
                )
            else:
                connection.execute(applications_table.insert().values(**values))

    def get_application(self, job_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(applications_table).where(applications_table.c.job_id == job_id)
            ).mappings().first()
        return dict(row) if row else None

    def list_applications(self) -> list[dict]:
        query = (
            select(applications_table, jobs_table.c.title, jobs_table.c.company)
            .join(jobs_table, jobs_table.c.job_id == applications_table.c.job_id)
            .order_by(applications_table.c.updated_at.desc())
        )
        with self.engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
        return [dict(row) for row in rows]

    @staticmethod
    def _job_from_row(row) -> dict:
        job = dict(row["payload_json"])
        job["job_id"] = row["job_id"]
        job["local_relevance"] = row["local_relevance"]
        return job

    @staticmethod
    def _match_from_row(row) -> dict:
        return {
            "job_id": row["job_id"],
            "job_hash": row["job_hash"],
            "provider": row["provider"],
            "model": row["model"],
            "match": row["result_json"],
        }
