"""Settings resolution, including the LEETLEARN_* -> ALFRED_* rename fallback.

The project was renamed from LeetLearn to Alfred and its env var prefix moved
from ``LEETLEARN_`` to ``ALFRED_``. Anyone with an existing ``.env`` from
before the rename should not have their deployment silently break, so
`Settings` still honors the old names when the new ones are absent.
"""

from __future__ import annotations

import warnings

from alfred.config import Settings


def test_new_prefix_is_read_normally(monkeypatch):
    monkeypatch.setenv("ALFRED_JWT_SECRET", "new-secret")
    monkeypatch.delenv("LEETLEARN_JWT_SECRET", raising=False)
    s = Settings(_env_file=None)
    assert s.jwt_secret == "new-secret"


def test_legacy_prefix_is_used_when_new_one_is_absent(monkeypatch):
    monkeypatch.delenv("ALFRED_JWT_SECRET", raising=False)
    monkeypatch.setenv("LEETLEARN_JWT_SECRET", "old-secret")
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        s = Settings(_env_file=None)
    assert s.jwt_secret == "old-secret"
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)
    assert any("LEETLEARN_JWT_SECRET" in str(w.message) for w in caught)


def test_new_prefix_wins_over_legacy_when_both_are_set(monkeypatch):
    monkeypatch.setenv("ALFRED_JWT_SECRET", "new-secret")
    monkeypatch.setenv("LEETLEARN_JWT_SECRET", "old-secret")
    s = Settings(_env_file=None)
    assert s.jwt_secret == "new-secret"


def test_explicit_none_kwarg_is_not_overridden_by_legacy_env(monkeypatch):
    # A caller that explicitly passes `jwt_secret=None` (as the auth tests do,
    # to exercise the fail-closed path) means it, even if a legacy
    # LEETLEARN_JWT_SECRET happens to be set in the environment.
    monkeypatch.setenv("LEETLEARN_JWT_SECRET", "old-secret")
    s = Settings(jwt_secret=None, _env_file=None)
    assert s.jwt_secret is None


def test_no_env_at_all_falls_back_to_field_default(monkeypatch):
    # Isolate from this repo's own apps/api/.env (which, for local dev, still
    # carries pre-rename LEETLEARN_* values) so the test reflects a genuinely
    # unconfigured environment rather than this checkout's.
    monkeypatch.setattr("alfred.config.dotenv_values", lambda *_a, **_k: {})
    monkeypatch.delenv("ALFRED_DEV_AUTH_ENABLED", raising=False)
    monkeypatch.delenv("LEETLEARN_DEV_AUTH_ENABLED", raising=False)
    s = Settings(_env_file=None)
    assert s.dev_auth_enabled is False
