import subprocess
import sys


def run_step(
    name: str,
    command: list[str],
) -> None:

    print()
    print(
        "=" * 70
    )

    print(
        f"STEP: {name}"
    )

    print(
        "=" * 70
    )

    result = subprocess.run(
        command,
        check=False,
    )

    if result.returncode != 0:

        print()
        print(
            f"ERROR: {name} failed."
        )

        sys.exit(
            result.returncode
        )


def main():

    python = sys.executable

    print(
        "=" * 70
    )

    print(
        "CAREER AGENT"
    )

    print(
        "=" * 70
    )

    # --------------------------------------------------
    # STEP 1 — FETCH JOBS
    # --------------------------------------------------

    run_step(
        "Job ingestion",
        [
            python,
            "src/fetch_greenhouse.py",
        ],
    )

    # --------------------------------------------------
    # STEP 2 — LOCAL RELEVANCE FILTER
    # --------------------------------------------------

    run_step(
        "Local relevance filtering",
        [
            python,
            "src/filter_jobs.py",
        ],
    )

    # --------------------------------------------------
    # STEP 3 — AI MATCHING
    # --------------------------------------------------

    run_step(
        "AI job matching",
        [
            python,
            "src/match_jobs.py",
        ],
    )

    print()
    print(
        "=" * 70
    )

    print(
        "CAREER AGENT COMPLETE"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()