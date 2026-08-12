"""Explainable job matching through the configured LLM provider."""

from __future__ import annotations

import json

from .config import AppConfig
from .llm import LLMProvider, create_provider


MATCH_FIELDS = [
    "match_score",
    "recommendation",
    "reasons",
    "matching_skills",
    "missing_skills",
    "experience_match",
    "concerns",
]


def build_match_prompt(profile: dict, job: dict) -> str:
    return f"""You are a conservative job-matching assistant.

Compare the candidate profile with the job posting. Do not invent candidate
experience. Prioritize required skills and relevant experience over nice-to-have
skills. Return one valid JSON object with exactly these fields:
{{
  "match_score": 0,
  "recommendation": "APPLY",
  "reasons": [],
  "matching_skills": [],
  "missing_skills": [],
  "experience_match": "",
  "concerns": []
}}

Rules:
- match_score is an integer from 0 to 100.
- recommendation is APPLY, CONSIDER, or SKIP.
- Explicitly mention missing mandatory experience or skills.
- Do not treat similar technology names as equivalent without evidence.
- AI-assisted development is not machine-learning engineering experience unless the profile says so.

CANDIDATE PROFILE:
---
{json.dumps(profile, indent=2)}
---

JOB:
---
{json.dumps(job, indent=2)}
---
"""


def match_job(
    config: AppConfig,
    profile: dict,
    job: dict,
    provider: LLMProvider | None = None,
) -> dict:
    provider = provider or create_provider(config)
    result = provider.complete_json(build_match_prompt(profile, job))
    missing = [field for field in MATCH_FIELDS if field not in result]
    if missing:
        raise ValueError(f"Match response is missing fields: {', '.join(missing)}")
    score = result["match_score"]
    if not isinstance(score, int) or not 0 <= score <= 100:
        raise ValueError("Match response match_score must be an integer from 0 to 100.")
    if result["recommendation"] not in {"APPLY", "CONSIDER", "SKIP"}:
        raise ValueError("Match response recommendation must be APPLY, CONSIDER, or SKIP.")
    return result
