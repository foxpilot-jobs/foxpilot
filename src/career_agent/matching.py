"""Explainable job matching through the configured LLM provider."""

from __future__ import annotations

import json

from .config import AppConfig
from .llm import LLMError, LLMProvider, create_provider

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
  "concerns": [],
  "gap_analysis": []
}}

Rules:
- match_score is an integer from 0 to 100.
- recommendation is APPLY, CONSIDER, or SKIP.
- Explicitly mention missing mandatory experience or skills.
- Do not treat similar technology names as equivalent without evidence.
- AI-assisted development is not machine-learning engineering experience unless the profile says so.
- For each material missing skill, include gap_analysis entries with severity blocking only when the posting clearly makes it mandatory; use addressable for learnable or adjacent gaps and unknown when the posting is ambiguous.
- Never claim a gap is bypassable without evidence from the posting; explain what should be verified.

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
    prompt = build_match_prompt(profile, job)

    for attempt in range(2):
        try:
            result = provider.complete_json(prompt)
        except LLMError:
            if attempt == 1:
                raise
            prompt += "\nReturn only the requested JSON object with no explanation or markdown."
            continue

        missing = [field for field in MATCH_FIELDS if field not in result]
        score = result.get("match_score")
        recommendation = result.get("recommendation")
        valid = (
            not missing
            and isinstance(score, int)
            and 0 <= score <= 100
            and recommendation in {"APPLY", "CONSIDER", "SKIP"}
        )
        if valid:
            result.setdefault("gap_analysis", [])
            return result

        if attempt == 0:
            prompt += (
                "\nYour previous response violated the schema. Return every required field: "
                "match_score (integer 0-100), recommendation (APPLY, CONSIDER, or SKIP), "
                "reasons, matching_skills, missing_skills, experience_match, and concerns."
            )
            continue

        if missing:
            raise ValueError(f"Match response is missing fields: {', '.join(missing)}")
        if not isinstance(score, int) or not 0 <= score <= 100:
            raise ValueError("Match response match_score must be an integer from 0 to 100.")
        raise ValueError("Match response recommendation must be APPLY, CONSIDER, or SKIP.")

    raise AssertionError("Unreachable match retry state")
