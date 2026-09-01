"""Local configuration and data paths."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

DEFAULT_DATA_DIR = Path.home() / ".foxpilot"
LEGACY_DATA_DIR = Path.home() / ".career-agent"
DEFAULT_CONFIG_PATH = DEFAULT_DATA_DIR / "config.json"


def normalize_database_url(url: str | None) -> str | None:
    """Use the installed Psycopg 3 driver for generic PostgreSQL URLs."""
    if url and url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def is_hosted_runtime() -> bool:
    """Return True in hosted environments that must use managed PostgreSQL."""
    return any(
        os.getenv(name)
        for name in (
            "RAILWAY_ENVIRONMENT",
            "RAILWAY_ENVIRONMENT_NAME",
            "RAILWAY_PROJECT_ID",
            "VERCEL",
        )
    )


@dataclass
class AppConfig:
    data_dir: Path = DEFAULT_DATA_DIR
    resume_path: Path | None = None
    llm_provider: str = "ollama"
    llm_model: str = "llama3.1:8b"
    ollama_base_url: str = "http://localhost:11434"
    database_url: str | None = None
    target_roles: list[str] = field(default_factory=list)
    locations: list[str] = field(default_factory=list)

    @property
    def profile_path(self) -> Path:
        return self.data_dir / "career_profile.json"

    @property
    def profile_metadata_path(self) -> Path:
        return self.data_dir / "career_profile.meta.json"

    @property
    def database_path(self) -> Path:
        legacy_database = self.data_dir / "career_agent.sqlite3"
        if self.data_dir == LEGACY_DATA_DIR and legacy_database.exists():
            return legacy_database
        return self.data_dir / "foxpilot.sqlite3"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        if is_hosted_runtime():
            raise RuntimeError(
                "DATABASE_URL is required in hosted deployments. "
                "Railway/API must use managed PostgreSQL; SQLite is only for local CLI/tests."
            )
        return f"sqlite:///{self.database_path}"


def _path_from_value(value: Any) -> Path | None:
    if not value:
        return None
    return Path(str(value)).expanduser().resolve()


def load_config(path: Path | None = None) -> AppConfig:
    load_dotenv()
    config_path = path or Path(
        os.getenv("FOXPILOT_CONFIG", str(DEFAULT_CONFIG_PATH))
    ).expanduser()
    if path is None and not config_path.exists():
        legacy_config = LEGACY_DATA_DIR / "config.json"
        if legacy_config.exists():
            config_path = legacy_config
    values: dict[str, Any] = {}
    if config_path.exists():
        values = json.loads(config_path.read_text(encoding="utf-8"))

    data_dir = _path_from_value(values.get("data_dir")) or config_path.parent
    provider_name = os.getenv("LLM_PROVIDER", values.get("llm_provider", "ollama")).lower()
    default_model = "gemini-3.6-flash" if provider_name in ("gemini", "google") else "llama3.1:8b"
    return AppConfig(
        data_dir=data_dir,
        resume_path=_path_from_value(values.get("resume_path")),
        llm_provider=provider_name,
        llm_model=os.getenv(
            "LLM_MODEL",
            os.getenv("OLLAMA_MODEL", values.get("llm_model", default_model)),
        ),
        ollama_base_url=os.getenv(
            "OLLAMA_BASE_URL",
            values.get("ollama_base_url", "http://localhost:11434"),
        ),
        database_url=normalize_database_url(os.getenv("DATABASE_URL") or values.get("database_url")),
        target_roles=list(values.get("target_roles", [])),
        locations=list(values.get("locations", [])),
    )
