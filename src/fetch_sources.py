"""Run all configured job sources while isolating source failures."""

from __future__ import annotations

from career_agent.sources import fetch_configured_sources
from fetch_greenhouse import fetch_jobs, load_searches


def main() -> int:
    total = 0
    try:
        jobs = fetch_jobs(load_searches())
        total += len(jobs)
        print(f"[SOURCE] Greenhouse: fetched {len(jobs)}")
    except Exception as error:  # noqa: BLE001 - one source must not stop the scan
        print(f"[SOURCE] Greenhouse: failed, continuing: {error}")

    total += fetch_configured_sources()
    print(f"Total new jobs discovered: {total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
