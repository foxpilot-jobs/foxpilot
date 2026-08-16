"""Resume extraction and structured profile generation."""

from __future__ import annotations

import hashlib
import json
from io import BytesIO
from pathlib import Path

from pypdf import PdfReader

from .config import AppConfig
from .llm import LLMError, LLMProvider, LLMTimeoutError, create_provider

PROFILE_FIELDS = [
    "summary",
    "years_of_experience",
    "current_or_recent_roles",
    "skills",
    "programming_languages",
    "data_and_ai_tools",
    "cloud_and_infrastructure",
    "databases",
    "analytics_and_bi_tools",
    "industries",
    "education",
    "certifications",
    "projects",
    "target_roles",
]

PROFILE_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": ["string", "null"]},
        "years_of_experience": {"type": ["number", "null"]},
        **{field: {"type": "array", "items": {"type": "string"}} for field in PROFILE_FIELDS[2:]},
    },
    "required": PROFILE_FIELDS,
}


def resume_fingerprint(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as resume:
        for chunk in iter(lambda: resume.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_local_profile_metadata(config: AppConfig) -> None:
    if not config.resume_path:
        return
    config.profile_metadata_path.write_text(
        json.dumps(
            {
                "resume_path": str(config.resume_path.resolve()),
                "resume_sha256": resume_fingerprint(config.resume_path),
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


def has_current_local_profile(config: AppConfig) -> bool:
    """Check that the saved local profile belongs to the configured resume."""
    if not config.resume_path or not config.resume_path.exists():
        return False
    if not config.profile_path.exists() or not config.profile_metadata_path.exists():
        # Profiles written before fingerprinting are assumed to belong to the
        # currently configured resume and get metadata on first reuse.
        if config.profile_path.exists() and not config.profile_metadata_path.exists():
            write_local_profile_metadata(config)
            return True
        return False
    try:
        metadata = json.loads(config.profile_metadata_path.read_text(encoding="utf-8"))
        return (
            metadata.get("resume_path") == str(config.resume_path.resolve())
            and metadata.get("resume_sha256") == resume_fingerprint(config.resume_path)
        )
    except (OSError, ValueError, TypeError):
        return False


def extract_resume_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {path}")
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8")
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def extract_resume_text_from_bytes(content: bytes, filename: str) -> str:
    """Extract text from an uploaded PDF without persisting the file itself."""
    if not filename.lower().endswith(".pdf"):
        raise ValueError("Resume uploads must be PDF files")
    reader = PdfReader(BytesIO(content))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def build_profile_prompt(resume_text: str) -> str:
    fields = ",\n  ".join(f'"{field}": null' for field in PROFILE_FIELDS)
    return f"""You are a careful career profile extraction assistant.

Use only facts explicitly present in the resume. Never invent skills, experience,
achievements, education, or job titles. Use an empty list or null when unknown.
Always derive target_roles from the user's current or recent roles and clearly
supported career direction; do not leave target_roles empty when the resume
contains a usable job title. Keep current_or_recent_roles and target_roles
distinct when possible.
Keep the response concise: summary <= 2 sentences, lists <= 5 items, projects <= 3 items,
and each list item <= 80 characters.
Return one valid JSON object with exactly these fields:
{{
  {fields}
}}

Resume:
---
{resume_text}
---
"""


def create_profile(
    config: AppConfig,
    provider: LLMProvider | None = None,
) -> dict:
    if not config.resume_path:
        raise ValueError(
            "No resume is configured. Run `foxpilot init --resume path/to/resume.pdf`."
        )
    provider = provider or create_provider(config)
    return create_profile_from_text(config, extract_resume_text(config.resume_path), provider)


def create_profile_from_text(
    config: AppConfig,
    resume_text: str,
    provider: LLMProvider | None = None,
    persist: bool = True,
) -> dict:
    provider = provider or create_provider(config)
    prompt = build_profile_prompt(resume_text)
    try:
        profile = provider.complete_json(prompt, response_schema=PROFILE_RESPONSE_SCHEMA)
    except LLMTimeoutError:
        raise
    except LLMError:
        profile = provider.complete_json(
            prompt
            + "\nReturn only the requested JSON object. Keep every list short and use null or [] when uncertain.",
            response_schema=PROFILE_RESPONSE_SCHEMA,
        )

    missing = [field for field in PROFILE_FIELDS if field not in profile]
    if missing:
        profile = provider.complete_json(
            prompt
            + "\nReturn every required field exactly once and keep the response concise.",
            response_schema=PROFILE_RESPONSE_SCHEMA,
        )
        missing = [field for field in PROFILE_FIELDS if field not in profile]
        if missing:
            raise ValueError(f"Profile response is missing fields: {', '.join(missing)}")
    if persist:
        config.data_dir.mkdir(parents=True, exist_ok=True)
        config.profile_path.write_text(
            json.dumps(profile, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        write_local_profile_metadata(config)
    return profile
