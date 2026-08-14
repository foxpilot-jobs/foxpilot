"""Small deployment guard for local API use and pre-native-auth staging."""

from __future__ import annotations

import hmac
import os
from dataclasses import dataclass

from fastapi import HTTPException, Request


@dataclass(frozen=True)
class AuthContext:
    """Authenticated identity passed from the API boundary to application code."""

    user_id: str
    email: str | None = None


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
    if production and mode == "local":
        raise HTTPException(
            status_code=503,
            detail="FOXPILOT_AUTH_MODE=token is required until native auth is enabled",
        )

    if mode == "local":
        return AuthContext(user_id="local-user", email="local@foxpilot.local")
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
