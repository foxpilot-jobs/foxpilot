from career_agent.sources.http_sources import (
    fetch_hacker_news,
    fetch_lever,
    fetch_remoteok,
    fetch_remotive,
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
