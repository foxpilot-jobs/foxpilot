from career_agent.sources.http_sources import (
    fetch_arbeitnow,
    fetch_ashby,
    fetch_greenhouse,
    fetch_hacker_news,
    fetch_jobicy,
    fetch_lever,
    fetch_remoteok,
    fetch_remotive,
    fetch_smartrecruiters,
    fetch_workable,
)


class FakeClient:
    def __init__(self, responses: dict[str, object]) -> None:
        self.responses = responses

    def get_json(self, url: str, params=None):
        key = url if params is None else (url, tuple(sorted(params.items())))
        return self.responses[key]


def test_remoteok_normalizes_jobs() -> None:
    client = FakeClient(
        {
            "https://remoteok.com/api": [
                {"legal": "metadata"},
                {
                    "id": 42,
                    "position": "Data Engineer",
                    "company": "Example",
                    "location": "Worldwide",
                    "url": "https://remoteok.com/example",
                    "description": "Build pipelines",
                },
            ]
        }
    )

    jobs = fetch_remoteok(client)

    assert jobs[0].source == "remoteok"
    assert jobs[0].source_job_id == "42"
    assert jobs[0].title == "Data Engineer"


def test_remoteok_filters_at_source_boundary() -> None:
    client = FakeClient(
        {
            "https://remoteok.com/api": [
                {"id": 1, "position": "Data Engineer", "description": "pipelines"},
                {"id": 2, "position": "Copywriter", "description": "content"},
            ]
        }
    )

    jobs = fetch_remoteok(client, ["Data Engineer"])

    assert [job.source_job_id for job in jobs] == ["1"]


def test_remotive_deduplicates_query_results() -> None:
    response = {"jobs": [{"id": 7, "title": "Analytics Engineer", "company_name": "Example", "url": "https://example.com", "description": "SQL"}]}
    client = FakeClient(
        {
            ("https://remotive.com/api/remote-jobs", (("search", "data engineer"),)): response,
            ("https://remotive.com/api/remote-jobs", (("search", "analytics engineer"),)): response,
        }
    )

    jobs = fetch_remotive(client, ["data engineer", "analytics engineer"])

    assert len(jobs) == 1


def test_lever_uses_configured_board_slug() -> None:
    client = FakeClient(
        {
            ("https://api.lever.co/v0/postings/example", (("mode", "json"),)): [
                {
                    "id": "lever-1",
                    "text": "Platform Engineer",
                    "hostedUrl": "https://jobs.lever.co/example/lever-1",
                    "descriptionPlain": "Build systems",
                    "categories": {"location": "Remote", "commitment": "Full-time"},
                }
            ]
        }
    )

    jobs = fetch_lever(client, [{"slug": "example", "company": "Example Co"}])

    assert jobs[0].company == "Example Co"
    assert jobs[0].work_type == "Full-time"


def test_greenhouse_uses_public_board_api() -> None:
    client = FakeClient(
        {
            ("https://boards-api.greenhouse.io/v1/boards/example/jobs", (("content", "true"),)): {
                "jobs": [
                    {
                        "id": 1,
                        "title": "Backend Engineer",
                        "location": {"name": "Remote"},
                        "absolute_url": "https://boards.greenhouse.io/example/jobs/1",
                        "content": "<p>Build APIs</p>",
                    }
                ]
            }
        }
    )

    jobs = fetch_greenhouse(client, [{"slug": "example", "company": "Example Co"}])

    assert jobs[0].source == "greenhouse"
    assert jobs[0].description == "Build APIs"


def test_ashby_uses_public_job_board_api() -> None:
    client = FakeClient(
        {
            "https://api.ashbyhq.com/posting-api/job-board/example": {
                "jobs": [
                    {
                        "id": "ashby-1",
                        "title": "Data Scientist",
                        "location": "Remote",
                        "jobUrl": "https://jobs.ashbyhq.com/example/ashby-1",
                        "descriptionHtml": "<p>Analyze data</p>",
                    }
                ]
            }
        }
    )

    jobs = fetch_ashby(client, [{"slug": "example", "company": "Example Co"}])

    assert jobs[0].source_job_id == "ashby-1"
    assert jobs[0].description == "Analyze data"


def test_workable_uses_public_account_api() -> None:
    client = FakeClient(
        {
            "https://apply.workable.com/api/v3/accounts/example/jobs": {
                "results": [
                    {
                        "shortcode": "workable-1",
                        "title": "Platform Engineer",
                        "location": {"city": "Remote"},
                        "url": "https://apply.workable.com/example/j/workable-1",
                    }
                ]
            }
        }
    )

    jobs = fetch_workable(client, [{"slug": "example", "company": "Example Co"}])

    assert jobs[0].source == "workable"


def test_smartrecruiters_uses_public_company_api() -> None:
    client = FakeClient(
        {
            ("https://api.smartrecruiters.com/v1/companies/example/postings", (("limit", 100),)): {
                "content": [
                    {
                        "id": "smart-1",
                        "name": "ML Engineer",
                        "location": {"city": "Bengaluru", "country": "India"},
                        "refNumber": "smart-1",
                    }
                ]
            }
        }
    )

    jobs = fetch_smartrecruiters(client, [{"slug": "example", "company": "Example Co"}])

    assert jobs[0].location == "Bengaluru, India"


def test_public_remote_aggregators_filter_queries() -> None:
    client = FakeClient(
        {
            "https://www.arbeitnow.com/api/job-board-api": {
                "data": [{"slug": "a1", "title": "Data Engineer", "description": "SQL"}]
            },
            ("https://jobicy.com/api/v2/remote-jobs", (("count", 50),)): {
                "jobs": [{"id": "j1", "jobTitle": "Data Engineer", "jobDescription": "Python"}]
            },
        }
    )

    assert len(fetch_arbeitnow(client, ["data engineer"])) == 1
    assert len(fetch_jobicy(client, ["data engineer"])) == 1


def test_hacker_news_normalizes_matching_comments() -> None:
    client = FakeClient(
        {
            ("https://hn.algolia.com/api/v1/search_by_date", (("hitsPerPage", 5), ("query", "Who is hiring"), ("tags", "ask_hn"))): {
                "hits": [{"objectID": "story-1", "title": "Ask HN: Who is hiring?"}]
            },
            "https://hn.algolia.com/api/v1/items/story-1": {
                "children": [{"id": 99, "text": "Data Engineer | Example | Remote | Python"}]
            },
        }
    )

    jobs = fetch_hacker_news(client, ["data engineer"], 10)

    assert jobs[0].source == "hackernews"
    assert jobs[0].source_job_id == "99"
