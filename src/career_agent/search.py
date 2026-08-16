"""Profile-driven job search planning shared by CLI and API scans."""

from __future__ import annotations

import re


def _values(profile: dict, field: str) -> list[str]:
    value = profile.get(field) or []
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        result: list[str] = []
        for nested in value.values():
            if isinstance(nested, list):
                result.extend(str(item) for item in nested)
            elif isinstance(nested, str):
                result.append(nested)
        return result
    return [str(item) for item in value]


def profile_search_queries(profile: dict) -> list[str]:
    """Return deduplicated search queries derived only from this profile."""
    roles = [*_values(profile, "target_roles"), *_values(profile, "current_or_recent_roles")]
    queries: list[str] = []
    seen: set[str] = set()
    for role in roles:
        for phrase in re.split(r"\s*(?:&|/|,|\band\b)\s*", role):
            query = re.sub(r"\s+", " ", phrase).strip()
            if len(query.split()) < 2:
                continue
            key = query.casefold()
            if key not in seen:
                seen.add(key)
                queries.append(query)
    if not queries:
        raise ValueError("Your profile has no usable target or current role")
    return queries[:8]


def profile_searches(
    profile: dict,
    *,
    date_posted: str = "past_day",
    work_type: str = "remote",
) -> list[dict]:
    """Build Greenhouse-compatible searches from profile role evidence."""
    return [
        {
            "name": query,
            "query": query,
            "date_posted": date_posted,
            "work_type": work_type,
        }
        for query in profile_search_queries(profile)
    ]
