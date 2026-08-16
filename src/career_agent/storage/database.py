"""Portable SQL repository with SQLite as the local default."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Self

from sqlalchemy import (
    JSON,
    Boolean,
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

users_table = Table(
    "users",
    metadata,
    Column("user_id", String, primary_key=True),
    Column("email", String),
    Column("password_hash", String),
    Column("email_verified", Boolean, nullable=False, default=False),
    Column("is_active", Boolean, nullable=False, default=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

sessions_table = Table(
    "sessions",
    metadata,
    Column("session_id", String, primary_key=True),
    Column("user_id", String, nullable=False),
    Column("token_hash", String, nullable=False, unique=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
    Column("revoked_at", DateTime(timezone=True)),
)

auth_tokens_table = Table(
    "auth_tokens",
    metadata,
    Column("token_id", String, primary_key=True),
    Column("user_id", String, nullable=False),
    Column("purpose", String, nullable=False),
    Column("token_hash", String, nullable=False, unique=True),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("used_at", DateTime(timezone=True)),
)

profiles_table = Table(
    "profiles",
    metadata,
    Column("user_id", String, primary_key=True),
    Column("resume_text", Text, nullable=False),
    Column("resume_filename", String, nullable=False),
    Column("profile_json", JSON, nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

background_jobs_table = Table(
    "background_jobs",
    metadata,
    Column("job_id", String, primary_key=True),
    Column("user_id", String, nullable=False),
    Column("kind", String, nullable=False),
    Column("status", String, nullable=False),
    Column("result_json", JSON),
    Column("error", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
)

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
    Column("user_id", String, primary_key=True),
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
    Column("user_id", String, primary_key=True),
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

    def __init__(self, database: Path | str, user_id: str = "local-user") -> None:
        self.user_id = user_id
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
                columns = {
                    row[1]
                    for row in connection.exec_driver_sql("PRAGMA table_info(users)").fetchall()
                }
                if "password_hash" not in columns:
                    connection.exec_driver_sql("ALTER TABLE users ADD COLUMN password_hash VARCHAR")
                if "email_verified" not in columns:
                    connection.exec_driver_sql(
                        "ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0"
                    )
                if "is_active" not in columns:
                    connection.exec_driver_sql(
                        "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
                    )
                self._upgrade_user_owned_tables(connection)
                connection.exec_driver_sql("PRAGMA foreign_keys = ON")
                connection.exec_driver_sql("PRAGMA journal_mode = WAL")

    @staticmethod
    def _upgrade_user_owned_tables(connection) -> None:
        """Rebuild pre-user-isolation SQLite tables with composite keys."""
        for table in (matches_table, applications_table):
            columns = {
                row[1]
                for row in connection.exec_driver_sql(f'PRAGMA table_info("{table.name}")').fetchall()
            }
            if "user_id" in columns:
                continue

            legacy_name = f"{table.name}_legacy"
            connection.exec_driver_sql(
                f'ALTER TABLE "{table.name}" RENAME TO "{legacy_name}"'
            )
            table.create(connection, checkfirst=False)
            copied_columns = [column.name for column in table.columns if column.name != "user_id"]
            column_list = ", ".join(f'"{column}"' for column in copied_columns)
            connection.exec_driver_sql(
                f'INSERT INTO "{table.name}" ("user_id", {column_list}) '
                f'SELECT \'local-user\', {column_list} FROM "{legacy_name}"'
            )
            connection.exec_driver_sql(f'DROP TABLE "{legacy_name}"')
            connection.exec_driver_sql(
                f'CREATE INDEX IF NOT EXISTS "idx_{table.name}_user" '
                f'ON "{table.name}" ("user_id")'
            )

    def close(self) -> None:
        self.engine.dispose()

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def create_user(self, user_id: str, email: str, password_hash: str) -> None:
        now = utc_now()
        with self.engine.begin() as connection:
            connection.execute(
                users_table.insert().values(
                    user_id=user_id,
                    email=email,
                    password_hash=password_hash,
                    email_verified=False,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )

    def get_user_by_email(self, email: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(users_table).where(users_table.c.email == email)
            ).mappings().first()
        return dict(row) if row else None

    def get_user(self, user_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(users_table).where(users_table.c.user_id == user_id)
            ).mappings().first()
        return dict(row) if row else None

    def mark_email_verified(self, user_id: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(users_table)
                .where(users_table.c.user_id == user_id)
                .values(email_verified=True, updated_at=utc_now())
            )

    def update_password(self, user_id: str, password_hash: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(users_table)
                .where(users_table.c.user_id == user_id)
                .values(password_hash=password_hash, updated_at=utc_now())
            )

    def create_session(
        self,
        session_id: str,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        now = utc_now()
        with self.engine.begin() as connection:
            connection.execute(
                sessions_table.insert().values(
                    session_id=session_id,
                    user_id=user_id,
                    token_hash=token_hash,
                    expires_at=expires_at,
                    created_at=now,
                    last_seen_at=now,
                )
            )

    def get_session_user(self, token_hash: str) -> dict | None:
        now = utc_now()
        query = (
            select(users_table, sessions_table.c.session_id, sessions_table.c.expires_at)
            .join(sessions_table, sessions_table.c.user_id == users_table.c.user_id)
            .where(
                sessions_table.c.token_hash == token_hash,
                sessions_table.c.revoked_at.is_(None),
                sessions_table.c.expires_at > now,
                users_table.c.is_active.is_(True),
            )
        )
        with self.engine.begin() as connection:
            row = connection.execute(query).mappings().first()
            if row:
                connection.execute(
                    update(sessions_table)
                    .where(sessions_table.c.session_id == row["session_id"])
                    .values(last_seen_at=now)
                )
        return dict(row) if row else None

    def revoke_session(self, token_hash: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(sessions_table)
                .where(sessions_table.c.token_hash == token_hash)
                .values(revoked_at=utc_now())
            )

    def revoke_user_sessions(self, user_id: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(sessions_table)
                .where(sessions_table.c.user_id == user_id, sessions_table.c.revoked_at.is_(None))
                .values(revoked_at=utc_now())
            )

    def save_profile(self, resume_text: str, resume_filename: str, profile: dict) -> None:
        now = utc_now()
        values = {
            "user_id": self.user_id,
            "resume_text": resume_text,
            "resume_filename": resume_filename,
            "profile_json": profile,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(profiles_table.c.user_id).where(profiles_table.c.user_id == self.user_id)
            ).first()
            if existing:
                connection.execute(
                    update(profiles_table)
                    .where(profiles_table.c.user_id == self.user_id)
                    .values(**values)
                )
            else:
                connection.execute(profiles_table.insert().values(created_at=now, **values))

    def get_profile(self) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(profiles_table).where(profiles_table.c.user_id == self.user_id)
            ).mappings().first()
        return dict(row) if row else None

    def create_background_job(self, job_id: str, kind: str) -> None:
        now = utc_now()
        with self.engine.begin() as connection:
            connection.execute(
                background_jobs_table.insert().values(
                    job_id=job_id,
                    user_id=self.user_id,
                    kind=kind,
                    status="queued",
                    created_at=now,
                    updated_at=now,
                )
            )

    def get_background_job(self, job_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(background_jobs_table).where(
                    background_jobs_table.c.job_id == job_id,
                    background_jobs_table.c.user_id == self.user_id,
                )
            ).mappings().first()
        return dict(row) if row else None

    def update_background_job(
        self,
        job_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(background_jobs_table)
                .where(
                    background_jobs_table.c.job_id == job_id,
                    background_jobs_table.c.user_id == self.user_id,
                )
                .values(
                    status=status,
                    result_json=result,
                    error=error,
                    updated_at=utc_now(),
                )
            )

    def create_auth_token(
        self,
        token_id: str,
        user_id: str,
        purpose: str,
        token_hash: str,
        expires_at: datetime,
    ) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                auth_tokens_table.insert().values(
                    token_id=token_id,
                    user_id=user_id,
                    purpose=purpose,
                    token_hash=token_hash,
                    expires_at=expires_at,
                    created_at=utc_now(),
                )
            )

    def consume_auth_token(self, token_hash: str, purpose: str) -> dict | None:
        now = utc_now()
        with self.engine.begin() as connection:
            row = connection.execute(
                select(auth_tokens_table).where(
                    auth_tokens_table.c.token_hash == token_hash,
                    auth_tokens_table.c.purpose == purpose,
                    auth_tokens_table.c.used_at.is_(None),
                    auth_tokens_table.c.expires_at > now,
                )
            ).mappings().first()
            if not row:
                return None
            connection.execute(
                update(auth_tokens_table)
                .where(auth_tokens_table.c.token_id == row["token_id"])
                .values(used_at=now)
            )
        return dict(row)

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
            "user_id": self.user_id,
            "job_id": job_id,
            "job_hash": job_hash,
            "provider": provider,
            "model": model,
            "result_json": result,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(matches_table.c.job_id).where(
                    matches_table.c.user_id == self.user_id,
                    matches_table.c.job_id == job_id,
                )
            ).first()
            if existing:
                connection.execute(
                    update(matches_table)
                    .where(
                        matches_table.c.user_id == self.user_id,
                        matches_table.c.job_id == job_id,
                    )
                    .values(**values)
                )
            else:
                connection.execute(matches_table.insert().values(created_at=now, **values))

    def get_match(self, job_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(matches_table).where(
                    matches_table.c.user_id == self.user_id,
                    matches_table.c.job_id == job_id,
                )
            ).mappings().first()
        return self._match_from_row(row) if row else None

    def list_matches(self) -> list[dict]:
        query = (
            select(matches_table, jobs_table.c.payload_json)
            .join(jobs_table, jobs_table.c.job_id == matches_table.c.job_id)
            .where(matches_table.c.user_id == self.user_id)
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
        values = {
            "user_id": self.user_id,
            "job_id": job_id,
            "status": status,
            "notes": notes,
            "updated_at": now,
        }
        with self.engine.begin() as connection:
            existing = connection.execute(
                select(applications_table.c.job_id).where(
                    applications_table.c.user_id == self.user_id,
                    applications_table.c.job_id == job_id,
                )
            ).first()
            if existing:
                connection.execute(
                    update(applications_table)
                    .where(
                        applications_table.c.user_id == self.user_id,
                        applications_table.c.job_id == job_id,
                    )
                    .values(**values)
                )
            else:
                connection.execute(applications_table.insert().values(**values))

    def get_application(self, job_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = connection.execute(
                select(applications_table).where(
                    applications_table.c.user_id == self.user_id,
                    applications_table.c.job_id == job_id,
                )
            ).mappings().first()
        return dict(row) if row else None

    def list_applications(self) -> list[dict]:
        query = (
            select(applications_table, jobs_table.c.title, jobs_table.c.company)
            .join(jobs_table, jobs_table.c.job_id == applications_table.c.job_id)
            .where(applications_table.c.user_id == self.user_id)
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
