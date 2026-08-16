"""Small API-boundary security helpers."""

from __future__ import annotations

from threading import Lock
from time import monotonic


class InMemoryRateLimiter:
    """Process-local limiter for single-worker local/staging deployments."""

    def __init__(self) -> None:
        self._entries: dict[str, tuple[float, int]] = {}
        self._lock = Lock()

    def allow(self, key: str, limit: int, window_seconds: int = 60) -> bool:
        now = monotonic()
        with self._lock:
            started, count = self._entries.get(key, (now, 0))
            if now - started >= window_seconds:
                started, count = now, 0
            if count >= limit:
                self._entries[key] = (started, count)
                return False
            self._entries[key] = (started, count + 1)
            return True
