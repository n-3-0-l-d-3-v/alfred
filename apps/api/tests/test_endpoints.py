"""HTTP-level coverage for the endpoints the other suites only reach indirectly.

Service-layer tests prove the logic; these prove the route exists, is wired to
that logic, enforces auth, and returns the shape the panel actually reads. A
route can be broken in all four of those ways while every unit test passes.
"""

from __future__ import annotations

from alfred.models import CardFeedback


def _auth(user):
    return {"Authorization": f"Bearer llt_{user.id}"}


# --- health ------------------------------------------------------------------


def test_health_reports_what_the_panel_branches_on(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()

    assert body["ok"] is True
    assert body["cards"] >= 15
    assert body["llm"] in {"online", "offline"}
    assert "python" in body["languages"]
    # The panel renders sign-in buttons from these, so a rename here silently
    # produces a screen with no way to sign in.
    assert set(body["auth"]) >= {"github", "dev"}


def test_health_needs_no_token(client):
    assert client.get("/health").status_code == 200


def test_health_reports_ecosystem_kpis(client):
    """Fields an external orchestrator (agent.yaml's health_check_command, or
    the MCP server) reads that the panel does not: version, DB connectivity,
    whether the optional LLM path is configured, and today's usage vs caps.
    """
    body = client.get("/health").json()

    assert body["version"]
    assert body["db"] == {"connected": True, "error": None}
    assert body["llm_configured"] is False  # no ALFRED_ANTHROPIC_API_KEY in tests
    assert set(body["usage_today"]) == {"card", "llm", "llm_review"}
    assert body["usage_today"]["card"]["cap_per_user"] == 40
    assert body["usage_today"]["llm"]["cap_per_user"] == 25
    assert "vault" in body and "configured" in body["vault"]


# --- auth --------------------------------------------------------------------


def test_dev_login_creates_a_user_and_returns_a_token(client):
    r = client.post("/auth/dev-login", json={"email": "new@example.com", "handle": "new"})
    assert r.status_code == 200
    assert r.json()["token"].startswith("llt_")


def test_dev_login_is_idempotent_for_one_email(client):
    first = client.post("/auth/dev-login", json={"email": "same@example.com"}).json()
    second = client.post("/auth/dev-login", json={"email": "same@example.com"}).json()
    assert first["user_id"] == second["user_id"]


def test_github_login_rejects_a_code_when_oauth_is_not_configured(client):
    """The test server has no GitHub credentials, so this must fail cleanly
    rather than 500 on a missing client secret."""
    r = client.post("/auth/github", json={"code": "abc123"})
    assert r.status_code == 401
    assert "configured" in r.json()["detail"].lower()


# --- analyze -----------------------------------------------------------------


def test_analyze_returns_signals_for_real_code(client, user):
    code = "def f(nums):\n    for x in nums:\n        for y in nums:\n            pass"
    r = client.post("/analyze", json={"language": "python", "code": code}, headers=_auth(user))
    assert r.status_code == 200
    body = r.json()
    assert body["parsed"] is True
    assert body["max_loop_depth"] == 2
    assert body["estimated_time_complexity"] == "O(n^2)"


def test_analyze_reports_a_syntax_error_rather_than_raising(client, user):
    r = client.post("/analyze", json={"language": "python", "code": "def broken(:"}, headers=_auth(user))
    assert r.status_code == 200
    assert r.json()["parsed"] is False
    assert r.json()["error"]


def test_analyze_requires_auth(client):
    assert client.post("/analyze", json={"language": "python", "code": "x = 1"}).status_code == 401


# --- personas ----------------------------------------------------------------


def test_personas_lists_every_voice_with_a_blurb(client):
    r = client.get("/personas")
    assert r.status_code == 200
    personas = r.json()["personas"]
    keys = {p["key"] for p in personas}
    assert {"mentor", "roast", "interviewer", "pragmatist", "professor", "deadpan"} <= keys
    for p in personas:
        assert p["label"] and p["blurb"]


# --- feedback ----------------------------------------------------------------


def test_feedback_is_recorded_for_the_review_queue(client, db, user):
    r = client.post(
        "/feedback",
        json={"slug": "two-sum", "level": 2, "reason": "unclear", "note": "didn't land"},
        headers=_auth(user),
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    row = db.query(CardFeedback).one()
    assert (row.slug, row.level, row.reason) == ("two-sum", 2, "unclear")


def test_feedback_requires_auth(client):
    assert client.post("/feedback", json={"slug": "two-sum"}).status_code == 401


# --- progress ----------------------------------------------------------------


def test_progress_returns_the_panel_stats_for_a_new_user(client, user):
    r = client.get("/progress", headers=_auth(user))
    assert r.status_code == 200
    body = r.json()
    assert body["xp_total"] == 0
    assert body["streak_current"] == 0
    # These drive the "hints left today" line, so they must be present and
    # positive before any hint has been spent.
    assert body["card_hints_left_today"] > 0
    assert body["llm_calls_left_today"] > 0


def test_progress_requires_auth(client):
    assert client.get("/progress").status_code == 401


# --- vault write-progress (end-to-end through the verdict endpoint) ----------


def test_accepted_verdict_writes_a_vault_progress_note_when_vault_path_is_set(client, user, tmp_path, monkeypatch):
    import alfred.main as main_mod

    monkeypatch.setattr(main_mod.settings, "vault_path", str(tmp_path))

    sid = client.post("/sessions", json={"slug": "two-sum"}, headers=_auth(user)).json()["session_id"]
    r = client.post(f"/sessions/{sid}/verdict", json={"verdict": "Accepted"}, headers=_auth(user))
    assert r.status_code == 200

    written = list((tmp_path / "agents" / "Alfred").glob("*.md"))
    assert len(written) == 1
    text = written[0].read_text(encoding="utf-8")
    assert "agent: Alfred" in text
    assert "pattern_archetype:" in text


def test_accepted_verdict_writes_nothing_when_vault_path_is_unset(client, user):
    import alfred.main as main_mod

    assert main_mod.settings.vault_path is None  # default in the test environment

    sid = client.post("/sessions", json={"slug": "two-sum"}, headers=_auth(user)).json()["session_id"]
    r = client.post(f"/sessions/{sid}/verdict", json={"verdict": "Accepted"}, headers=_auth(user))
    assert r.status_code == 200
    assert r.json()["accepted"] is True
