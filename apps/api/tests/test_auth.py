"""Auth: JWT minting/verification, the GitHub upsert, and the dev-bypass fence.

The thing under test is mostly negative space — what a caller *cannot* do with a
token they weren't given.
"""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest

from leetlearn.auth import AuthError, decode_token, issue_token, upsert_github_user
from leetlearn.config import Settings
from leetlearn.models import User, utcnow

SETTINGS = Settings(jwt_secret="unit-test-secret-that-is-long-enough-for-hs256", dev_auth_enabled=False)


def _profile(**over) -> dict:
    return {
        "github_id": "12345",
        "handle": "neil",
        "email": "neil@example.com",
        "avatar_url": "https://avatars.example/neil.png",
        **over,
    }


# --- token round-trip --------------------------------------------------------


def test_token_round_trips_to_the_same_user(db, user):
    assert decode_token(issue_token(user, SETTINGS), SETTINGS) == user.id


def test_token_signed_with_another_secret_is_rejected(db, user):
    forged = jwt.encode({"sub": str(user.id)}, "attacker-secret-that-is-also-long-enough-for-hs256", algorithm="HS256")
    with pytest.raises(AuthError):
        decode_token(forged, SETTINGS)


def test_expired_token_is_rejected(db, user):
    stale = jwt.encode(
        {"sub": str(user.id), "exp": utcnow() - timedelta(days=1)},
        SETTINGS.jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(AuthError, match="expired"):
        decode_token(stale, SETTINGS)


def test_unsigned_none_algorithm_token_is_rejected(db, user):
    """`alg: none` is the classic JWT bypass — the decoder must not honour it."""
    unsigned = jwt.encode({"sub": str(user.id)}, key="", algorithm="none")
    with pytest.raises(AuthError):
        decode_token(unsigned, SETTINGS)


def test_missing_secret_fails_closed():
    unconfigured = Settings(jwt_secret=None)
    with pytest.raises(AuthError, match="JWT_SECRET"):
        decode_token("anything", unconfigured)


# --- GitHub upsert -----------------------------------------------------------


def test_github_login_creates_then_reuses_one_account(db):
    first = upsert_github_user(db, _profile())
    second = upsert_github_user(db, _profile(handle="renamed", email="new@example.com"))
    assert first.id == second.id
    assert db.query(User).count() == 1


def test_github_adopts_an_account_created_by_email(db):
    """A pre-existing dev-login account with the same address must be adopted.

    Otherwise the unique email constraint turns a first GitHub sign-in into a
    500 for anyone who tried the app locally first.
    """
    existing = User(email="neil@example.com", handle="local-dev")
    db.add(existing)
    db.commit()

    linked = upsert_github_user(db, _profile())
    assert linked.id == existing.id
    assert linked.github_id == "12345"
    assert db.query(User).count() == 1


def test_identity_follows_github_id_not_email(db):
    """Changing your GitHub email must not fork your account and lose your XP."""
    original = upsert_github_user(db, _profile())
    renamed = upsert_github_user(db, _profile(email="moved@example.com"))
    assert renamed.id == original.id
    assert db.query(User).count() == 1


# --- the dev bypass ----------------------------------------------------------


def test_dev_token_is_refused_when_dev_auth_is_disabled(client, user, monkeypatch):
    """The impersonation hole: `llt_<id>` names a user without proving anything.

    With the bypass off, presenting one must fail even though the user exists.
    """
    from leetlearn import auth

    monkeypatch.setattr(auth, "get_settings", lambda: SETTINGS)
    r = client.get("/me", headers={"Authorization": f"Bearer llt_{user.id}"})
    assert r.status_code == 401
    assert "disabled" in r.json()["detail"]


def test_garbage_bearer_token_is_refused(client, user):
    r = client.get("/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert r.status_code == 401


def test_missing_authorization_header_is_refused(client):
    assert client.get("/me").status_code == 401


def test_jwt_authenticates_against_a_live_endpoint(client, db, user):
    from leetlearn import auth

    token = issue_token(user, SETTINGS)
    # The dependency reads settings at request time, so point it at the same
    # secret the token was minted with.
    original = auth.get_settings
    auth.get_settings = lambda: SETTINGS
    try:
        r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    finally:
        auth.get_settings = original

    assert r.status_code == 200
    assert r.json()["id"] == user.id
