"""Compatibility command for matching filtered jobs."""

from __future__ import annotations

import hashlib
import json

from career_agent.config import load_config
from career_agent.llm import LLMError, create_provider
from career_agent.matching import match_job
from career_agent.storage import JobStore
from filter_jobs import classify_job


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
        print("Run `foxpilot scan` or `python src/create_profile.py` first.")
        return 1
    profile = json.loads(config.profile_path.read_text(encoding="utf-8"))
    try:
        provider = create_provider(config)
    except LLMError as error:
        print(f"LLM setup failed: {error}")
        return 1

    analyzed = 0
    skipped = 0

    with JobStore(config.resolved_database_url) as store:
        jobs = [
            job
            for job in store.list_jobs(limit=10000)["items"]
            if classify_job(job, profile) == "TARGET"
        ]
        for job in jobs:
            job_id = job["job_id"]
            job_hash = get_job_hash(job)
            cached = store.get_match(job_id)
            if cached and cached.get("job_hash") == job_hash:
                skipped += 1
                continue

            print(
                f"Analyzing: {job.get('title', 'Unknown')} - {job.get('company', 'Unknown')}"
            )
            try:
                result = match_job(config, profile, job, provider=provider)
            except (LLMError, ValueError) as error:
                print(f"Matching failed for {job_id}: {error}")
                continue

            store.save_match(
                job_id,
                job_hash,
                config.llm_provider,
                config.llm_model,
                result,
            )
            analyzed += 1

    print(f"New jobs analyzed: {analyzed}")
    print(f"Already analyzed: {skipped}")
    return 0 if analyzed or skipped else 1


if __name__ == "__main__":
    raise SystemExit(main())
