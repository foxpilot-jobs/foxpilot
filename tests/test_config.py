from pathlib import Path

import pytest

from career_agent.config import AppConfig, normalize_database_url


def test_normalize_railway_postgres_url() -> None:
    url = "postgresql://user:password@postgres.railway.internal:5432/railway"
    expected = "postgresql+psycopg://user:password@postgres.railway.internal:5432/railway"
    assert normalize_database_url(url) == expected


def test_hosted_runtime_requires_database_url(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RAILWAY_ENVIRONMENT_NAME", "production")
    config = AppConfig(data_dir=tmp_path, database_url=None)
    with pytest.raises(RuntimeError, match="DATABASE_URL is required"):
        _ = config.resolved_database_url


def test_local_runtime_defaults_to_sqlite(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("RAILWAY_ENVIRONMENT", raising=False)
    monkeypatch.delenv("RAILWAY_ENVIRONMENT_NAME", raising=False)
    monkeypatch.delenv("RAILWAY_PROJECT_ID", raising=False)
    monkeypatch.delenv("VERCEL", raising=False)
    config = AppConfig(data_dir=tmp_path, database_url=None)
    assert config.resolved_database_url.startswith("sqlite:///")
