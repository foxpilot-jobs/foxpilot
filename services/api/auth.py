"""Authentication adapters for local, staging, and hosted API deployments."""

from __future__ import annotations

import hmac
import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import jwt
from fastapi import HTTPException, Request


@dataclass(frozen=True)
class AuthContext:
    """Authenticated identity passed from the API boundary to application code."""

    user_id: str
    email: str | None = None
    claims: dict[str, Any] | None = None


def _unauthorized(detail: str = "A valid bearer token is required") -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _bearer_token(request: Request) -> str:
    authorization = request.headers.get("authorization", "")
    scheme, _, provided = authorization.partition(" ")
    if scheme.lower() != "bearer" or not provided:
        raise _unauthorized()
    return provided


@lru_cache(maxsize=1)
def _jwks_client(url: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(url)


def _oidc_context(token: str) -> AuthContext:
    issuer = os.getenv("FOXPILOT_JWT_ISSUER")
    audience = os.getenv("FOXPILOT_JWT_AUDIENCE")
    jwks_url = os.getenv("FOXPILOT_JWKS_URL")
    if not issuer or not audience or not jwks_url:
        raise HTTPException(
            status_code=503,
            detail=(
                "FOXPILOT_JWT_ISSUER, FOXPILOT_JWT_AUDIENCE, and "
                "FOXPILOT_JWKS_URL are required in oidc mode"
            ),
        )

    try:
        signing_key = _jwks_client(jwks_url).get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256", "RS384", "RS512", "ES256", "ES384", "ES512"],
            audience=audience,
            issuer=issuer,
            options={"require": ["exp", "iat", "sub"]},
        )
    except (jwt.InvalidTokenError, jwt.PyJWKClientError) as error:
        raise _unauthorized("The identity token is invalid or expired") from error

    user_id = str(claims["sub"])
    email = claims.get(os.getenv("FOXPILOT_JWT_EMAIL_CLAIM", "email"))
    return AuthContext(user_id=user_id, email=email, claims=claims)


def require_api_access(request: Request) -> AuthContext:
    """Return the authenticated identity for an API request.

    Local mode intentionally uses one explicit local identity. Hosted deployments
    must select OIDC mode; token mode remains available for staging and automation.
    """
    mode = os.getenv("FOXPILOT_AUTH_MODE", "").lower()
    production = os.getenv("FOXPILOT_ENV", "local").lower() == "production"
    expected = os.getenv("FOXPILOT_API_TOKEN")

    if not mode:
        mode = "token" if expected else "local"
    if production and mode == "local":
        raise HTTPException(
            status_code=503,
            detail="FOXPILOT_AUTH_MODE must be token or oidc in production",
        )

    if mode == "local":
        return AuthContext(user_id="local-user", email="local@foxpilot.local")

    token = _bearer_token(request)
    if mode == "token":
        if not expected:
            raise HTTPException(
                status_code=503,
                detail="FOXPILOT_API_TOKEN is required in token mode",
            )
        if not hmac.compare_digest(token, expected):
            raise _unauthorized()
        return AuthContext(
            user_id=os.getenv("FOXPILOT_TOKEN_USER_ID", "token-user"),
            email=None,
        )
    if mode == "oidc":
        return _oidc_context(token)
    raise HTTPException(status_code=503, detail=f"Unsupported auth mode: {mode}")
