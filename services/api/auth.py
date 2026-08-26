"""Small deployment guard for local API use and pre-native-auth staging."""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from fastapi import HTTPException, Request
from pwdlib import PasswordHash

from career_agent.storage import JobStore

SESSION_COOKIE = "foxpilot_session"
SESSION_DAYS = 30
password_hash = PasswordHash.recommended()

COMMON_BREACHED_PASSWORDS = frozenset(
    {
        "123456789012",
        "password1234",
        "password123456",
        "qwertyuiop12",
        "qwerty123456",
        "letmein123456",
        "welcome123456",
        "iloveyou12345",
        "admin1234567",
        "changeme1234",
        "correcthorsebatterystaple",
    }
)


@dataclass(frozen=True)
class AuthContext:
    """Authenticated identity passed from the API boundary to application code."""

    user_id: str
    email: str | None = None
    email_verified: bool = True


def normalize_email(email: str) -> str:
    return email.strip().lower()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, encoded: str | None) -> bool:
    return bool(encoded) and password_hash.verify(password, encoded)


def is_breached_password(password: str) -> bool:
    return password.strip().lower() in COMMON_BREACHED_PASSWORDS


def _store(request: Request) -> JobStore:
    return JobStore(request.app.state.service.config.resolved_database_url)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_auth_token(store: JobStore, user_id: str, purpose: str, days: int = 1) -> str:
    token = secrets.token_urlsafe(48)
    store.create_auth_token(
        token_id=str(uuid4()),
        user_id=user_id,
        purpose=purpose,
        token_hash=_token_hash(token),
        expires_at=datetime.now(UTC) + timedelta(days=days),
    )
    return token


def consume_auth_token(store: JobStore, token: str, purpose: str) -> dict | None:
    return store.consume_auth_token(_token_hash(token), purpose)


def create_session(store: JobStore, user_id: str) -> str:
    token = secrets.token_urlsafe(48)
    store.create_session(
        session_id=str(uuid4()),
        user_id=user_id,
        token_hash=_token_hash(token),
        expires_at=datetime.now(UTC) + timedelta(days=SESSION_DAYS),
    )
    return token


def _cookie_domain() -> str | None:
    """Derive the cookie domain from FOXPILOT_PUBLIC_URL so the session cookie
    is shared between the frontend (foxpilot.in) and the API (api.foxpilot.in).
    Returns None for localhost / local development."""
    public_url = os.getenv("FOXPILOT_PUBLIC_URL", "")
    if not public_url or "localhost" in public_url or "127.0.0.1" in public_url:
        return None
    try:
        from urllib.parse import urlparse
        host = urlparse(public_url).hostname or ""
        # Use the registrable domain (e.g. foxpilot.in from www.foxpilot.in)
        parts = host.split(".")
        if len(parts) >= 2:
            return f".{'.'.join(parts[-2:])}"
    except Exception:  # noqa: BLE001
        return None
    return None


def set_session_cookie(response, token: str, production: bool) -> None:
    hosted = production or os.getenv("FOXPILOT_PUBLIC_URL", "").lower().startswith("https://")
    domain = _cookie_domain()
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        secure=hosted,
        samesite="none" if hosted else "lax",
        path="/",
        domain=domain,
    )


def hosted_cookie(production: bool) -> bool:
    """Return whether browser cookies cross the hosted web/API boundary."""
    return production or os.getenv("FOXPILOT_PUBLIC_URL", "").lower().startswith("https://")


_LAST_CLEANUP_TIME: datetime | None = None
_CLEANUP_LOCK = threading.Lock()


def maybe_cleanup_sessions(store: JobStore, interval_minutes: int = 60) -> None:
    global _LAST_CLEANUP_TIME
    now = datetime.now(UTC)
    with _CLEANUP_LOCK:
        if _LAST_CLEANUP_TIME is None or (now - _LAST_CLEANUP_TIME) > timedelta(minutes=interval_minutes):
            _LAST_CLEANUP_TIME = now
            store.cleanup_sessions()


def clear_session_cookie(response) -> None:
    domain = _cookie_domain()
    response.delete_cookie(SESSION_COOKIE, path="/", domain=domain)


def current_native_user(request: Request) -> AuthContext:
    t_start = time.perf_counter()
    from career_agent.storage.database import _REQUEST_TIMINGS
    ctx = _REQUEST_TIMINGS.get()
    if ctx is not None:
        ctx["events"].append(("current_native_user_start", t_start))

    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise _unauthorized()

    if ctx is not None:
        ctx["events"].append(("store_init_start", time.perf_counter()))
    store = _store(request)
    if ctx is not None:
        ctx["events"].append(("store_init_end", time.perf_counter()))

    try:
        if ctx is not None:
            ctx["events"].append(("maybe_cleanup_start", time.perf_counter()))
        maybe_cleanup_sessions(store)
        if ctx is not None:
            ctx["events"].append(("maybe_cleanup_end", time.perf_counter()))

        user = store.get_session_user(_token_hash(token))
    finally:
        if ctx is not None:
            ctx["events"].append(("store_close_start", time.perf_counter()))
        store.close()
        if ctx is not None:
            ctx["events"].append(("store_close_end", time.perf_counter()))

    if not user:
        raise _unauthorized()
    if os.getenv("FOXPILOT_ENV", "local").lower() == "production" and not user["email_verified"]:
        raise HTTPException(status_code=403, detail="Verify your email before signing in")

    elapsed_ms = (time.perf_counter() - t_start) * 1000
    if ctx is not None:
        ctx["auth_ms"] = elapsed_ms
        ctx["events"].append(("current_native_user_end", time.perf_counter()))
    return AuthContext(
        user_id=user["user_id"],
        email=user["email"],
        email_verified=bool(user.get("email_verified", True)),
    )


def get_user_by_email(request: Request, email: str) -> dict | None:
    store = _store(request)
    try:
        return store.get_user_by_email(normalize_email(email))
    finally:
        store.close()


def _unauthorized() -> HTTPException:
    return HTTPException(
        status_code=401,
        detail="A valid bearer token is required",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_api_access(request: Request) -> AuthContext:
    """Return the request identity for local or token-protected API access.

    Local mode intentionally uses one explicit local identity. Token mode remains
    a temporary single-user staging guard until native FoxPilot auth lands.
    """
    mode = os.getenv("FOXPILOT_AUTH_MODE", "").lower()
    production = os.getenv("FOXPILOT_ENV", "local").lower() == "production"
    expected = os.getenv("FOXPILOT_API_TOKEN")

    if not mode:
        mode = "token" if expected else "local"
    if production and mode in {"", "local"}:
        raise HTTPException(
            status_code=503,
            detail="FOXPILOT_AUTH_MODE=native or token is required in production",
        )

    if mode == "local":
        return AuthContext(user_id="local-user", email="local@foxpilot.local")
    if mode == "native":
        return current_native_user(request)
    if mode != "token":
        raise HTTPException(status_code=503, detail=f"Unsupported auth mode: {mode}")
    if not expected:
        raise HTTPException(
            status_code=503,
            detail="FOXPILOT_API_TOKEN is required in token mode",
        )

    authorization = request.headers.get("authorization", "")
    scheme, _, provided = authorization.partition(" ")
    if scheme.lower() != "bearer" or not provided or not hmac.compare_digest(provided, expected):
        raise _unauthorized()
    return AuthContext(
        user_id=os.getenv("FOXPILOT_TOKEN_USER_ID", "token-user"),
        email=None,
    )
