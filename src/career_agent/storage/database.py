"""Portable SQL repository with SQLite as the local default."""

from __future__ import annotations

import hashlib
import json
import re
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Self
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    UniqueConstraint,
    create_engine,
    delete,
    exists,
    or_,
    select,
    update,
)
from sqlalchemy.engine import Engine

_ENGINES: dict[str, Engine] = {}
_INITIALIZED_URLS: set[str] = set()
_ENGINE_LOCK = threading.Lock()


def get_database_url(database: Path | str) -> str:
    if isinstance(database, Path):
        database_path = database.expanduser().resolve()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{database_path}"
    return database


import contextvars
import time

from sqlalchemy import event

_REQUEST_TIMINGS: contextvars.ContextVar[dict | None] = contextvars.ContextVar(
    "request_timings", default=None
)


def _attach_instrumentation(engine: Engine) -> None:
    if getattr(engine, "_has_timing_listeners", False):
        return
    engine._has_timing_listeners = True

    @event.listens_for(engine, "connect")
    def on_connect(dbapi_connection, connection_record):
        ctx = _REQUEST_TIMINGS.get()
        if ctx is not None:
            ctx["events"].append(("driver_connect", time.perf_counter()))

        try:
            orig_rollback = getattr(dbapi_connection, "rollback", None)
            if orig_rollback:

                def traced_rollback(*args, **kwargs):
                    ctx_inner = _REQUEST_TIMINGS.get()
                    t0 = time.perf_counter()
                    if ctx_inner is not None:
                        ctx_inner["events"].append(("dbapi_rollback_start", t0))
                    res = orig_rollback(*args, **kwargs)
                    t1 = time.perf_counter()
                    if ctx_inner is not None:
                        ctx_inner["events"].append(
                            (
                                "dbapi_rollback_end",
                                t1,
                                f"{round((t1 - t0) * 1000, 2)}ms",
                            )
                        )
                    return res

                dbapi_connection.rollback = traced_rollback
        except (AttributeError, TypeError):
            pass

        try:
            orig_commit = getattr(dbapi_connection, "commit", None)
            if orig_commit:

                def traced_commit(*args, **kwargs):
                    ctx_inner = _REQUEST_TIMINGS.get()
                    t0 = time.perf_counter()
                    if ctx_inner is not None:
                        ctx_inner["events"].append(("dbapi_commit_start", t0))
                    res = orig_commit(*args, **kwargs)
                    t1 = time.perf_counter()
                    if ctx_inner is not None:
                        ctx_inner["events"].append(
                            ("dbapi_commit_end", t1, f"{round((t1 - t0) * 1000, 2)}ms")
                        )
                    return res

                dbapi_connection.commit = traced_commit
        except (AttributeError, TypeError):
            pass

    @event.listens_for(engine, "reset")
    def on_reset(dbapi_connection, connection_record, reset_state):
        ctx = _REQUEST_TIMINGS.get()
        if ctx is not None:
            ctx["events"].append(("engine_reset_event", time.perf_counter()))

    @event.listens_for(engine, "checkout")
    def on_checkout(dbapi_connection, connection_record, connection_proxy):
        ctx = _REQUEST_TIMINGS.get()
        if ctx is not None:
            ctx["events"].append(("pool_checkout", time.perf_counter()))

    @event.listens_for(engine, "checkin")
    def on_checkin(dbapi_connection, connection_record):
        ctx = _REQUEST_TIMINGS.get()
        if ctx is not None:
            ctx["events"].append(("pool_checkin", time.perf_counter()))

    @event.listens_for(engine, "invalidate")
    def on_invalidate(dbapi_connection, connection_record, exception):
        ctx = _REQUEST_TIMINGS.get()
        if ctx is not None:
            ctx["events"].append(("pool_invalidate", time.perf_counter()))

    @event.listens_for(engine, "before_cursor_execute")
    def before_cursor_execute(
        conn, cursor, statement, parameters, context, executemany
    ):
        conn.info.setdefault("query_start", []).append(time.perf_counter())
        ctx = _REQUEST_TIMINGS.get()
        if ctx is not None:
            stmt_summary = " ".join(statement.split()[:5])
            ctx["events"].append(
                ("before_cursor_exec", time.perf_counter(), stmt_summary)
            )

    @event.listens_for(engine, "after_cursor_execute")
    def after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
        starts = conn.info.get("query_start", [])
        if starts:
            elapsed_ms = (time.perf_counter() - starts.pop()) * 1000
            ctx = _REQUEST_TIMINGS.get()
            if ctx is not None:
                stmt_summary = " ".join(statement.split()[:5])
                ctx["events"].append(
                    (
                        "after_cursor_exec",
                        time.perf_counter(),
                        stmt_summary,
                        round(elapsed_ms, 2),
                    )
                )
                ctx["queries"].append(
                    {"stmt": stmt_summary, "ms": round(elapsed_ms, 2)}
                )


def get_engine(database: Path | str | Engine) -> Engine:
    if isinstance(database, Engine):
        _attach_instrumentation(database)
        return database
    database_url = get_database_url(database)
    with _ENGINE_LOCK:
        if database_url not in _ENGINES:
            connect_args = (
                {"check_same_thread": False}
                if database_url.startswith("sqlite")
                else {}
            )
            pool_recycle = 300 if not database_url.startswith("sqlite") else -1
            engine = create_engine(
                database_url,
                connect_args=connect_args,
                pool_pre_ping=False,
                pool_recycle=pool_recycle,
            )
            _attach_instrumentation(engine)
            _ENGINES[database_url] = engine
        return _ENGINES[database_url]


def _initialize_schema(engine: Engine) -> None:
    metadata.create_all(engine)
    if engine.dialect.name == "sqlite":
        with engine.begin() as connection:
            columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    "PRAGMA table_info(users)"
                ).fetchall()
            }
            if "password_hash" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE users ADD COLUMN password_hash VARCHAR"
                )
            if "email_verified" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0"
                )
            if "is_active" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE users ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
                )
            if "auth_provider" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE users ADD COLUMN auth_provider VARCHAR"
                )
            if "auth_subject" not in columns:
                connection.exec_driver_sql(
                    "ALTER TABLE users ADD COLUMN auth_subject VARCHAR"
                )
            job_columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    "PRAGMA table_info(jobs)"
                ).fetchall()
            }
            if "is_active" not in job_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE jobs ADD COLUMN is_active BOOLEAN NOT NULL DEFAULT 1"
                )
            if "last_seen_at" not in job_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE jobs ADD COLUMN last_seen_at DATETIME"
                )
            if "inactive_at" not in job_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE jobs ADD COLUMN inactive_at DATETIME"
                )
            if "canonical_key" not in job_columns:
                connection.exec_driver_sql(
                    "ALTER TABLE jobs ADD COLUMN canonical_key VARCHAR"
                )
            bg_columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    "PRAGMA table_info(background_jobs)"
                ).fetchall()
            }
            for col, ddl in (
                (
                    "attempt",
                    "ALTER TABLE background_jobs ADD COLUMN attempt INTEGER NOT NULL DEFAULT 0",
                ),
                (
                    "max_attempts",
                    "ALTER TABLE background_jobs ADD COLUMN max_attempts INTEGER NOT NULL DEFAULT 3",
                ),
                (
                    "lease_owner",
                    "ALTER TABLE background_jobs ADD COLUMN lease_owner VARCHAR",
                ),
                (
                    "lease_expires_at",
                    "ALTER TABLE background_jobs ADD COLUMN lease_expires_at DATETIME",
                ),
                (
                    "error_class",
                    "ALTER TABLE background_jobs ADD COLUMN error_class VARCHAR",
                ),
                (
                    "started_at",
                    "ALTER TABLE background_jobs ADD COLUMN started_at DATETIME",
                ),
                (
                    "idempotency_key",
                    "ALTER TABLE background_jobs ADD COLUMN idempotency_key VARCHAR",
                ),
                (
                    "progress_json",
                    "ALTER TABLE background_jobs ADD COLUMN progress_json JSON",
                ),
            ):
                if col not in bg_columns:
                    connection.exec_driver_sql(ddl)
            JobStore._upgrade_user_owned_tables(connection)
            connection.exec_driver_sql("PRAGMA foreign_keys = ON")
            connection.exec_driver_sql("PRAGMA journal_mode = WAL")


def initialize_database(database: Path | str | Engine) -> Engine:
    engine = get_engine(database)
    url_key = None
    if isinstance(database, (Path, str)):
        url_key = get_database_url(database)

    with _ENGINE_LOCK:
        if url_key is None or url_key not in _INITIALIZED_URLS:
            _initialize_schema(engine)
            if url_key:
                _INITIALIZED_URLS.add(url_key)
    return engine


def dispose_all_engines() -> None:
    with _ENGINE_LOCK:
        for engine in _ENGINES.values():
            engine.dispose()
        _ENGINES.clear()
        _INITIALIZED_URLS.clear()


metadata = MetaData()

users_table = Table(
    "users",
    metadata,
    Column("user_id", String, primary_key=True),
    Column("email", String),
    Column("password_hash", String),
    Column("auth_provider", String),
    Column("auth_subject", String),
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
    Column("attempt", Integer, nullable=False, default=0),
    Column("max_attempts", Integer, nullable=False, default=3),
    Column("lease_owner", String),
    Column("lease_expires_at", DateTime(timezone=True)),
    Column("error_class", String),
    Column("started_at", DateTime(timezone=True)),
    Column("idempotency_key", String, unique=True),
    Column("progress_json", JSON),
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
    Column("is_active", Boolean, nullable=False, default=True),
    Column("last_seen_at", DateTime(timezone=True)),
    Column("inactive_at", DateTime(timezone=True)),
    Column("canonical_key", String),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    UniqueConstraint("source", "source_job_id"),
)

job_listings_table = Table(
    "job_listings",
    metadata,
    Column("listing_id", String, primary_key=True),
    Column("listing_key", String, nullable=False, unique=True),
    Column("job_id", String, nullable=False),
    Column("source", String, nullable=False),
    Column("source_job_id", String, nullable=False),
    Column("url", String, nullable=False, default=""),
    Column("payload_json", JSON, nullable=False),
    Column("availability_status", String, nullable=False, default="active"),
    Column("first_seen_at", DateTime(timezone=True), nullable=False),
    Column("last_seen_at", DateTime(timezone=True), nullable=False),
    Column("last_checked_at", DateTime(timezone=True)),
    Column("unavailable_since", DateTime(timezone=True)),
    Column("check_failures", Integer, nullable=False, default=0),
    Column("status_reason", String),
    Column("visibility", String, nullable=False, default="public"),
    Column("owner_user_id", String),
)

ingestion_runs_table = Table(
    "ingestion_runs",
    metadata,
    Column("run_id", String, primary_key=True),
    Column("status", String, nullable=False),
    Column("trigger", String, nullable=False),
    Column("trigger_user_id", String),
    Column("source_filter", JSON),
    Column("result_json", JSON),
    Column("error", Text),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
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


def _normalise_job_text(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", " ", str(value or "").lower()).strip()


def _job_canonical_key(job: dict) -> str:
    parts = (
        _normalise_job_text(job.get("company")),
        _normalise_job_text(job.get("title")),
        _normalise_job_text(job.get("location")),
    )
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()


def _description_similarity(left: object, right: object) -> float:
    left_words = set(re.findall(r"[a-z0-9]+", str(left or "").lower()))
    right_words = set(re.findall(r"[a-z0-9]+", str(right or "").lower()))
    if not left_words or not right_words:
        return 0.0
    return len(left_words & right_words) / len(left_words | right_words)


class JobStore:
    """Repository shared by CLI, API, and background workers."""

    def __init__(
        self, database: Path | str | Engine, user_id: str = "local-user"
    ) -> None:
        self.user_id = user_id
        self.engine: Engine = initialize_database(database)

    @staticmethod
    def _upgrade_user_owned_tables(connection) -> None:
        """Rebuild pre-user-isolation SQLite tables with composite keys."""
        for table in (matches_table, applications_table):
            columns = {
                row[1]
                for row in connection.exec_driver_sql(
                    f'PRAGMA table_info("{table.name}")'
                ).fetchall()
            }
            if "user_id" in columns:
                continue

            legacy_name = f"{table.name}_legacy"
            connection.exec_driver_sql(
                f'ALTER TABLE "{table.name}" RENAME TO "{legacy_name}"'
            )
            table.create(connection, checkfirst=False)
            copied_columns = [
                column.name for column in table.columns if column.name != "user_id"
            ]
            column_list = ", ".join(f'"{column}"' for column in copied_columns)
            connection.exec_driver_sql(
                f'INSERT INTO "{table.name}" ("user_id", {column_list}) '
                f"SELECT 'local-user', {column_list} FROM \"{legacy_name}\""
            )
            connection.exec_driver_sql(f'DROP TABLE "{legacy_name}"')
            connection.exec_driver_sql(
                f'CREATE INDEX IF NOT EXISTS "idx_{table.name}_user" '
                f'ON "{table.name}" ("user_id")'
            )

    def close(self) -> None:
        pass

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *_args) -> None:
        self.close()

    def create_user(
        self,
        user_id: str,
        email: str,
        password_hash: str | None,
        auth_provider: str | None = None,
        auth_subject: str | None = None,
    ) -> None:
        now = utc_now()
        with self.engine.begin() as connection:
            connection.execute(
                users_table.insert().values(
                    user_id=user_id,
                    email=email,
                    password_hash=password_hash,
                    auth_provider=auth_provider,
                    auth_subject=auth_subject,
                    email_verified=False,
                    is_active=True,
                    created_at=now,
                    updated_at=now,
                )
            )

    def get_user_by_email(self, email: str) -> dict | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(users_table).where(users_table.c.email == email)
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def get_user_by_auth_subject(self, provider: str, subject: str) -> dict | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(users_table).where(
                        users_table.c.auth_provider == provider,
                        users_table.c.auth_subject == subject,
                    )
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def link_auth_subject(self, user_id: str, provider: str, subject: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(users_table)
                .where(users_table.c.user_id == user_id)
                .values(
                    auth_provider=provider,
                    auth_subject=subject,
                    email_verified=True,
                    updated_at=utc_now(),
                )
            )

    def get_user(self, user_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(users_table).where(users_table.c.user_id == user_id)
                )
                .mappings()
                .first()
            )
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

    def get_session_user(
        self, token_hash: str, touch_threshold_minutes: int = 5
    ) -> dict | None:
        ctx = _REQUEST_TIMINGS.get()
        if ctx is not None:
            ctx["events"].append(("get_session_user_start", time.perf_counter()))
        now = utc_now()
        query = (
            select(
                users_table,
                sessions_table.c.session_id,
                sessions_table.c.expires_at,
                sessions_table.c.last_seen_at,
            )
            .join(sessions_table, sessions_table.c.user_id == users_table.c.user_id)
            .where(
                sessions_table.c.token_hash == token_hash,
                sessions_table.c.revoked_at.is_(None),
                sessions_table.c.expires_at > now,
                users_table.c.is_active.is_(True),
            )
        )
        if ctx is not None:
            ctx["events"].append(("conn_acquire_start", time.perf_counter()))
        with self.engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as connection:
            if ctx is not None:
                ctx["events"].append(("conn_acquired_exec_start", time.perf_counter()))
            result_proxy = connection.execute(query)
            if ctx is not None:
                ctx["events"].append(("exec_end_fetch_start", time.perf_counter()))
            row = result_proxy.mappings().first()
            if ctx is not None:
                ctx["events"].append(
                    ("fetch_end_conn_release_start", time.perf_counter())
                )
        if ctx is not None:
            ctx["events"].append(("conn_release_end", time.perf_counter()))

        if not row:
            if ctx is not None:
                ctx["events"].append(("get_session_user_end_none", time.perf_counter()))
            return None

        last_seen = row.get("last_seen_at")
        if isinstance(last_seen, datetime) and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=UTC)
        if last_seen is None or (now - last_seen) > timedelta(
            minutes=touch_threshold_minutes
        ):
            if ctx is not None:
                ctx["events"].append(("touch_update_write_start", time.perf_counter()))
            with self.engine.begin() as connection:
                connection.execute(
                    update(sessions_table)
                    .where(sessions_table.c.session_id == row["session_id"])
                    .values(last_seen_at=now)
                )
            if ctx is not None:
                ctx["events"].append(("touch_update_write_end", time.perf_counter()))
        else:
            if ctx is not None:
                ctx["events"].append(
                    ("touch_update_skipped_fresh", time.perf_counter())
                )

        if ctx is not None:
            ctx["events"].append(("get_session_user_end", time.perf_counter()))
        return dict(row)

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
                .where(
                    sessions_table.c.user_id == user_id,
                    sessions_table.c.revoked_at.is_(None),
                )
                .values(revoked_at=utc_now())
            )

    def cleanup_sessions(self, retention_days: int = 7) -> None:
        cutoff = utc_now() - timedelta(days=retention_days)
        with self.engine.begin() as connection:
            connection.execute(
                delete(sessions_table).where(
                    (sessions_table.c.expires_at < utc_now())
                    | (
                        sessions_table.c.revoked_at.is_not(None)
                        & (sessions_table.c.revoked_at < cutoff)
                    )
                )
            )

    def save_profile(
        self, resume_text: str, resume_filename: str, profile: dict
    ) -> None:
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
                select(profiles_table.c.user_id).where(
                    profiles_table.c.user_id == self.user_id
                )
            ).first()
            if existing:
                connection.execute(
                    update(profiles_table)
                    .where(profiles_table.c.user_id == self.user_id)
                    .values(**values)
                )
            else:
                connection.execute(
                    profiles_table.insert().values(created_at=now, **values)
                )

    def get_profile(self) -> dict | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(profiles_table).where(
                        profiles_table.c.user_id == self.user_id
                    )
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def create_background_job(
        self,
        job_id: str,
        kind: str,
        result: dict | None = None,
        max_attempts: int = 3,
        idempotency_key: str | None = None,
    ) -> None:
        now = utc_now()
        with self.engine.begin() as connection:
            connection.execute(
                background_jobs_table.insert().values(
                    job_id=job_id,
                    user_id=self.user_id,
                    kind=kind,
                    status="queued",
                    result_json=result,
                    attempt=0,
                    max_attempts=max_attempts,
                    idempotency_key=idempotency_key,
                    created_at=now,
                    updated_at=now,
                )
            )

    def get_background_job(self, job_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(background_jobs_table).where(
                        background_jobs_table.c.job_id == job_id,
                        background_jobs_table.c.user_id == self.user_id,
                    )
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def get_active_background_job(self, kind: str) -> dict | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(background_jobs_table)
                    .where(
                        background_jobs_table.c.user_id == self.user_id,
                        background_jobs_table.c.kind == kind,
                        background_jobs_table.c.status.in_(("queued", "running")),
                    )
                    .order_by(background_jobs_table.c.updated_at.desc())
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def claim_next_background_job(
        self,
        worker_id: str = "worker-local",
        lease_duration_minutes: int = 5,
    ) -> dict | None:
        """Atomically claim queued work or work whose lease has expired.

        Sets the lease owner, extends the lease expiry, and increments the
        attempt counter.  Jobs that have exhausted their max_attempts are
        moved to ``dead_letter`` instead of being claimed.
        """
        now = utc_now()
        with self.engine.begin() as connection:
            candidate = (
                connection.execute(
                    select(background_jobs_table)
                    .where(
                        or_(
                            background_jobs_table.c.status == "queued",
                            (background_jobs_table.c.status == "running")
                            & (
                                background_jobs_table.c.lease_expires_at.is_(None)
                                | (background_jobs_table.c.lease_expires_at < now)
                            ),
                        )
                    )
                    .order_by(background_jobs_table.c.created_at)
                    .limit(1)
                )
                .mappings()
                .first()
            )
            if not candidate:
                return None

            next_attempt = (candidate["attempt"] or 0) + 1
            max_attempts = candidate["max_attempts"] or 3

            # Exhausted retries → dead-letter rather than re-claiming.
            if next_attempt > max_attempts:
                connection.execute(
                    update(background_jobs_table)
                    .where(
                        background_jobs_table.c.job_id == candidate["job_id"],
                        background_jobs_table.c.status == candidate["status"],
                        background_jobs_table.c.updated_at == candidate["updated_at"],
                    )
                    .values(
                        status="dead_letter",
                        error=candidate["error"] or "Max attempts exhausted",
                        error_class="permanent",
                        updated_at=now,
                    )
                )
                return None

            lease_expires = now + timedelta(minutes=lease_duration_minutes)
            claimed = connection.execute(
                update(background_jobs_table)
                .where(
                    background_jobs_table.c.job_id == candidate["job_id"],
                    background_jobs_table.c.status == candidate["status"],
                    background_jobs_table.c.updated_at == candidate["updated_at"],
                )
                .values(
                    status="running",
                    attempt=next_attempt,
                    lease_owner=worker_id,
                    lease_expires_at=lease_expires,
                    started_at=now if next_attempt == 1 else candidate["started_at"],
                    updated_at=now,
                )
            )
            if claimed.rowcount != 1:
                return None
        claimed_job = dict(candidate)
        claimed_job["status"] = "running"
        claimed_job["attempt"] = next_attempt
        claimed_job["lease_owner"] = worker_id
        claimed_job["lease_expires_at"] = lease_expires
        return claimed_job

    def recover_interrupted_background_jobs(self) -> None:
        """Re-queue retryable interrupted jobs; dead-letter exhausted ones."""
        now = utc_now()
        with self.engine.begin() as connection:
            # Jobs that still have retry budget → back to queued
            connection.execute(
                update(background_jobs_table)
                .where(
                    background_jobs_table.c.status == "running",
                    background_jobs_table.c.attempt
                    < background_jobs_table.c.max_attempts,
                )
                .values(
                    status="queued",
                    error="Job interrupted by a process restart. Will retry.",
                    error_class="retryable",
                    lease_owner=None,
                    lease_expires_at=None,
                    updated_at=now,
                )
            )
            # Jobs that exhausted retries → dead letter
            connection.execute(
                update(background_jobs_table)
                .where(
                    background_jobs_table.c.status == "running",
                    background_jobs_table.c.attempt
                    >= background_jobs_table.c.max_attempts,
                )
                .values(
                    status="dead_letter",
                    error="Job interrupted after exhausting all retry attempts.",
                    error_class="permanent",
                    lease_owner=None,
                    lease_expires_at=None,
                    updated_at=now,
                )
            )

    def update_background_job(
        self,
        job_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
        error_class: str | None = None,
        progress: dict | None = None,
    ) -> None:
        values: dict = {"status": status, "updated_at": utc_now()}
        if result is not None:
            values["result_json"] = result
        if error is not None:
            values["error"] = error
        if error_class is not None:
            values["error_class"] = error_class
        if progress is not None:
            values["progress_json"] = progress
        # Clear lease on terminal states
        if status in ("completed", "failed", "dead_letter"):
            values["lease_owner"] = None
            values["lease_expires_at"] = None
        with self.engine.begin() as connection:
            connection.execute(
                update(background_jobs_table)
                .where(
                    background_jobs_table.c.job_id == job_id,
                    background_jobs_table.c.user_id == self.user_id,
                )
                .values(**values)
            )

    def heartbeat_background_job(
        self,
        job_id: str,
        worker_id: str,
        lease_duration_minutes: int = 5,
        progress: dict | None = None,
    ) -> bool:
        """Extend the lease for a running job.  Returns True if the extension succeeded."""
        now = utc_now()
        values: dict = {
            "lease_expires_at": now + timedelta(minutes=lease_duration_minutes),
            "updated_at": now,
        }
        if progress is not None:
            values["progress_json"] = progress
        with self.engine.begin() as connection:
            result = connection.execute(
                update(background_jobs_table)
                .where(
                    background_jobs_table.c.job_id == job_id,
                    background_jobs_table.c.lease_owner == worker_id,
                    background_jobs_table.c.status == "running",
                )
                .values(**values)
            )
        return result.rowcount == 1

    def fail_background_job_retryable(
        self,
        job_id: str,
        error: str,
    ) -> None:
        """Mark a job as failed with retryable classification.

        If the job still has retry budget it goes back to ``queued``.
        Otherwise it moves to ``dead_letter``.
        """
        now = utc_now()
        with self.engine.begin() as connection:
            row = (
                connection.execute(
                    select(
                        background_jobs_table.c.attempt,
                        background_jobs_table.c.max_attempts,
                    ).where(
                        background_jobs_table.c.job_id == job_id,
                        background_jobs_table.c.user_id == self.user_id,
                    )
                )
                .mappings()
                .first()
            )
            if not row:
                return
            attempt = row["attempt"] or 0
            max_attempts = row["max_attempts"] or 3
            if attempt < max_attempts:
                connection.execute(
                    update(background_jobs_table)
                    .where(
                        background_jobs_table.c.job_id == job_id,
                        background_jobs_table.c.user_id == self.user_id,
                    )
                    .values(
                        status="queued",
                        error=error,
                        error_class="retryable",
                        lease_owner=None,
                        lease_expires_at=None,
                        updated_at=now,
                    )
                )
            else:
                connection.execute(
                    update(background_jobs_table)
                    .where(
                        background_jobs_table.c.job_id == job_id,
                        background_jobs_table.c.user_id == self.user_id,
                    )
                    .values(
                        status="dead_letter",
                        error=error,
                        error_class="permanent",
                        lease_owner=None,
                        lease_expires_at=None,
                        updated_at=now,
                    )
                )

    # -- Ingestion runs (shared corpus, not user-scoped) --

    def create_ingestion_run(
        self,
        run_id: str,
        trigger: str,
        trigger_user_id: str | None = None,
        source_filter: dict | None = None,
    ) -> None:
        now = utc_now()
        with self.engine.begin() as connection:
            connection.execute(
                ingestion_runs_table.insert().values(
                    run_id=run_id,
                    status="queued",
                    trigger=trigger,
                    trigger_user_id=trigger_user_id,
                    source_filter=source_filter,
                    created_at=now,
                    updated_at=now,
                )
            )

    def get_ingestion_run(self, run_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(ingestion_runs_table).where(
                        ingestion_runs_table.c.run_id == run_id
                    )
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

    def update_ingestion_run(
        self,
        run_id: str,
        status: str,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        values: dict = {"status": status, "updated_at": utc_now()}
        if result is not None:
            values["result_json"] = result
        if error is not None:
            values["error"] = error
        with self.engine.begin() as connection:
            connection.execute(
                update(ingestion_runs_table)
                .where(ingestion_runs_table.c.run_id == run_id)
                .values(**values)
            )

    def get_active_ingestion_run(self) -> dict | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(ingestion_runs_table)
                    .where(ingestion_runs_table.c.status.in_(("queued", "running")))
                    .order_by(ingestion_runs_table.c.updated_at.desc())
                )
                .mappings()
                .first()
            )
        return dict(row) if row else None

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
            row = (
                connection.execute(
                    select(auth_tokens_table).where(
                        auth_tokens_table.c.token_hash == token_hash,
                        auth_tokens_table.c.purpose == purpose,
                        auth_tokens_table.c.used_at.is_(None),
                        auth_tokens_table.c.expires_at > now,
                    )
                )
                .mappings()
                .first()
            )
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

    def bulk_upsert_jobs(self, jobs: list[dict]) -> dict[str, int]:
        if not jobs:
            return {"inserted": 0, "updated": 0, "deduplicated": 0}

        now = utc_now()
        prepared_jobs = []
        for job in jobs:
            source = job.get("source", "unknown")
            source_job_id = str(job.get("source_job_id", self.job_id(job)))
            visibility = job.get("visibility", "public")
            owner_user_id = (
                job.get("owner_user_id") if visibility == "private" else None
            )
            if visibility not in {"public", "private"} or (
                visibility == "private" and not owner_user_id
            ):
                raise ValueError("Private jobs require an owner_user_id")
            listing_key = f"{visibility}:{owner_user_id or ''}:{source}:{source_job_id}"
            canonical_key = _job_canonical_key(job)
            prepared_jobs.append(
                {
                    "raw": job,
                    "source": source,
                    "source_job_id": source_job_id,
                    "visibility": visibility,
                    "owner_user_id": owner_user_id,
                    "listing_key": listing_key,
                    "canonical_key": canonical_key,
                }
            )

        listing_keys = [pj["listing_key"] for pj in prepared_jobs]
        canonical_keys = [
            pj["canonical_key"] for pj in prepared_jobs if pj["visibility"] == "public"
        ]

        with self.engine.begin() as connection:
            existing_listings_rows = (
                connection.execute(
                    select(
                        job_listings_table.c.listing_key, job_listings_table.c.job_id
                    ).where(job_listings_table.c.listing_key.in_(listing_keys))
                )
                .mappings()
                .all()
            )
            existing_listings: dict[str, str] = {
                row["listing_key"]: row["job_id"] for row in existing_listings_rows
            }

            existing_candidates_rows = []
            if canonical_keys:
                existing_candidates_rows = (
                    connection.execute(
                        select(jobs_table).where(
                            jobs_table.c.canonical_key.in_(canonical_keys)
                        )
                    )
                    .mappings()
                    .all()
                )

            candidates_by_canonical_key: dict[str, list[dict]] = {}
            for row in existing_candidates_rows:
                ckey = row["canonical_key"]
                if ckey not in candidates_by_canonical_key:
                    candidates_by_canonical_key[ckey] = []
                candidates_by_canonical_key[ckey].append(dict(row))

            inserted_count = 0
            updated_count = 0
            deduplicated_count = 0

            jobs_to_insert: list[dict] = []
            jobs_to_update_ids: set[str] = set()
            listings_to_insert: list[dict] = []
            listings_to_update: list[dict] = []

            batch_job_ids_by_listing: dict[str, str] = {}
            batch_jobs_by_id: dict[str, dict] = {}

            for item in prepared_jobs:
                job = item["raw"]
                source = item["source"]
                source_job_id = item["source_job_id"]
                visibility = item["visibility"]
                owner_user_id = item["owner_user_id"]
                listing_key = item["listing_key"]
                canonical_key = item["canonical_key"]

                job_id = existing_listings.get(
                    listing_key
                ) or batch_job_ids_by_listing.get(listing_key)
                is_existing_listing = bool(job_id)

                if not job_id and visibility == "public":
                    candidates = candidates_by_canonical_key.get(canonical_key, [])
                    for candidate in candidates:
                        if (
                            _description_similarity(
                                job.get("description"), candidate.get("description")
                            )
                            >= 0.75
                        ):
                            job_id = candidate["job_id"]
                            deduplicated_count += 1
                            break

                    if not job_id:
                        for b_job in batch_jobs_by_id.values():
                            if (
                                b_job["canonical_key"] == canonical_key
                                and _description_similarity(
                                    job.get("description"), b_job.get("description")
                                )
                                >= 0.75
                            ):
                                job_id = b_job["job_id"]
                                deduplicated_count += 1
                                break

                if not job_id:
                    job_id = self.job_id(job)
                    if visibility == "private":
                        job_id = f"private_{owner_user_id}_{job_id}"

                    new_job_record = {
                        "job_id": job_id,
                        "source": source,
                        "source_job_id": source_job_id,
                        "title": job.get("title", ""),
                        "company": job.get("company", ""),
                        "location": job.get("location", ""),
                        "url": job.get("url", ""),
                        "description": job.get("description", ""),
                        "first_published": job.get("first_published"),
                        "work_type": job.get("work_type"),
                        "payload_json": job,
                        "is_active": True,
                        "last_seen_at": now,
                        "canonical_key": canonical_key,
                        "created_at": now,
                        "updated_at": now,
                    }
                    jobs_to_insert.append(new_job_record)
                    batch_jobs_by_id[job_id] = new_job_record
                    inserted_count += 1
                else:
                    jobs_to_update_ids.add(job_id)
                    if is_existing_listing:
                        updated_count += 1

                batch_job_ids_by_listing[listing_key] = job_id

                listing_values = {
                    "job_id": job_id,
                    "listing_key": listing_key,
                    "source": source,
                    "source_job_id": source_job_id,
                    "url": job.get("url", ""),
                    "payload_json": job,
                    "availability_status": "active",
                    "last_seen_at": now,
                    "last_checked_at": now,
                    "unavailable_since": None,
                    "check_failures": 0,
                    "status_reason": None,
                    "visibility": visibility,
                    "owner_user_id": owner_user_id,
                }

                if is_existing_listing:
                    listings_to_update.append(listing_values)
                else:
                    listings_to_insert.append(
                        {
                            "listing_id": str(uuid4()),
                            "first_seen_at": now,
                            **listing_values,
                        }
                    )

            if jobs_to_insert:
                connection.execute(jobs_table.insert(), jobs_to_insert)

            if jobs_to_update_ids:
                connection.execute(
                    update(jobs_table)
                    .where(jobs_table.c.job_id.in_(list(jobs_to_update_ids)))
                    .values(
                        is_active=True,
                        inactive_at=None,
                        last_seen_at=now,
                        updated_at=now,
                    )
                )

            if listings_to_insert:
                connection.execute(job_listings_table.insert(), listings_to_insert)

            for l_val in listings_to_update:
                connection.execute(
                    update(job_listings_table)
                    .where(job_listings_table.c.listing_key == l_val["listing_key"])
                    .values(**l_val)
                )

        return {
            "inserted": inserted_count,
            "updated": updated_count,
            "deduplicated": deduplicated_count,
        }

    def upsert_job(self, job: dict) -> str:
        source = job.get("source", "unknown")
        source_job_id = str(job.get("source_job_id", self.job_id(job)))
        visibility = job.get("visibility", "public")
        owner_user_id = job.get("owner_user_id") if visibility == "private" else None
        if visibility not in {"public", "private"} or (
            visibility == "private" and not owner_user_id
        ):
            raise ValueError("Private jobs require an owner_user_id")
        listing_key = f"{visibility}:{owner_user_id or ''}:{source}:{source_job_id}"
        self.bulk_upsert_jobs([job])
        with self.engine.connect() as connection:
            row = connection.execute(
                select(job_listings_table.c.job_id).where(
                    job_listings_table.c.listing_key == listing_key,
                )
            ).first()
            return row[0] if row else self.job_id(job)

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

    def _build_jobs_from_rows(self, rows: list, connection) -> list[dict]:
        if not rows:
            return []
        job_ids = [row["job_id"] for row in rows]
        listings_query = (
            select(
                job_listings_table.c.job_id,
                job_listings_table.c.source,
                job_listings_table.c.source_job_id,
                job_listings_table.c.url,
                job_listings_table.c.availability_status,
                job_listings_table.c.last_seen_at,
                job_listings_table.c.last_checked_at,
            )
            .where(job_listings_table.c.job_id.in_(job_ids))
            .order_by(job_listings_table.c.source)
        )
        listings_rows = connection.execute(listings_query).mappings().all()
        listings_by_job: dict[str, list[dict]] = {}
        for listing in listings_rows:
            jid = listing["job_id"]
            if jid not in listings_by_job:
                listings_by_job[jid] = []
            listings_by_job[jid].append(
                {
                    "source": listing["source"],
                    "source_job_id": listing["source_job_id"],
                    "url": listing["url"],
                    "availability_status": listing["availability_status"],
                    "last_seen_at": listing["last_seen_at"],
                    "last_checked_at": listing["last_checked_at"],
                }
            )

        results = []
        for row in rows:
            job = dict(row["payload_json"])
            job["job_id"] = row["job_id"]
            job["local_relevance"] = row["local_relevance"]
            job["is_active"] = row["is_active"]
            job["last_seen_at"] = row["last_seen_at"]
            job_listings = listings_by_job.get(row["job_id"])
            if not job_listings:
                job_listings = [
                    {
                        "source": row["source"],
                        "source_job_id": row["source_job_id"],
                        "url": row["url"],
                        "availability_status": "active"
                        if row["is_active"]
                        else "inactive",
                        "last_seen_at": row["last_seen_at"],
                        "last_checked_at": None,
                    }
                ]
            job["sources"] = job_listings
            results.append(job)
        return results

    def get_job(self, job_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(jobs_table)
                    .where(jobs_table.c.job_id == job_id)
                    .where(self._visible_job_filter(job_id))
                )
                .mappings()
                .first()
            )
            if not row:
                return None
            return self._build_jobs_from_rows([row], connection)[0]

    def list_jobs(
        self, relevance: str | None = None, include_inactive: bool = False
    ) -> list[dict]:
        query = select(jobs_table).order_by(jobs_table.c.updated_at.desc())
        if relevance:
            query = query.where(jobs_table.c.local_relevance == relevance)
        if not include_inactive:
            query = query.where(jobs_table.c.is_active.is_(True))
        query = query.where(self._visible_job_filter(jobs_table.c.job_id))
        with self.engine.connect() as connection:
            rows = connection.execute(query).mappings().all()
            return self._build_jobs_from_rows(rows, connection)

    def set_relevance(self, job_id: str, relevance: str) -> None:
        with self.engine.begin() as connection:
            connection.execute(
                update(jobs_table)
                .where(jobs_table.c.job_id == job_id)
                .values(local_relevance=relevance, updated_at=utc_now())
            )

    def mark_listing_inactive(
        self, source: str, source_job_id: str, reason: str
    ) -> None:
        now = utc_now()
        with self.engine.begin() as connection:
            listing = (
                connection.execute(
                    select(
                        job_listings_table.c.job_id,
                        job_listings_table.c.unavailable_since,
                    ).where(
                        job_listings_table.c.source == source,
                        job_listings_table.c.source_job_id == source_job_id,
                    )
                )
                .mappings()
                .first()
            )
            if not listing:
                return
            connection.execute(
                update(job_listings_table)
                .where(
                    job_listings_table.c.source == source,
                    job_listings_table.c.source_job_id == source_job_id,
                )
                .values(
                    availability_status="inactive",
                    last_checked_at=now,
                    unavailable_since=listing["unavailable_since"] or now,
                    check_failures=job_listings_table.c.check_failures + 1,
                    status_reason=reason,
                )
            )
            active_listing = connection.execute(
                select(job_listings_table.c.listing_id).where(
                    job_listings_table.c.job_id == listing["job_id"],
                    job_listings_table.c.availability_status == "active",
                )
            ).first()
            if not active_listing:
                connection.execute(
                    update(jobs_table)
                    .where(jobs_table.c.job_id == listing["job_id"])
                    .values(is_active=False, inactive_at=now, updated_at=now)
                )

    def mark_listing_active(self, source: str, source_job_id: str) -> None:
        now = utc_now()
        with self.engine.begin() as connection:
            listing = connection.execute(
                select(job_listings_table.c.job_id).where(
                    job_listings_table.c.source == source,
                    job_listings_table.c.source_job_id == source_job_id,
                )
            ).first()
            if not listing:
                return
            connection.execute(
                update(job_listings_table)
                .where(
                    job_listings_table.c.source == source,
                    job_listings_table.c.source_job_id == source_job_id,
                )
                .values(
                    availability_status="active",
                    last_checked_at=now,
                    check_failures=0,
                    unavailable_since=None,
                    status_reason=None,
                )
            )
            connection.execute(
                update(jobs_table)
                .where(jobs_table.c.job_id == listing[0])
                .values(is_active=True, inactive_at=None, updated_at=now)
            )

    def list_listings_for_check(
        self, limit: int = 100, stale_after_hours: int = 24
    ) -> list[dict]:
        cutoff = utc_now() - timedelta(hours=stale_after_hours)
        query = (
            select(job_listings_table)
            .where(
                job_listings_table.c.url != "",
                job_listings_table.c.visibility == "public",
                job_listings_table.c.availability_status != "inactive",
                or_(
                    job_listings_table.c.last_checked_at.is_(None),
                    job_listings_table.c.last_checked_at < cutoff,
                ),
            )
            .order_by(job_listings_table.c.last_checked_at)
            .limit(limit)
        )
        with self.engine.connect() as connection:
            return [dict(row) for row in connection.execute(query).mappings().all()]

    def _visible_job_filter(self, job_id_column):
        return exists(
            select(job_listings_table.c.listing_id).where(
                job_listings_table.c.job_id == job_id_column,
                or_(
                    job_listings_table.c.visibility == "public",
                    job_listings_table.c.owner_user_id == self.user_id,
                ),
            )
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
                connection.execute(
                    matches_table.insert().values(created_at=now, **values)
                )

    def get_match(self, job_id: str) -> dict | None:
        with self.engine.connect() as connection:
            row = (
                connection.execute(
                    select(matches_table).where(
                        matches_table.c.user_id == self.user_id,
                        matches_table.c.job_id == job_id,
                    )
                )
                .mappings()
                .first()
            )
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

    def save_application(
        self, job_id: str, status: str = "saved", notes: str = ""
    ) -> None:
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
            row = (
                connection.execute(
                    select(applications_table).where(
                        applications_table.c.user_id == self.user_id,
                        applications_table.c.job_id == job_id,
                    )
                )
                .mappings()
                .first()
            )
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

    def _job_from_row(self, row) -> dict:
        with self.engine.connect() as connection:
            return self._build_jobs_from_rows([row], connection)[0]

    @staticmethod
    def _match_from_row(row) -> dict:
        return {
            "job_id": row["job_id"],
            "job_hash": row["job_hash"],
            "provider": row["provider"],
            "model": row["model"],
            "match": row["result_json"],
        }
