import re

from career_agent.config import load_config
from career_agent.storage import JobStore

TARGET_ROLES = [
    "analytics engineer",
    "analytics engineering",
    "data engineer",
    "data analyst",
    "senior data analyst",
    "bi engineer",
    "business intelligence engineer",
    "snowflake developer",
    "data warehouse engineer",
]


EXCLUDED_ROLES = [
    "android engineer",
    "ios engineer",
    "mobile engineer",
    "frontend engineer",
    "front end engineer",
    "backend engineer",
    "back end engineer",
    "full stack engineer",
    "full-stack engineer",
    "site reliability engineer",
    "sre",
    "devops engineer",
    "cloud engineer",
    "network engineer",
    "security engineer",
    "sales engineer",
    "solutions architect",
    "product manager",
    "project manager",
    "engineering manager",
    "qa engineer",
    "test engineer",
]


ML_SIGNALS = [
    "pytorch",
    "tensorflow",
    "computer vision",
    "deep learning",
    "machine learning model",
    "mlops",
    "model training",
    "model deployment",
    "neural network",
    "transformers",
]


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


def contains_any(
    text: str,
    keywords: list[str],
) -> bool:

    normalized = normalize(text)

    return any(
        keyword in normalized
        for keyword in keywords
    )


def is_excluded_role(
    title: str,
) -> bool:

    return contains_any(
        title,
        EXCLUDED_ROLES,
    )


def is_target_role(
    title: str,
) -> bool:

    return contains_any(
        title,
        TARGET_ROLES,
    )


def has_strong_ml_signals(
    description: str,
) -> bool:

    normalized = normalize(
        description
    )

    matches = [
        signal
        for signal in ML_SIGNALS
        if signal in normalized
    ]

    # A couple of ML signals are enough to
    # prevent automatic targeting.
    return len(matches) >= 2


def profile_matches_job(
    job: dict,
    profile: dict,
) -> bool:
    """Return whether the job has deterministic evidence of profile fit."""
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
    profile_role_domain = any(
        contains_any(
            normalize(role),
            ["data", "analytics", "bi", "warehouse", "snowflake"],
        )
        for role in roles
    )
    taxonomy_match = profile_role_domain and is_target_role(title)
    return role_match or taxonomy_match


def classify_job(
    job: dict,
    profile: dict | None = None,
) -> str:

    title = job.get(
        "title",
        "",
    )

    description = job.get(
        "description",
        "",
    )

    # An uploaded profile is the source of truth for personalized scans.
    # This allows roles outside the generic taxonomy while still requiring
    # deterministic evidence before spending an LLM call.
    if profile and profile_matches_job(job, profile):
        if has_strong_ml_signals(description):
            return "REVIEW"
        return "TARGET"

    # Do not fall back to the generic taxonomy after a profile is available;
    # otherwise a generic "Data Engineer" target can bypass the user's career.
    if profile:
        return "REVIEW"

    # --------------------------------------------------
    # 1. Clearly unrelated roles
    # --------------------------------------------------

    if is_excluded_role(title):

        return "EXCLUDE"

    # --------------------------------------------------
    # 2. ML-heavy roles
    # --------------------------------------------------
    #
    # Example:
    #
    # "Data Analyst — Machine Learning"
    #
    # We don't want the title alone to make this
    # a TARGET just because it contains "Data Analyst".
    #
    # Instead, send it to REVIEW.
    # The user can decide whether it should be analyzed.
    #

    if (
        is_target_role(title)
        and has_strong_ml_signals(
            description
        )
    ):

        return "REVIEW"

    # --------------------------------------------------
    # 3. Clearly relevant roles
    # --------------------------------------------------

    if is_target_role(title):

        return "TARGET"

    # --------------------------------------------------
    # 4. Everything else is ambiguous
    # --------------------------------------------------

    return "REVIEW"


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
