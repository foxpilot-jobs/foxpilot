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


def profile_matches_job(
    job: dict,
    profile: dict,
) -> bool:
    """Return whether the job has deterministic evidence of profile fit."""
    if job.get("source") == "hackernews":
        # HN comments are represented as synthetic titles containing the
        # entire post; they are not reliable enough for title-only targeting.
        return False
    title = normalize(job.get("title", ""))
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

    roles = [
        *profile_values("target_roles"),
        *profile_values("current_or_recent_roles"),
    ]
    role_phrases = {
        phrase.strip()
        for role in roles
        for phrase in re.split(r"\s*(?:&|/|,|\band\b)\s*", normalize(role))
        if len(phrase.strip().split()) >= 2
    }
    role_match = any(
        phrase in title
        for phrase in role_phrases
    )
    return role_match


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
