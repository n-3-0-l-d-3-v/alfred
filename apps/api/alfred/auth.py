"""Authentication: GitHub OAuth -> signed JWT.

Replaces the `Bearer llt_<user_id>` dev stub, which accepted any integer as
proof of identity and so let anyone read or mutate any account by counting.

Shape of the flow (the extension drives the browser half):

    extension  chrome.identity.launchWebAuthFlow(github authorize URL)
       -> GitHub redirects back with ?code=...
    extension  POST /auth/github {code}
       -> server exchanges code + client_secret for a GitHub token
       -> server reads the GitHub profile, upserts a User
       -> server returns OUR jwt, which is what every other endpoint accepts

The client secret only ever exists on the server; the extension holds nothing
but the resulting JWT. GitHub's access token is used once, server-side, and
deliberately not stored — we need identity, not ongoing API access.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import httpx
import jwt
from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .config import Settings, get_settings
from .db import get_db
from .models import User, utcnow

log = logging.getLogger("alfred.auth")

GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

_ALGORITHM = "HS256"


class AuthError(Exception):
    """Anything that should surface to the client as a 401/503 auth failure."""


# --- token minting / verification -------------------------------------------


# RFC 7518 §3.2: an HMAC-SHA256 key should be at least as long as the digest.
# A short secret is brute-forceable offline, and forging one token forges every
# account, so this is checked rather than warned about.
MIN_SECRET_BYTES = 32


def _secret(settings: Settings) -> str:
    if not settings.jwt_secret:
        # Failing closed matters more here than convenience: a default secret
        # would let anyone who reads this file mint tokens for any account.
        raise AuthError("ALFRED_JWT_SECRET is not configured")
    if len(settings.jwt_secret.encode()) < MIN_SECRET_BYTES:
        raise AuthError(
            f"ALFRED_JWT_SECRET must be at least {MIN_SECRET_BYTES} bytes "
            "(generate one with: python -c \"import secrets; print(secrets.token_urlsafe(32))\")"
        )
    return settings.jwt_secret


def issue_token(user: User, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    now = utcnow()
    payload = {
        "sub": str(user.id),
        "handle": user.handle,
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_ttl_days),
    }
    return jwt.encode(payload, _secret(settings), algorithm=_ALGORITHM)


def decode_token(token: str, settings: Settings | None = None) -> int:
    """Return the user id carried by a valid token, or raise AuthError."""
    settings = settings or get_settings()
    try:
        claims = jwt.decode(token, _secret(settings), algorithms=[_ALGORITHM])
        return int(claims["sub"])
    except jwt.ExpiredSignatureError:
        raise AuthError("session expired — sign in again")
    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise AuthError("invalid token")


# --- GitHub exchange ---------------------------------------------------------


async def exchange_github_code(code: str, redirect_uri: str | None, settings: Settings) -> dict:
    """Trade an OAuth code for a GitHub profile. Never returns the access token."""
    if not settings.github_oauth_configured:
        raise AuthError("GitHub sign-in isn't configured on this server")

    async with httpx.AsyncClient(timeout=10) as http:
        token_res = await http.post(
            GITHUB_TOKEN_URL,
            headers={"Accept": "application/json"},
            data={
                "client_id": settings.github_client_id,
                "client_secret": settings.github_client_secret,
                "code": code,
                **({"redirect_uri": redirect_uri} if redirect_uri else {}),
            },
        )
        token_body = token_res.json()
        access = token_body.get("access_token")
        if not access:
            # GitHub reports failures with HTTP 200 and an `error` field, so the
            # status code alone is not a usable success signal here.
            raise AuthError(f"GitHub rejected the sign-in ({token_body.get('error', 'no access_token')})")

        headers = {"Authorization": f"Bearer {access}", "Accept": "application/vnd.github+json"}
        profile = (await http.get(GITHUB_USER_URL, headers=headers)).json()

        email = profile.get("email")
        if not email:
            # Users with a private email get null on /user; the verified primary
            # from /user/emails is the reliable source.
            emails = (await http.get(GITHUB_EMAILS_URL, headers=headers)).json()
            if isinstance(emails, list):
                email = next(
                    (e["email"] for e in emails if e.get("primary") and e.get("verified")),
                    next((e["email"] for e in emails if e.get("verified")), None),
                )

    gh_id = profile.get("id")
    if not gh_id:
        raise AuthError("couldn't read a GitHub profile")

    login = profile.get("login")
    return {
        "github_id": str(gh_id),
        "handle": login,
        "email": email or f"{gh_id}+{login}@users.noreply.github.com",
        "avatar_url": profile.get("avatar_url"),
    }


def upsert_github_user(db: DbSession, profile: dict) -> User:
    """Find or create the account for a GitHub profile.

    Matched on `github_id` first, then email — so an account created by an
    earlier dev-login with the same address is adopted rather than colliding
    with the unique email constraint.
    """
    user = db.scalar(select(User).where(User.github_id == profile["github_id"]))
    if user is None:
        user = db.scalar(select(User).where(User.email == profile["email"]))
    if user is None:
        user = User(email=profile["email"])
        db.add(user)

    user.github_id = profile["github_id"]
    user.handle = user.handle or profile["handle"]
    user.avatar_url = profile["avatar_url"]
    db.commit()
    return user


# --- request dependency ------------------------------------------------------


def current_user(
    authorization: str | None = Header(default=None),
    db: DbSession = Depends(get_db),
) -> User:
    settings = get_settings()

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()

    if token.startswith("llt_"):
        # Local-development bypass. Off unless explicitly enabled, because it
        # authenticates nothing — the token *is* the user id.
        if not settings.dev_auth_enabled:
            raise HTTPException(401, "dev tokens are disabled on this server")
        try:
            user_id = int(token.removeprefix("llt_"))
        except ValueError:
            raise HTTPException(401, "bad dev token")
    else:
        try:
            user_id = decode_token(token, settings)
        except AuthError as e:
            raise HTTPException(401, str(e))

    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "unknown user")
    return user
