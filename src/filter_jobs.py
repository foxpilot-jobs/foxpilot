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
    {"engineer", "developer", "specialist", "analyst", "consultant", "manager", "architect", "lead"}
)


def profile_matches_job(
    job: dict,
    profile: dict,
) -> bool:
    """Return whether a job passes broad recall-oriented deterministic candidate pre-filtering."""
    if not profile:
        return False

    if job.get("source") == "hackernews":
        return False

    title_norm = normalize(job.get("title", ""))
    desc_norm = normalize(job.get("description", ""))
    full_text_norm = f"{title_norm} {desc_norm}"

    def profile_values(field: str) -> list[str]:
        value = profile.get(field) or []
        if isinstance(value, str):
            return [value]
        if isinstance(value, dict):
            values = []
            for nested in value.values():
                if isinstance(nested, list):
                    values.extend(str(item) for item in nested)
                elif isinstance(nested, str):
                    values.append(nested)
            return values
        return [str(item) for item in value]

    target_roles = [normalize(r) for r in profile_values("target_roles") if normalize(r)]
    recent_roles = [normalize(r) for r in profile_values("current_or_recent_roles") if normalize(r)]
    all_roles = [*target_roles, *recent_roles]

    # 1. Direct role phrase match in title
    for r in all_roles:
        if r and r in title_norm:
            return True

    # 2. Specific role token match in title (excluding generic role words like "engineer")
    primary_role_sources = target_roles if target_roles else recent_roles
    specific_role_tokens = set()
    for role in primary_role_sources:
        tokens = [
            t for t in role.split() if t not in STOP_WORDS and len(t) >= 3 and t not in GENERIC_ROLE_WORDS
        ]
        specific_role_tokens.update(tokens)

    if specific_role_tokens:
        title_words = set(title_norm.split())
        if title_words.intersection(specific_role_tokens):
            return True

    # 3. Candidate skill overlap in job text (title + description)
    skills = profile_values("skills")
    skill_tokens = set()
    for skill in skills:
        norm_skill = normalize(skill)
        if norm_skill and norm_skill not in STOP_WORDS and len(norm_skill) >= 2:
            skill_tokens.add(norm_skill)

    if skill_tokens:
        skill_matches = 0
        for skill_token in skill_tokens:
            if re.search(r"\b" + re.escape(skill_token) + r"\b", full_text_norm):
                skill_matches += 1
                if skill_matches >= 3:
                    return True

    return False


def classify_job(
    job: dict,
    profile: dict | None = None,
) -> str:
    return "TARGET" if profile and profile_matches_job(job, profile) else "REVIEW"


def load_jobs() -> list[dict]:
    with JobStore(load_config().resolved_database_url) as store:
        return store.list_jobs()


def print_job_list(
    title: str,
    jobs: list[dict],
    symbol: str,
) -> None:

    if not jobs:
        return

    print(
        f"{title}:"
    )

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

    print(
        f"Loaded {len(jobs)} job(s)."
    )

    target_jobs = []
    review_jobs = []
    excluded_jobs = []

    with JobStore(config.resolved_database_url) as store:
        for job in jobs:

            classification = classify_job(
                job,
                profile,
            )

            job["local_relevance"] = (
                classification
            )
            store.set_relevance(job["job_id"], classification)

            if classification == "TARGET":

                target_jobs.append(
                    job
                )

            elif classification == "REVIEW":

                review_jobs.append(
                    job
                )

            else:

                excluded_jobs.append(
                    job
                )

    # --------------------------------------------------
    # Print summary
    # --------------------------------------------------

    print()

    print(
        "Profile-aware relevance filtering:"
    )

    print(
        f"  Target:  "
        f"{len(target_jobs)}"
    )

    print(
        f"  Review:  "
        f"{len(review_jobs)}"
    )

    print(
        f"  Exclude: "
        f"{len(excluded_jobs)}"
    )

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

    print(
        f"Jobs passed to AI: "
        f"{len(target_jobs)}"
    )

    print(
        f"Jobs held for review: "
        f"{len(review_jobs)}"
    )

    print(
        f"Jobs excluded: "
        f"{len(excluded_jobs)}"
    )


if __name__ == "__main__":
    main()
