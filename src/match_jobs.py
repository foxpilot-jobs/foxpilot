import hashlib
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI


PROFILE_PATH = Path("data/career_profile.json")
FILTERED_JOBS_PATH = Path("data/filtered_jobs.json")
MATCHES_PATH = Path("data/matches.json")


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(path: Path, data: dict) -> None:
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def load_jobs() -> list[dict]:
    """
    Load jobs that passed the local relevance filter.

    These are the only jobs that should reach the AI matcher.
    """

    if not FILTERED_JOBS_PATH.exists():
        print(
            f"ERROR: {FILTERED_JOBS_PATH} does not exist."
        )

        print(
            "Run filter_jobs.py first."
        )

        return []

    jobs = load_json(
        FILTERED_JOBS_PATH
    )

    if not isinstance(jobs, list):
        raise ValueError(
            f"{FILTERED_JOBS_PATH} must contain a JSON list."
        )

    for job in jobs:

        source = job.get(
            "source",
            "unknown",
        )

        source_job_id = job.get(
            "source_job_id"
        )

        if source_job_id:
            job["job_id"] = (
                f"{source}_{source_job_id}"
            )
        else:
            # Fallback for manually created jobs.
            job["job_id"] = (
                f"{source}_"
                f"{job.get('company', 'unknown')}_"
                f"{job.get('title', 'unknown')}"
            )

    return jobs


def load_matches() -> dict:
    if not MATCHES_PATH.exists():
        return {}

    return load_json(
        MATCHES_PATH
    )


def get_job_hash(job: dict) -> str:
    """
    Create a fingerprint of the important job content.

    If the description or other important fields change,
    the hash changes and the job will be analyzed again.
    """

    content = {
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "url": job.get("url"),
        "description": job.get("description"),
    }

    serialized = json.dumps(
        content,
        sort_keys=True,
        ensure_ascii=False,
    )

    return hashlib.sha256(
        serialized.encode("utf-8")
    ).hexdigest()


def match_job(
    profile: dict,
    job: dict,
) -> dict:

    client = OpenAI(
        api_key=os.getenv(
            "OPENAI_API_KEY"
        )
    )

    prompt = f"""
You are a careful job-matching assistant.

Compare the candidate's career profile against the job posting.

Your goal is NOT to maximize the score.

Your goal is to accurately determine whether this candidate
is a strong candidate for the role.

Never assume the candidate has experience that isn't in the profile.

Return valid JSON with exactly these fields:

{{
  "match_score": 0,
  "recommendation": "APPLY",
  "reasons": [],
  "matching_skills": [],
  "missing_skills": [],
  "experience_match": "",
  "concerns": []
}}

Rules:

- match_score must be between 0 and 100.
- APPLY = strong fit.
- CONSIDER = reasonable fit but has meaningful gaps.
- SKIP = poor fit.
- Give more importance to required skills and relevant experience
  than optional skills.
- Do not penalize the candidate heavily for nice-to-have skills.
- Do not invent candidate experience.
- Be conservative.
- Distinguish between required and nice-to-have requirements.
- If the candidate falls short of a required years-of-experience
  requirement, explicitly mention it.
- Do not treat similar technology names as equivalent unless
  the profile actually demonstrates that skill.
- Do not treat AI-assisted development or prompt engineering
  as machine learning engineering experience unless the profile
  explicitly demonstrates actual ML work.
- Be especially careful with mandatory requirements.
- A job with many missing mandatory requirements should receive
  a substantially lower score even if the candidate has several
  related skills.

CANDIDATE PROFILE:
---
{json.dumps(profile, indent=2)}
---

JOB:
---
{json.dumps(job, indent=2)}
---
"""

    response = client.responses.create(
        model="gpt-5.6",
        input=prompt,
    )

    text = response.output_text.strip()

    # Remove markdown code fences if the model adds them.
    if text.startswith("```"):
        text = (
            text
            .replace("```json", "")
            .replace("```", "")
            .strip()
        )

    return json.loads(text)


def print_match(
    index: int,
    result: dict,
) -> None:

    job = result["job"]
    match = result["match"]

    print("=" * 60)

    print(
        f"{index}. "
        f"{job['title']} — "
        f"{job['company']}"
    )

    print(
        f"Location: "
        f"{job.get('location', 'Not specified')}"
    )

    print(
        f"Match: "
        f"{match['match_score']}%"
    )

    print(
        f"Recommendation: "
        f"{match['recommendation']}"
    )

    print(
        "\nMatching skills:"
    )

    for skill in match["matching_skills"]:
        print(
            f"  ✓ {skill}"
        )

    print(
        "\nMissing skills:"
    )

    for skill in match["missing_skills"]:
        print(
            f"  • {skill}"
        )

    print(
        "\nWhy:"
    )

    for reason in match["reasons"]:
        print(
            f"  • {reason}"
        )

    if match["concerns"]:

        print(
            "\nConcerns:"
        )

        for concern in match["concerns"]:
            print(
                f"  • {concern}"
            )

    print()


def main():

    load_dotenv()

    profile = load_json(
        PROFILE_PATH
    )

    jobs = load_jobs()

    matches = load_matches()

    print(
        f"Found {len(jobs)} "
        f"filtered job(s)."
    )

    print()

    new_jobs = 0
    skipped_jobs = 0
    analyzed_job_ids = []

    for job in jobs:

        job_id = job["job_id"]

        job_hash = get_job_hash(
            job
        )

        cached = matches.get(
            job_id
        )

        # Skip jobs that have already been analyzed
        # and haven't changed.
        if (
            cached
            and cached.get("job_hash")
            == job_hash
        ):

            skipped_jobs += 1

            continue

        print(
            f"Analyzing: "
            f"{job['title']} — "
            f"{job['company']}"
        )

        try:

            result = match_job(
                profile,
                job,
            )

            matches[job_id] = {
                "job_id": job_id,
                "job_hash": job_hash,
                "job": job,
                "match": result,
            }

            # Save immediately after each AI call.
            save_json(
                MATCHES_PATH,
                matches,
            )

            analyzed_job_ids.append(
                job_id
            )

            new_jobs += 1

        except Exception as error:

            print(
                f"ERROR analyzing "
                f"{job['title']} — "
                f"{job['company']}: "
                f"{error}"
            )

            print()

    print()

    print(
        f"New jobs analyzed: "
        f"{new_jobs}"
    )

    print(
        f"Already analyzed: "
        f"{skipped_jobs}"
    )

    print()

    # If there are no new jobs, don't print
    # all old results.
    if new_jobs == 0:

        print(
            "No new or changed jobs "
            "to analyze."
        )

        return

    # Display ONLY jobs analyzed during
    # this run.
    results = [
        matches[job_id]
        for job_id in analyzed_job_ids
    ]

    results.sort(
        key=lambda item: item[
            "match"
        ]["match_score"],
        reverse=True,
    )

    for index, result in enumerate(
        results,
        start=1,
    ):

        print_match(
            index,
            result,
        )


if __name__ == "__main__":
    main()