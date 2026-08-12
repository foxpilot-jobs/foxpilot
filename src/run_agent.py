import json
import subprocess
import sys
from pathlib import Path

from career_agent.config import load_config


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


def has_filtered_jobs() -> bool:
    path = Path("data/filtered_jobs.json")
    if not path.exists():
        return False

    try:
        jobs = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False

    return isinstance(jobs, list) and bool(jobs)


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

    if not has_filtered_jobs():
        print()
        print("No target jobs were found. Skipping AI matching.")
        print("If Greenhouse returned redirects, log in with the new browser profile and scan again.")
        return

    config = load_config()
    if not config.profile_path.exists():
        run_step(
            "Career profile creation",
            [
                python,
                "src/create_profile.py",
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
    raise SystemExit(main() or 0)
