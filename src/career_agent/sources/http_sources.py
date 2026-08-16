"""Public HTTP job-source adapters with bounded retries and isolation."""

from __future__ import annotations

import html
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

from ..config import load_config
from ..storage import JobStore

DEFAULT_SOURCES_PATH = Path("data/sources.json")
USER_AGENT = "FoxPilot/0.1 (+https://github.com/foxpilot; job discovery client)"


@dataclass(frozen=True)
class SourceJob:
    source: str
    source_job_id: str
    title: str
    company: str
    location: str
    url: str
    description: str
    first_published: str | None = None
    work_type: str | None = None
    payload: dict[str, Any] | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "source_job_id": self.source_job_id,
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "url": self.url,
            "description": self.description,
            "first_published": self.first_published,
            "work_type": self.work_type,
            "source_payload": self.payload or {},
        }


class PublicSourceClient:
    def __init__(self) -> None:
        self.client = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
            follow_redirects=True,
            timeout=httpx.Timeout(20.0, connect=10.0),
        )
        self._last_request = 0.0

    def close(self) -> None:
        self.client.close()

    def get_json(self, url: str, params: dict[str, Any] | None = None) -> Any:
        wait = 0.25 - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        for attempt in range(3):
            response = self.client.get(url, params=params)
            self._last_request = time.monotonic()
            if response.status_code == 429 or response.status_code >= 500:
                if attempt == 2:
                    response.raise_for_status()
                time.sleep(min(float(response.headers.get("retry-after", "1")), 5.0))
                continue
            response.raise_for_status()
            return response.json()
        raise RuntimeError(f"Unable to fetch {url}")


def _clean(value: Any) -> str:
    text = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _job(
    source: str,
    source_job_id: Any,
    title: Any,
    company: Any,
    location: Any,
    url: Any,
    description: Any,
    published: Any = None,
    work_type: Any = None,
    payload: dict[str, Any] | None = None,
) -> SourceJob | None:
    clean_title = _clean(title)
    if not clean_title or not source_job_id:
        return None
    return SourceJob(
        source=source,
        source_job_id=str(source_job_id),
        title=clean_title,
        company=_clean(company) or "Unknown company",
        location=_clean(location),
        url=_clean(url),
        description=_clean(description),
        first_published=_clean(published) or None,
        work_type=_clean(work_type) or None,
        payload=payload,
    )


def fetch_remoteok(client: PublicSourceClient) -> list[SourceJob]:
    payload = client.get_json("https://remoteok.com/api")
    jobs: list[SourceJob] = []
    for raw in payload if isinstance(payload, list) else []:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        item = _job(
            "remoteok",
            raw.get("id") or raw.get("slug"),
            raw.get("position"),
            raw.get("company"),
            raw.get("location"),
            raw.get("url") or f"https://remoteok.com/remote-jobs/{raw.get('id')}",
            raw.get("description"),
            raw.get("date"),
            "remote",
            raw,
        )
        if item:
            jobs.append(item)
    return jobs


def fetch_remotive(client: PublicSourceClient, queries: list[str]) -> list[SourceJob]:
    jobs: list[SourceJob] = []
    seen: set[str] = set()
    for query in queries or [""]:
        payload = client.get_json("https://remotive.com/api/remote-jobs", {"search": query})
        for raw in payload.get("jobs", []) if isinstance(payload, dict) else []:
            if not isinstance(raw, dict) or str(raw.get("id")) in seen:
                continue
            seen.add(str(raw.get("id")))
            item = _job(
                "remotive",
                raw.get("id"),
                raw.get("title"),
                raw.get("company_name"),
                raw.get("candidate_required_location"),
                raw.get("url"),
                raw.get("description"),
                raw.get("publication_date"),
                "remote",
                raw,
            )
            if item:
                jobs.append(item)
    return jobs


def fetch_lever(client: PublicSourceClient, boards: list[dict[str, Any]]) -> list[SourceJob]:
    jobs: list[SourceJob] = []
    for board in boards:
        slug = str(board.get("slug", "")).strip()
        if not slug:
            continue
        payload = client.get_json(f"https://api.lever.co/v0/postings/{slug}", {"mode": "json"})
        for raw in payload if isinstance(payload, list) else []:
            categories = raw.get("categories") or {}
            item = _job(
                "lever",
                raw.get("id"),
                raw.get("text"),
                board.get("company") or slug,
                categories.get("location"),
                raw.get("hostedUrl") or raw.get("applyUrl"),
                raw.get("descriptionPlain") or raw.get("description"),
                raw.get("createdAt"),
                categories.get("commitment"),
                raw,
            )
            if item:
                jobs.append(item)
    return jobs


def _hn_title(text: str) -> str:
    return (_clean(text).split(" | ")[0].split("\n")[0] or "Hacker News hiring opportunity")[:160]


def fetch_hacker_news(client: PublicSourceClient, queries: list[str], comment_limit: int) -> list[SourceJob]:
    stories = client.get_json(
        "https://hn.algolia.com/api/v1/search_by_date",
        {"tags": "ask_hn", "query": "Who is hiring", "hitsPerPage": 5},
    )
    jobs: list[SourceJob] = []
    for story in stories.get("hits", []) if isinstance(stories, dict) else []:
        story_id = story.get("objectID")
        if not story_id:
            continue
        item = client.get_json(f"https://hn.algolia.com/api/v1/items/{story_id}")
        comments = item.get("children", []) if isinstance(item, dict) else []
        for comment in comments[:comment_limit]:
            text = _clean(comment.get("text")) if isinstance(comment, dict) else ""
            if queries and not any(query.lower() in text.lower() for query in queries):
                continue
            comment_id = comment.get("id") if isinstance(comment, dict) else None
            job = _job(
                "hackernews",
                comment_id,
                _hn_title(text),
                "Hacker News hiring thread",
                "Remote / see post",
                f"https://news.ycombinator.com/item?id={comment_id}",
                text,
                story.get("created_at"),
                "remote",
                {"thread_id": story_id, "thread_title": story.get("title")},
            )
            if job:
                jobs.append(job)
    return jobs


def _load_source_config() -> dict[str, Any]:
    path = Path(os.getenv("FOXPILOT_SOURCES_CONFIG", str(DEFAULT_SOURCES_PATH)))
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _save_jobs(jobs: list[SourceJob]) -> int:
    with JobStore(load_config().resolved_database_url) as store:
        for job in jobs:
            store.upsert_job(job.as_dict())
    return len(jobs)


def fetch_configured_sources() -> int:
    config = _load_source_config()
    queries = [str(query) for query in config.get("queries", [])]
    client = PublicSourceClient()
    total = 0
    adapters = [
        ("RemoteOK", lambda: fetch_remoteok(client), config.get("remoteok", {}).get("enabled", True)),
        ("Remotive", lambda: fetch_remotive(client, queries), config.get("remotive", {}).get("enabled", True)),
        ("Lever", lambda: fetch_lever(client, config.get("lever", {}).get("boards", [])), bool(config.get("lever", {}).get("boards"))),
        ("Hacker News", lambda: fetch_hacker_news(client, queries, int(config.get("hacker_news", {}).get("comment_limit", 500))), config.get("hacker_news", {}).get("enabled", True)),
    ]
    try:
        for name, fetch, enabled in adapters:
            if not enabled:
                print(f"[SOURCE] {name}: disabled")
                continue
            try:
                jobs = fetch()
                saved = _save_jobs(jobs)
                total += saved
                print(f"[SOURCE] {name}: fetched {len(jobs)}, upserted {saved}")
            except Exception as error:  # noqa: BLE001 - isolate every external source
                print(f"[SOURCE] {name}: failed, continuing: {error}")
    finally:
        client.close()
    return total
