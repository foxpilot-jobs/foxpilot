import subprocess
import sys

from career_agent.config import load_config
from career_agent.profile import has_current_local_profile
from career_agent.runtime import ScanAlreadyRunning, ScanLock
from career_agent.storage import JobStore


def run_step(
    name: str,
    command: list[str],
) -> None:

    print()
    print("=" * 70)

    print(f"STEP: {name}")

    print("=" * 70)

    result = subprocess.run(
        command,
        check=False,
    )

    if result.returncode != 0:
        print()
        print(f"ERROR: {name} failed.")

        sys.exit(result.returncode)


def has_filtered_jobs() -> bool:
    with JobStore(load_config().resolved_database_url) as store:
        return store.list_jobs(relevance="TARGET", limit=1)["total"] > 0


def _run_pipeline():

    python = sys.executable

    print("=" * 70)

    print("FOXPILOT")

    print("=" * 70)

    config = load_config()
    if not has_current_local_profile(config):
        run_step(
            "Career profile creation",
            [
                python,
                "src/create_profile.py",
            ],
        )

    # --------------------------------------------------
    # STEP 1 — PROFILE-DRIVEN JOB INGESTION
    # --------------------------------------------------

    run_step(
        "Profile-driven job ingestion",
        [
            python,
            "src/fetch_sources.py",
        ],
    )

    # --------------------------------------------------
    # STEP 2 — PROFILE-AWARE RELEVANCE FILTER
    # --------------------------------------------------

    run_step(
        "Profile-aware relevance filtering",
        [
            python,
            "src/filter_jobs.py",
        ],
    )

    if not has_filtered_jobs():
        print()
        print("No target jobs were found. Skipping AI matching.")
        print(
            "If Greenhouse returned redirects, log in with the new browser profile and scan again."
        )
        return 0

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
    print("=" * 70)


def main() -> int:
    config = load_config()
    try:
        with ScanLock(config.data_dir / "scan.lock"):
            result = _run_pipeline() or 0
            print("FOXPILOT COMPLETE")
            print("=" * 70)
            return result
    except ScanAlreadyRunning as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
