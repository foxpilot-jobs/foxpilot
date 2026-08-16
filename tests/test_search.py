import pytest

from career_agent.search import profile_search_queries, profile_searches


def test_search_queries_are_derived_from_profile_roles() -> None:
    profile = {
        "target_roles": None,
        "current_or_recent_roles": ["Data Engineering Analyst & Data Engineer", "Data Engineer"],
    }

    assert profile_search_queries(profile) == ["Data Engineering Analyst", "Data Engineer"]
    assert profile_searches(profile)[0]["query"] == "Data Engineering Analyst"


def test_search_requires_profile_role_evidence() -> None:
    with pytest.raises(ValueError, match="no usable target or current role"):
        profile_search_queries({"target_roles": [], "current_or_recent_roles": []})
