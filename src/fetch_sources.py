"""Run all configured job sources while isolating source failures.

When called without a profile (``--no-profile``), the script runs a shared
ingestion that fetches all available public jobs without profile-driven query
filtering.  This is the intended mode for populating the reusable job corpus.

When called with a profile (the default for backward compatibility), searches
are still derived from the profile and passed to browser-based Greenhouse
ingestion.
"""

from __future__ import annotations

import json
import sys

from career_agent.config import load_config
from career_agent.search import profile_searches
from career_agent.sources import fetch_configured_sources
from fetch_greenhouse import fetch_jobs


def main(profile: dict | None = None, user_id: str = "local-user", max_jobs: int | None = None) -> int:
    total = 0

    # Browser-based Greenhouse ingestion requires profile-derived searches.
    # Skip it during profile-free shared ingestion.
    if profile is not None:
        try:
            jobs = fetch_jobs(profile_searches(profile), user_id=user_id)
            if max_jobs is not None and len(jobs) > max_jobs:
                jobs = jobs[:max_jobs]
            total += len(jobs)
            print(f"[SOURCE] Greenhouse (browser): fetched {len(jobs)}")
        except Exception as error:  # noqa: BLE001 - one source must not stop the scan
            print(f"[SOURCE] Greenhouse (browser): failed, continuing: {error}")

    remaining_cap = (max_jobs - total) if (max_jobs is not None) else None
    total += fetch_configured_sources(profile=profile, user_id=user_id, max_jobs=remaining_cap)
    print(f"Total jobs processed/discovered: {total}")
    return 0


if __name__ == "__main__":
    config = load_config()

    max_jobs_val = None
    if "--max-jobs" in sys.argv:
        idx = sys.argv.index("--max-jobs")
        if idx + 1 < len(sys.argv):
            try:
                max_jobs_val = int(sys.argv[idx + 1])
            except ValueError:
                pass

    if "--no-profile" in sys.argv:
        raise SystemExit(main(profile=None, user_id="system", max_jobs=max_jobs_val))

    if not config.profile_path.exists():
        raise SystemExit("Create a career profile before scanning for jobs.")
    raise SystemExit(main(json.loads(config.profile_path.read_text(encoding="utf-8")), max_jobs=max_jobs_val))
