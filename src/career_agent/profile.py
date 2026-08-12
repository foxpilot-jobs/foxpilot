"""Resume extraction and structured profile generation."""

from __future__ import annotations

import json
from pathlib import Path

from pypdf import PdfReader

from .config import AppConfig
from .llm import LLMProvider, create_provider


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


def extract_resume_text(path: Path) -> str:
    if not path.exists():
        raise FileNotFoundError(f"Resume not found: {path}")
    if path.suffix.lower() == ".txt":
        return path.read_text(encoding="utf-8")
    reader = PdfReader(path)
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def build_profile_prompt(resume_text: str) -> str:
    fields = ",\n  ".join(f'"{field}": null' for field in PROFILE_FIELDS)
    return f"""You are a careful career profile extraction assistant.

Use only facts explicitly present in the resume. Never invent skills, experience,
achievements, education, or job titles. Use an empty list or null when unknown.
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
            "No resume is configured. Run `career-agent init --resume path/to/resume.pdf`."
        )
    provider = provider or create_provider(config)
    profile = provider.complete_json(build_profile_prompt(extract_resume_text(config.resume_path)))
    missing = [field for field in PROFILE_FIELDS if field not in profile]
    if missing:
        raise ValueError(f"Profile response is missing fields: {', '.join(missing)}")
    config.data_dir.mkdir(parents=True, exist_ok=True)
    config.profile_path.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return profile
