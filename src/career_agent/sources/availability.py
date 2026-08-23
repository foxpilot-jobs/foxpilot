"""Bounded availability checks for previously ingested public job listings."""

from __future__ import annotations

import httpx

from ..config import load_config
from ..storage import JobStore


def refresh_listing_availability(limit: int = 100, stale_after_hours: int = 24) -> dict[str, int]:
    """Check stale listing URLs and retain history for unavailable postings."""
    checked = active = inactive = unknown = 0
    with JobStore(load_config().resolved_database_url) as store:
        listings = store.list_listings_for_check(limit, stale_after_hours)
        with httpx.Client(
            follow_redirects=True,
            timeout=httpx.Timeout(15.0, connect=8.0),
            headers={"User-Agent": "FoxPilot/0.1 availability checker"},
        ) as client:
            for listing in listings:
                checked += 1
                try:
                    response = client.head(listing["url"])
                    if response.status_code == 405:
                        response = client.get(listing["url"])
                    if response.status_code in {404, 410}:
                        store.mark_listing_inactive(
                            listing["source"], listing["source_job_id"], f"HTTP {response.status_code}"
                        )
                        inactive += 1
                    elif 200 <= response.status_code < 400:
                        store.mark_listing_active(listing["source"], listing["source_job_id"])
                        active += 1
                    else:
                        unknown += 1
                except httpx.HTTPError:
                    unknown += 1
    return {"checked": checked, "active": active, "inactive": inactive, "unknown": unknown}
