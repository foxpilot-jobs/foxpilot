"""Explainable job matching through the configured LLM provider."""

from __future__ import annotations

import json

from .config import AppConfig
from .llm import LLMError, LLMProvider, LLMTimeoutError, create_provider

MATCH_FIELDS = [
    "match_score",
    "recommendation",
    "reasons",
    "matching_skills",
    "missing_skills",
    "experience_match",
    "concerns",
]
MAX_JOB_DESCRIPTION_CHARS = 8000

MATCH_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "match_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "recommendation": {"type": "string", "enum": ["APPLY", "CONSIDER", "SKIP"]},
        "reasons": {"type": "array", "items": {"type": "string"}},
        "matching_skills": {"type": "array", "items": {"type": "string"}},
        "missing_skills": {"type": "array", "items": {"type": "string"}},
        "experience_match": {"type": "string"},
        "concerns": {"type": "array", "items": {"type": "string"}},
        "gap_analysis": {"type": "array", "items": {"type": "object"}},
    },
    "required": MATCH_FIELDS,
}


def build_match_prompt(profile: dict, job: dict) -> str:
    compact_job = {
        field: job.get(field, "")
        for field in ("title", "company", "location", "url", "description")
    }
    description = str(compact_job["description"])
    if len(description) > MAX_JOB_DESCRIPTION_CHARS:
        compact_job["description"] = (
            description[:6500]
            + "\n...[description truncated]...\n"
            + description[-1500:]
        )
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
- Keep reasons and concerns concise; return no more than 3 items in each list.
- For each material missing skill, include gap_analysis entries with severity blocking only when the posting clearly makes it mandatory; use addressable for learnable or adjacent gaps and unknown when the posting is ambiguous.
- Never claim a gap is bypassable without evidence from the posting; explain what should be verified.

CANDIDATE PROFILE:
---
{json.dumps(profile, indent=2)}
---

JOB:
---
{json.dumps(compact_job, indent=2)}
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
            result = provider.complete_json(prompt, response_schema=MATCH_RESPONSE_SCHEMA)
        except LLMTimeoutError:
            raise
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
