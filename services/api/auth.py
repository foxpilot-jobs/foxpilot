"""Small deployment guard for the local API and pre-OIDC hosted stage."""

from __future__ import annotations

import hmac
import os

from fastapi import HTTPException, Request


def require_api_access(request: Request) -> None:
    """Require a bearer token when configured or when running in production."""
    expected = os.getenv("FOXPILOT_API_TOKEN")
    production = os.getenv("FOXPILOT_ENV", "local").lower() == "production"
    if not expected:
        if production:
            raise HTTPException(
                status_code=503,
                detail="FOXPILOT_API_TOKEN is required in production",
            )
        return

    authorization = request.headers.get("authorization", "")
    scheme, _, provided = authorization.partition(" ")
    if scheme.lower() != "bearer" or not provided or not hmac.compare_digest(provided, expected):
        raise HTTPException(
            status_code=401,
            detail="A valid bearer token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )
