"""Run all configured job sources while isolating source failures."""

from __future__ import annotations

import json

from career_agent.config import load_config
from career_agent.search import profile_searches
from career_agent.sources import fetch_configured_sources
from fetch_greenhouse import fetch_jobs


def main(profile: dict, user_id: str = "local-user") -> int:
    total = 0
    try:
        jobs = fetch_jobs(profile_searches(profile), user_id=user_id)
        total += len(jobs)
        print(f"[SOURCE] Greenhouse: fetched {len(jobs)}")
    except Exception as error:  # noqa: BLE001 - one source must not stop the scan
        print(f"[SOURCE] Greenhouse: failed, continuing: {error}")

    total += fetch_configured_sources(profile=profile, user_id=user_id)
    print(f"Total new jobs discovered: {total}")
    return 0


if __name__ == "__main__":
    config = load_config()
    if not config.profile_path.exists():
        raise SystemExit("Create a career profile before scanning for jobs.")
    raise SystemExit(main(json.loads(config.profile_path.read_text(encoding="utf-8"))))
