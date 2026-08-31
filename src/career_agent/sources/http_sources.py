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
from ..search import profile_search_queries
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

    def get_text(self, url: str, params: dict[str, Any] | None = None) -> str:
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
            return response.text
        raise RuntimeError(f"Unable to fetch {url}")


def _clean(value: Any) -> str:
    text = html.unescape(str(value or ""))
    return re.sub(r"\s+", " ", text).strip()


def _clean_html(value: Any) -> str:
    return _clean(re.sub(r"<[^>]+>", " ", html.unescape(str(value or ""))))


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


def fetch_remoteok(client: PublicSourceClient, queries: list[str] | None = None) -> list[SourceJob]:
    payload = client.get_json("https://remoteok.com/api")
    jobs: list[SourceJob] = []
    for raw in payload if isinstance(payload, list) else []:
        if not isinstance(raw, dict) or not raw.get("id"):
            continue
        searchable = _clean(f"{raw.get('position', '')} {raw.get('description', '')}").casefold()
        if queries and not any(str(query).casefold() in searchable for query in queries):
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


def fetch_greenhouse(client: PublicSourceClient, boards: list[dict[str, Any]]) -> list[SourceJob]:
    jobs: list[SourceJob] = []
    for board in boards:
        slug = str(board.get("slug", "")).strip()
        if not slug:
            continue
        payload = client.get_json(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs", {"content": "true"})
        for raw in payload.get("jobs", []) if isinstance(payload, dict) else []:
            location = raw.get("location") or {}
            item = _job(
                "greenhouse",
                raw.get("id") or raw.get("internal_job_id"),
                raw.get("title"),
                board.get("company") or slug,
                location.get("name") if isinstance(location, dict) else location,
                raw.get("absolute_url"),
                _clean_html(raw.get("content")),
                raw.get("updated_at"),
                None,
                raw,
            )
            if item:
                jobs.append(item)
    return jobs


def fetch_ashby(client: PublicSourceClient, boards: list[dict[str, Any]]) -> list[SourceJob]:
    jobs: list[SourceJob] = []
    for board in boards:
        slug = str(board.get("slug", "")).strip()
        if not slug:
            continue
        payload = client.get_json(f"https://api.ashbyhq.com/posting-api/job-board/{slug}")
        for raw in payload.get("jobs", []) if isinstance(payload, dict) else []:
            item = _job(
                "ashby",
                raw.get("id") or raw.get("jobUrl"),
                raw.get("title"),
                board.get("company") or raw.get("teamName") or slug,
                raw.get("location") or ("Remote" if raw.get("isRemote") else ""),
                raw.get("jobUrl"),
                _clean_html(raw.get("descriptionHtml") or raw.get("descriptionPlain")),
                raw.get("publishedAt"),
                raw.get("employmentType"),
                raw,
            )
            if item:
                jobs.append(item)
    return jobs


def fetch_workable(client: PublicSourceClient, boards: list[dict[str, Any]]) -> list[SourceJob]:
    jobs: list[SourceJob] = []
    for board in boards:
        slug = str(board.get("slug", "")).strip()
        if not slug:
            continue
        payload = client.get_json(f"https://apply.workable.com/api/v3/accounts/{slug}/jobs")
        raw_jobs = payload.get("results", payload.get("jobs", [])) if isinstance(payload, dict) else []
        for raw in raw_jobs if isinstance(raw_jobs, list) else []:
            location = raw.get("location") or raw.get("locations") or ""
            if isinstance(location, list):
                location = ", ".join(_clean(item.get("city") or item.get("name")) for item in location if isinstance(item, dict))
            item = _job(
                "workable",
                raw.get("shortcode") or raw.get("id"),
                raw.get("title"),
                board.get("company") or raw.get("company") or slug,
                location,
                raw.get("url") or raw.get("shortlink") or f"https://apply.workable.com/{slug}/j/{raw.get('shortcode')}",
                _clean_html(raw.get("description") or raw.get("descriptionHtml")),
                raw.get("published") or raw.get("created_at"),
                raw.get("employment_type"),
                raw,
            )
            if item:
                jobs.append(item)
    return jobs


def fetch_smartrecruiters(client: PublicSourceClient, boards: list[dict[str, Any]]) -> list[SourceJob]:
    jobs: list[SourceJob] = []
    for board in boards:
        slug = str(board.get("slug", "")).strip()
        if not slug:
            continue
        payload = client.get_json(f"https://api.smartrecruiters.com/v1/companies/{slug}/postings", {"limit": 100})
        for raw in payload.get("content", []) if isinstance(payload, dict) else []:
            location = raw.get("location") or {}
            if isinstance(location, dict):
                location = ", ".join(
                    _clean(location.get(key)) for key in ("city", "region", "country") if _clean(location.get(key))
                )
            job_id = raw.get("id") or raw.get("refNumber")
            item = _job(
                "smartrecruiters",
                job_id,
                raw.get("name"),
                board.get("company") or slug,
                location,
                raw.get("refNumber") and f"https://jobs.smartrecruiters.com/{slug}/{raw['refNumber']}",
                _clean_html(raw.get("jobAd", {}).get("sections", {}).get("jobDescription", {}).get("text"))
                if isinstance(raw.get("jobAd"), dict)
                else "",
                raw.get("releasedDate"),
                raw.get("typeOfEmployment"),
                raw,
            )
            if item:
                jobs.append(item)
    return jobs


def fetch_arbeitnow(client: PublicSourceClient, queries: list[str]) -> list[SourceJob]:
    payload = client.get_json("https://www.arbeitnow.com/api/job-board-api")
    jobs: list[SourceJob] = []
    for raw in payload.get("data", []) if isinstance(payload, dict) else []:
        searchable = _clean(f"{raw.get('title', '')} {raw.get('description', '')}").casefold()
        if queries and not any(str(query).casefold() in searchable for query in queries):
            continue
        item = _job(
            "arbeitnow",
            raw.get("slug") or raw.get("id"),
            raw.get("title"),
            raw.get("company_name"),
            raw.get("location"),
            raw.get("url"),
            _clean_html(raw.get("description")),
            raw.get("created_at"),
            "remote" if raw.get("remote") else None,
            raw,
        )
        if item:
            jobs.append(item)
    return jobs


def fetch_jobicy(client: PublicSourceClient, queries: list[str]) -> list[SourceJob]:
    payload = client.get_json("https://jobicy.com/api/v2/remote-jobs", {"count": 50})
    jobs: list[SourceJob] = []
    for raw in payload.get("jobs", []) if isinstance(payload, dict) else []:
        searchable = _clean(f"{raw.get('jobTitle', '')} {raw.get('jobDescription', '')}").casefold()
        if queries and not any(str(query).casefold() in searchable for query in queries):
            continue
        item = _job(
            "jobicy",
            raw.get("id") or raw.get("url"),
            raw.get("jobTitle"),
            raw.get("companyName"),
            raw.get("jobGeo") or "Remote",
            raw.get("url"),
            _clean_html(raw.get("jobDescription")),
            raw.get("pubDate"),
            raw.get("jobType"),
            raw,
        )
        if item:
            jobs.append(item)
    return jobs


def fetch_weworkremotely(client: PublicSourceClient, queries: list[str] | None = None) -> list[SourceJob]:
    import xml.etree.ElementTree as ET

    try:
        response_text = client.get_text("https://weworkremotely.com/remote-jobs.rss")
    except (httpx.HTTPError, RuntimeError):
        return []

    jobs: list[SourceJob] = []
    try:
        root = ET.fromstring(response_text)
        for item_elem in root.findall("./channel/item"):
            title_raw = _clean(item_elem.findtext("title"))
            link = _clean(item_elem.findtext("link"))
            guid = _clean(item_elem.findtext("guid")) or link
            pub_date = _clean(item_elem.findtext("pubDate"))
            description = _clean_html(item_elem.findtext("description"))
            category = _clean(item_elem.findtext("category"))

            company = "WeWorkRemotely"
            title = title_raw
            if ":" in title_raw:
                parts = title_raw.split(":", 1)
                company = parts[0].strip()
                title = parts[1].strip()

            searchable = f"{title} {description} {category}".casefold()
            if queries and not any(str(query).casefold() in searchable for query in queries):
                continue

            job_item = _job(
                "weworkremotely",
                guid,
                title,
                company,
                category or "Remote",
                link,
                description,
                pub_date,
                "remote",
                {"raw_category": category},
            )
            if job_item:
                jobs.append(job_item)
    except ET.ParseError:
        return jobs
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


def _save_jobs(jobs: list[SourceJob | dict[str, Any]], user_id: str) -> dict[str, int]:
    if not jobs:
        return {"inserted": 0, "updated": 0, "deduplicated": 0}
    with JobStore(load_config().resolved_database_url, user_id=user_id) as store:
        job_dicts = [j if isinstance(j, dict) else j.as_dict() for j in jobs]
        return store.bulk_upsert_jobs(job_dicts)


from ..tech_classification import classify_tech_job
from ..work_arrangement import parse_work_arrangement


def fetch_configured_sources(
    profile: dict | None = None,
    user_id: str = "local-user",
    max_jobs: int | None = None,
    miss_threshold: int = 2,
    return_details: bool = False,
) -> int | dict[str, Any]:
    config = _load_source_config()
    queries = profile_search_queries(profile) if profile else []
    client = PublicSourceClient()
    total = 0
    total_raw_fetched = 0
    total_tech_accepted = 0
    total_non_tech_rejected = 0
    source_stats: list[dict[str, Any]] = []

    adapters = [
        ("RemoteOK", lambda: fetch_remoteok(client, queries), config.get("remoteok", {}).get("enabled", True)),
        ("Remotive", lambda: fetch_remotive(client, queries), config.get("remotive", {}).get("enabled", True)),
        ("WeWorkRemotely", lambda: fetch_weworkremotely(client, queries), config.get("weworkremotely", {}).get("enabled", True)),
        ("Lever", lambda: fetch_lever(client, config.get("lever", {}).get("boards", [])), bool(config.get("lever", {}).get("boards"))),
        ("Greenhouse", lambda: fetch_greenhouse(client, config.get("greenhouse", {}).get("boards", [])), bool(config.get("greenhouse", {}).get("boards"))),
        ("Ashby", lambda: fetch_ashby(client, config.get("ashby", {}).get("boards", [])), bool(config.get("ashby", {}).get("boards"))),
        ("Workable", lambda: fetch_workable(client, config.get("workable", {}).get("boards", [])), bool(config.get("workable", {}).get("boards"))),
        ("SmartRecruiters", lambda: fetch_smartrecruiters(client, config.get("smartrecruiters", {}).get("boards", [])), bool(config.get("smartrecruiters", {}).get("boards"))),
        ("Hacker News", lambda: fetch_hacker_news(client, queries, int(config.get("hacker_news", {}).get("comment_limit", 500))), config.get("hacker_news", {}).get("enabled", True)),
        ("Arbeitnow", lambda: fetch_arbeitnow(client, queries), config.get("arbeitnow", {}).get("enabled", True)),
        ("Jobicy", lambda: fetch_jobicy(client, queries), config.get("jobicy", {}).get("enabled", True)),
    ]
    try:
        for name, fetch, enabled in adapters:
            if not enabled:
                print(f"[SOURCE] {name}: disabled")
                source_stats.append({
                    "source": name.lower(),
                    "status": "disabled",
                    "fetched": 0,
                    "tech_accepted": 0,
                    "non_tech_rejected": 0,
                    "inserted": 0,
                    "updated": 0,
                    "archived_listings": 0,
                    "archived_jobs": 0,
                    "error": None,
                })
                continue

            if max_jobs is not None and total >= max_jobs:
                print(f"[SOURCE] Cap reached ({total}/{max_jobs} jobs), stopping ingestion.")
                break

            try:
                raw_jobs = fetch()
                if max_jobs is not None and (total + len(raw_jobs)) > max_jobs:
                    remaining = max_jobs - total
                    raw_jobs = raw_jobs[:remaining]

                tech_accepted_jobs: list[dict[str, Any]] = []
                non_tech_rejected_count = 0

                for j in raw_jobs:
                    j_dict = j.as_dict()
                    res = classify_tech_job(j_dict)
                    wa = parse_work_arrangement(j_dict)
                    wa_dict = wa.as_dict()

                    payload = j_dict.get("source_payload")
                    if payload is None or not isinstance(payload, dict):
                        payload = {}

                    payload["tech_classification"] = {
                        "is_tech_job": res.is_tech_job,
                        "tech_category": res.tech_category,
                        "confidence": res.confidence,
                        "score": res.score,
                        "signals": res.signals,
                    }
                    payload["work_arrangement"] = wa_dict
                    j_dict["source_payload"] = payload
                    j_dict["work_arrangement"] = wa_dict

                    if res.is_tech_job:
                        tech_accepted_jobs.append(j_dict)
                    else:
                        non_tech_rejected_count += 1

                total_raw_fetched += len(raw_jobs)
                total_tech_accepted += len(tech_accepted_jobs)
                total_non_tech_rejected += non_tech_rejected_count

                stats = _save_jobs(tech_accepted_jobs, user_id)
                saved = stats.get("inserted", 0) + stats.get("updated", 0)
                total += saved

                reconcile_stats = {"archived_listings": 0, "archived_jobs": 0}
                if max_jobs is None:
                    returned_ids = {str(j.source_job_id) for j in raw_jobs if j.source_job_id}
                    with JobStore(load_config().resolved_database_url, user_id=user_id) as store:
                        reconcile_stats = store.reconcile_source_listings(
                            source=name.lower(),
                            returned_source_job_ids=returned_ids,
                            miss_threshold=miss_threshold,
                        )

                source_stats.append({
                    "source": name.lower(),
                    "status": "success",
                    "fetched": len(raw_jobs),
                    "tech_accepted": len(tech_accepted_jobs),
                    "non_tech_rejected": non_tech_rejected_count,
                    "inserted": stats.get("inserted", 0),
                    "updated": stats.get("updated", 0),
                    "deduplicated": stats.get("deduplicated", 0),
                    "archived_listings": reconcile_stats.get("archived_listings", 0),
                    "archived_jobs": reconcile_stats.get("archived_jobs", 0),
                    "error": None,
                })
                print(
                    f"[SOURCE] {name}: fetched {len(raw_jobs)} raw, "
                    f"accepted {len(tech_accepted_jobs)} tech (rejected {non_tech_rejected_count} non-tech), "
                    f"upserted {saved}, archived listings {reconcile_stats.get('archived_listings', 0)}"
                )
            except Exception as error:  # noqa: BLE001 - isolate every external source
                print(f"[SOURCE] {name}: failed, continuing: {error}")
                source_stats.append({
                    "source": name.lower(),
                    "status": "failed",
                    "fetched": 0,
                    "tech_accepted": 0,
                    "non_tech_rejected": 0,
                    "inserted": 0,
                    "updated": 0,
                    "archived_listings": 0,
                    "archived_jobs": 0,
                    "error": str(error),
                })
    finally:
        client.close()

    if return_details:
        return {
            "jobs_upserted": total,
            "raw_fetched": total_raw_fetched,
            "tech_accepted": total_tech_accepted,
            "non_tech_rejected": total_non_tech_rejected,
            "source_stats": source_stats,
        }
    return total
