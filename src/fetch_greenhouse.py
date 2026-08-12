import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

from career_agent.config import load_config
from career_agent.storage import JobStore

JOBS_PATH = Path("data/jobs")
BROWSER_PROFILE = Path("data/browser-profile")
SEARCHES_PATH = Path("data/searches.json")


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def job_already_exists(job: dict) -> bool:
    """
    Check whether this job has already been saved.
    """

    job_id = job["source_job_id"]

    with JobStore(load_config().database_path) as store:
        return store.get_job(f"mygreenhouse_{job_id}") is not None


def save_job(job: dict) -> None:
    """
    Save a new job locally.
    """

    with JobStore(load_config().database_path) as store:
        store.upsert_job(job)


def load_searches() -> list[dict]:
    """
    Load configured MyGreenhouse searches.
    """

    if not SEARCHES_PATH.exists():
        raise FileNotFoundError(
            f"Search configuration not found: "
            f"{SEARCHES_PATH}"
        )

    with SEARCHES_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:

        data = json.load(file)

    searches = data.get(
        "searches",
        [],
    )

    if not isinstance(
        searches,
        list,
    ):
        raise TypeError(
            "'searches' must be a list."
        )

    return searches


def build_search_url(search: dict) -> str:
    """
    Build a MyGreenhouse search URL from
    the configuration.
    """

    query = search.get(
        "query",
        "",
    )

    date_posted = search.get(
        "date_posted",
        "past_day",
    )

    work_type = search.get(
        "work_type",
        "remote",
    )

    params = [
        ("query", query),
        ("date_posted", date_posted),
        ("work_type[]", work_type),
    ]

    return (
        "https://my.greenhouse.io/jobs?"
        + urlencode(params)
    )


def extract_job_posts_from_responses(
    responses: list,
) -> list[dict]:

    """
    Find the MyGreenhouse job-search response.
    """

    for response in responses:

        try:

            data = response.json()

            if not isinstance(
                data,
                dict,
            ):
                continue

            if (
                data.get("component")
                != "job_search"
            ):
                continue

            props = data.get(
                "props",
                {},
            )

            if not isinstance(
                props,
                dict,
            ):
                continue

            job_posts = props.get(
                "jobPosts"
            )

            if isinstance(
                job_posts,
                list,
            ):
                return job_posts

        except (PlaywrightError, ValueError):
            continue

    return []


def normalize_job(
    raw_job: dict,
) -> dict:

    locations = (
        raw_job.get("locations")
        or []
    )

    if isinstance(
        locations,
        list,
    ):

        location = ", ".join(
            str(item)
            for item in locations
        )

    else:

        location = str(
            locations
        )

    return {
        "source": "mygreenhouse",
        "source_job_id": str(
            raw_job.get("id")
        ),
        "title": raw_job.get(
            "title",
            "",
        ),
        "company": raw_job.get(
            "companyName",
            "",
        ),
        "location": location,
        "url": raw_job.get(
            "publicUrl",
            "",
        ),
        "description": "",
        "first_published": raw_job.get(
            "firstPublished"
        ),
        "work_type": raw_job.get(
            "workType"
        ),
        "pay_ranges": raw_job.get(
            "payRanges"
        ),
    }


def extract_job_description(
    context,
    job: dict,
) -> dict:

    url = job.get(
        "url"
    )

    if not url:
        return job

    page = context.new_page()

    try:

        print(
            f"  Fetching description: "
            f"{url}"
        )

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        page.wait_for_timeout(
            1500
        )

        body_text = (
            page.locator(
                "body"
            ).inner_text()
        )

        job["description"] = clean_text(
            body_text
        )

        if not job["title"]:

            try:

                job["title"] = clean_text(
                    page.locator(
                        "h1"
                    ).first.inner_text()
                )

            except PlaywrightError:
                pass

    except PlaywrightError as error:

        print(
            f"  Warning: could not fetch "
            f"description: {error}"
        )

    finally:

        page.close()

    return job


def fetch_single_search(
    context,
    search_url: str,
    search_name: str,
) -> list[dict] | None:

    captured_responses = []

    page = context.new_page()

    def handle_response(response):

        try:

            url = response.url

            if (
                "jobs" in url.lower()
                or "run" in url.lower()
                or "search" in url.lower()
            ):

                print(
                    f"[NETWORK] "
                    f"{response.status} "
                    f"{response.headers.get('content-type', '')} "
                    f"{url}"
                )

            captured_responses.append(
                response
            )

        except PlaywrightError:
            pass

    page.on(
        "response",
        handle_response,
    )

    try:

        print()
        print(
            "=" * 70
        )

        print(
            f"SEARCH: {search_name}"
        )

        print(
            search_url
        )

        print(
            "=" * 70
        )

        page.goto(
            search_url,
            wait_until="domcontentloaded",
            timeout=30000,
        )

        # Give the React application time to load
        # and request the search data.
        page.wait_for_timeout(
            8000
        )

        raw_jobs = (
            extract_job_posts_from_responses(
                captured_responses
            )
        )

        redirected = any(
            response.status in {301, 302, 303, 307, 308}
            for response in captured_responses
        )

        if not raw_jobs and redirected and sys.stdin.isatty():
            print()
            print(
                "Greenhouse redirected the request. "
                "Log in in the open browser window, then return here."
            )
            input("Press Enter to retry this search... ")
            captured_responses.clear()
            try:
                page.reload(
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
            except PlaywrightError as error:
                print(
                    "The browser window was closed before the search could be retried: "
                    f"{error}"
                )
                return None

            page.wait_for_timeout(8000)
            raw_jobs = extract_job_posts_from_responses(
                captured_responses
            )

        print()
        print(
            f"Found {len(raw_jobs)} "
            f"job(s)."
        )

        normalized_jobs = []

        for raw_job in raw_jobs:

            job = normalize_job(
                raw_job
            )

            normalized_jobs.append(
                job
            )

        new_jobs = []
        existing_jobs = []

        # Deduplicate BEFORE opening individual
        # job pages.
        for job in normalized_jobs:

            if job_already_exists(
                job
            ):

                existing_jobs.append(
                    job
                )

            else:

                new_jobs.append(
                    job
                )

        print(
            f"New: {len(new_jobs)}"
        )

        print(
            f"Already known: "
            f"{len(existing_jobs)}"
        )

        # Fetch descriptions only for new jobs.
        jobs = []

        for index, job in enumerate(
            new_jobs,
            start=1,
        ):

            print()
            print(
                f"[{index}/{len(new_jobs)}] "
                f"{job['title']} — "
                f"{job['company']}"
            )

            job = extract_job_description(
                context,
                job,
            )

            save_job(job)

            jobs.append(
                job
            )

        return jobs

    finally:
        try:
            page.close()
        except PlaywrightError:
            pass


def fetch_jobs(
    searches: list[dict],
) -> list[dict]:

    """
    Run multiple searches using one persistent
    browser context.
    """

    all_new_jobs = []

    with JobStore(load_config().database_path) as store:
        store.import_legacy_jobs(JOBS_PATH)

    with sync_playwright() as playwright:

        print(
            "Launching persistent browser..."
        )

        context = (
            playwright.chromium
            .launch_persistent_context(
                user_data_dir=str(
                    BROWSER_PROFILE
                ),
                headless=False,
            )
        )

        print()
        print(
            "Using saved MyGreenhouse "
            "browser session."
        )

        print(
            "If you are not logged in, "
            "log in manually in the browser."
        )

        for search in searches:

            search_name = search.get(
                "name",
                "Unnamed Search",
            )

            search_url = build_search_url(
                search
            )

            new_jobs = fetch_single_search(
                context,
                search_url,
                search_name,
            )

            if new_jobs is None:
                print("Stopping ingestion because the browser is no longer available.")
                break

            all_new_jobs.extend(
                new_jobs
            )

        try:
            context.close()
        except PlaywrightError:
            pass

    return all_new_jobs


def main():

    JOBS_PATH.mkdir(
        parents=True,
        exist_ok=True,
    )

    with JobStore(load_config().database_path) as store:
        store.import_legacy_jobs(JOBS_PATH)

    BROWSER_PROFILE.mkdir(
        parents=True,
        exist_ok=True,
    )

    # If a URL is supplied directly, keep supporting
    # the old one-search command.
    if len(sys.argv) == 2:

        searches = [
            {
                "name": "Manual Search",
                "query": "",
                "date_posted": "past_day",
                "work_type": "remote",
                "url": sys.argv[1],
            }
        ]

        # Handle direct URL separately.
        search_url = sys.argv[1]

        with sync_playwright() as playwright:

            context = (
                playwright.chromium
                .launch_persistent_context(
                    user_data_dir=str(
                        BROWSER_PROFILE
                    ),
                    headless=False,
                )
            )

            new_jobs = fetch_single_search(
                context,
                search_url,
                "Manual Search",
            )

            context.close()

        print()
        print(
            f"New jobs processed: "
            f"{len(new_jobs)}"
        )

        return

    searches = load_searches()

    print(
        f"Loaded {len(searches)} "
        f"configured searches."
    )

    new_jobs = fetch_jobs(
        searches
    )

    print()
    print(
        "=" * 70
    )

    print(
        "INGESTION COMPLETE"
    )

    print(
        f"New jobs discovered: "
        f"{len(new_jobs)}"
    )

    print(
        "=" * 70
    )


if __name__ == "__main__":
    main()
