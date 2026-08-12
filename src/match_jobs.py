"""Compatibility command for matching filtered jobs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from career_agent.config import load_config
from career_agent.llm import LLMError, create_provider
from career_agent.matching import match_job


FILTERED_JOBS_PATH = Path("data/filtered_jobs.json")
MATCHES_PATH = Path("data/matches.json")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def get_job_hash(job: dict) -> str:
    content = {
        key: job.get(key)
        for key in ("title", "company", "location", "url", "description")
    }
    serialized = json.dumps(content, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def main() -> int:
    config = load_config()
    if not config.profile_path.exists():
        print(f"Career profile not found: {config.profile_path}")
        print("Run `career-agent scan` or `python src/create_profile.py` first.")
        return 1
    if not FILTERED_JOBS_PATH.exists():
        print(f"Filtered jobs not found: {FILTERED_JOBS_PATH}")
        return 1

    profile = load_json(config.profile_path)
    jobs = load_json(FILTERED_JOBS_PATH)
    matches = load_json(MATCHES_PATH) if MATCHES_PATH.exists() else {}
    try:
        provider = create_provider(config)
    except LLMError as error:
        print(f"LLM setup failed: {error}")
        return 1

    analyzed = 0
    skipped = 0

    for job in jobs:
        source = job.get("source", "unknown")
        source_job_id = job.get("source_job_id", f"{job.get('company')}-{job.get('title')}")
        job_id = f"{source}_{source_job_id}"
        job_hash = get_job_hash(job)
        cached = matches.get(job_id)
        if cached and cached.get("job_hash") == job_hash:
            skipped += 1
            continue

        print(f"Analyzing: {job.get('title', 'Unknown')} - {job.get('company', 'Unknown')}")
        try:
            result = match_job(config, profile, job, provider=provider)
        except (LLMError, ValueError) as error:
            print(f"Matching failed for {job_id}: {error}")
            continue

        matches[job_id] = {
            "job_id": job_id,
            "job_hash": job_hash,
            "job": job,
            "match": result,
        }
        save_json(MATCHES_PATH, matches)
        analyzed += 1

    print(f"New jobs analyzed: {analyzed}")
    print(f"Already analyzed: {skipped}")
    return 0 if analyzed or skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
