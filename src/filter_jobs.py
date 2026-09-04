import re

from career_agent.config import load_config
from career_agent.storage import JobStore


def normalize(text: str) -> str:
    text = text.lower()

    text = re.sub(
        r"[^a-z0-9+#.\s-]",
        " ",
        text,
    )

    text = re.sub(
        r"\s+",
        " ",
        text,
    )

    return text.strip()


STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "the",
        "and",
        "or",
        "of",
        "to",
        "in",
        "for",
        "with",
        "on",
        "at",
        "by",
        "from",
        "senior",
        "junior",
        "lead",
        "staff",
        "principal",
        "head",
        "vp",
        "director",
        "manager",
        "associate",
        "intern",
        "contractor",
        "freelance",
        "remote",
        "full-time",
        "part-time",
    }
)


GENERIC_ROLE_WORDS = frozenset(
    {
        "engineer",
        "developer",
        "specialist",
        "analyst",
        "consultant",
        "manager",
        "architect",
        "lead",
    }
)


from career_agent.work_arrangement import is_job_location_eligible

PREFIXES_TO_STRIP = (
    "senior",
    "jr",
    "junior",
    "lead",
    "staff",
    "principal",
    "distinguished",
    "head of",
    "head",
    "director",
    "vp of",
    "vp",
    "associate",
    "intern",
    "co-op",
    "contractor",
    "freelance",
    "interim",
    "chief",
    "sr.",
    "sr",
    "jr.",
)

SUFFIXES_TO_STRIP = (
    "i",
    "ii",
    "iii",
    "iv",
    "v",
    "1",
    "2",
    "3",
    "4",
    "5",
    "sr",
    "jr",
    "lead",
)

ROLE_ALIASES = {
    "software development engineer": "software engineer",
    "sde": "software engineer",
    "sde i": "software engineer",
    "sde ii": "software engineer",
    "sde iii": "software engineer",
    "swe": "software engineer",
}


def clean_role_title(title: str) -> str:
    norm = title.lower().strip()
    norm = re.sub(r"[^a-z0-9\s-]", " ", norm)
    norm = re.sub(r"\s+", " ", norm).strip()

    if norm in ROLE_ALIASES:
        return ROLE_ALIASES[norm]

    tokens = norm.split()
    while tokens and tokens[0] in PREFIXES_TO_STRIP:
        tokens.pop(0)
    while tokens and tokens[-1] in SUFFIXES_TO_STRIP:
        tokens.pop()

    cleaned = " ".join(tokens)
    return ROLE_ALIASES.get(cleaned, cleaned)


def is_target_role_compatible(job_title: str, target_roles: list[str]) -> bool:
    if not target_roles:
        return False

    cleaned_job = clean_role_title(job_title)

    for target in target_roles:
        if not target or not isinstance(target, str) or not target.strip():
            continue
        cleaned_target = clean_role_title(target)

        # 1. Exact match on cleaned titles
        if cleaned_job == cleaned_target:
            return True

        # 2. Check phrase / sub-role compatibility
        if cleaned_target in cleaned_job:
            target_nouns = set(cleaned_target.split())
            job_nouns = set(cleaned_job.split())

            if "engineer" in target_nouns and "engineer" not in job_nouns:
                continue
            if "manager" in target_nouns and "manager" not in job_nouns:
                continue
            if "scientist" in target_nouns and "scientist" not in job_nouns:
                continue
            if cleaned_target == "data engineer" and "scientist" in job_nouns:
                continue
            if cleaned_target == "data engineer" and "analyst" in job_nouns:
                continue
            if cleaned_target == "software engineer" and ("manager" in job_nouns or "designer" in job_nouns):
                continue
            return True

        # 3. Check reverse: cleaned_job in cleaned_target
        if cleaned_job in cleaned_target:
            target_nouns = set(cleaned_target.split())
            job_nouns = set(cleaned_job.split())
            if "engineer" in job_nouns and "engineer" in target_nouns:
                return True

    return False


def profile_matches_job(
    job: dict,
    profile: dict,
) -> bool:
    if not profile:
        return False
    if job.get("source") == "hackernews":
        return False
    locs = profile.get("locations") or []
    if isinstance(locs, str):
        locs = [locs]
    if not is_job_location_eligible(job, preferred_locations=locs):
        return False
    target_roles = profile.get("target_roles") or []
    if isinstance(target_roles, str):
        target_roles = [target_roles]
    if target_roles:
        return is_target_role_compatible(job.get("title", ""), target_roles)
    return False


def classify_job(
    job: dict,
    profile: dict | None = None,
    workspace_preferences: dict | None = None,
) -> str:
    """Classify a job as TARGET or OUT_OF_SCOPE/REVIEW based strictly on workspace preferences."""
    is_implicit_prefs = False
    if not workspace_preferences and profile:
        is_implicit_prefs = True
        target_roles = profile.get("target_roles") or []
        if isinstance(target_roles, str):
            target_roles = [target_roles]
        workspace_preferences = {
            "target_roles": target_roles,
            "work_arrangement": "any",
            "preferred_locations": profile.get("locations") or [],
        }

    if workspace_preferences:
        wa_pref = workspace_preferences.get("work_arrangement", "any")
        loc_pref = workspace_preferences.get("preferred_locations") or []
        if not is_job_location_eligible(job, wa_pref, loc_pref):
            return "REVIEW" if is_implicit_prefs else "OUT_OF_SCOPE"

        target_roles = workspace_preferences.get("target_roles") or []
        if target_roles:
            if not is_target_role_compatible(job.get("title", ""), target_roles):
                return "REVIEW" if is_implicit_prefs else "OUT_OF_SCOPE"
            return "TARGET"

    return "TARGET" if profile and profile_matches_job(job, profile) else "REVIEW"


def load_jobs() -> list[dict]:
    with JobStore(load_config().resolved_database_url) as store:
        return store.list_jobs(limit=10000)["items"]


def print_job_list(
    title: str,
    jobs: list[dict],
    symbol: str,
) -> None:

    if not jobs:
        return

    print(f"{title}:")

    for job in jobs:
        print(
            f"  {symbol} "
            f"{job.get('title', 'Unknown')} "
            f"— "
            f"{job.get('company', 'Unknown')}"
        )

    print()


def main():

    config = load_config()
    jobs = load_jobs()

    profile = None
    if config.profile_path.exists():
        import json

        profile = json.loads(config.profile_path.read_text(encoding="utf-8"))

    print(f"Loaded {len(jobs)} job(s).")

    target_jobs = []
    review_jobs = []
    excluded_jobs = []

    with JobStore(config.resolved_database_url) as store:
        for job in jobs:
            classification = classify_job(
                job,
                profile,
            )

            job["local_relevance"] = classification
            store.set_relevance(job["job_id"], classification)

            if classification == "TARGET":
                target_jobs.append(job)

            elif classification == "REVIEW":
                review_jobs.append(job)

            else:
                excluded_jobs.append(job)

    # --------------------------------------------------
    # Print summary
    # --------------------------------------------------

    print()

    print("Profile-aware relevance filtering:")

    print(f"  Target:  {len(target_jobs)}")

    print(f"  Review:  {len(review_jobs)}")

    print(f"  Exclude: {len(excluded_jobs)}")

    print()

    # --------------------------------------------------
    # Print lists
    # --------------------------------------------------

    print_job_list(
        "TARGET JOBS",
        target_jobs,
        "✓",
    )

    print_job_list(
        "REVIEW JOBS",
        review_jobs,
        "?",
    )

    print_job_list(
        "EXCLUDED JOBS",
        excluded_jobs,
        "✗",
    )

    print("Relevance classifications persisted to SQLite.")

    print()

    print(f"Jobs passed to AI: {len(target_jobs)}")

    print(f"Jobs held for review: {len(review_jobs)}")

    print(f"Jobs excluded: {len(excluded_jobs)}")


if __name__ == "__main__":
    main()
