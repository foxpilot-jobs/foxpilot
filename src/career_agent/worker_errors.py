"""Error classification for background job retry decisions."""

from __future__ import annotations

_RETRYABLE_SUBSTRINGS = (
    "connection",
    "timeout",
    "timed out",
    "unavailable",
    "rate limit",
    "429",
    "502",
    "503",
    "504",
    "temporary",
    "reset by peer",
    "broken pipe",
)


def classify_error(error: Exception) -> str:
    """Return ``'retryable'`` for transient errors, ``'permanent'`` otherwise."""
    message = str(error).lower()
    if any(hint in message for hint in _RETRYABLE_SUBSTRINGS):
        return "retryable"
    return "permanent"
