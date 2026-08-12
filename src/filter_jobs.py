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


def classify_job(
    job: dict,
) -> str:

    title = job.get(
        "title",
        "",
    )

    description = job.get(
        "description",
        "",
    )

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

    jobs = load_jobs()

    print(
        f"Loaded {len(jobs)} job(s)."
    )

    target_jobs = []
    review_jobs = []
    excluded_jobs = []

    with JobStore(load_config().resolved_database_url) as store:
        for job in jobs:

            classification = classify_job(
                job
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
        "Local relevance filtering:"
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
