"""Session lifecycle at the HTTP boundary.

The reuse rule lives in the endpoint, so it needs endpoint-level coverage: the
scoring guarantees in `test_budget_streaks` all assume that opening the panel
twice on one problem lands on *one* session row.
"""

from __future__ import annotations

from leetlearn.models import Session


def _auth(user):
    return {"Authorization": f"Bearer llt_{user.id}"}


def test_reopening_a_problem_resumes_the_same_session(client, db, user):
    first = client.post("/sessions", json={"slug": "two-sum", "language": "python"}, headers=_auth(user))
    second = client.post("/sessions", json={"slug": "two-sum", "language": "python"}, headers=_auth(user))

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["session_id"] == second.json()["session_id"]
    assert db.query(Session).filter(Session.slug == "two-sum").count() == 1


def test_resume_preserves_hint_count(client, db, user, service):
    sid = client.post("/sessions", json={"slug": "two-sum"}, headers=_auth(user)).json()["session_id"]
    s = db.get(Session, sid)
    service.get_hint(db, user, s, 1)
    service.get_hint(db, user, s, 2)

    again = client.post("/sessions", json={"slug": "two-sum"}, headers=_auth(user)).json()
    assert again["session_id"] == sid
    assert again["hints_used"] == 2
    assert again["resumed"] is True


def test_different_problems_get_different_sessions(client, user):
    a = client.post("/sessions", json={"slug": "two-sum"}, headers=_auth(user)).json()
    b = client.post("/sessions", json={"slug": "valid-parentheses"}, headers=_auth(user)).json()
    assert a["session_id"] != b["session_id"]


def test_switching_language_updates_the_existing_session(client, user):
    a = client.post("/sessions", json={"slug": "two-sum", "language": "python"}, headers=_auth(user)).json()
    b = client.post("/sessions", json={"slug": "two-sum", "language": "cpp"}, headers=_auth(user)).json()
    assert a["session_id"] == b["session_id"]
    assert b["language"] == "cpp"


def test_unknown_slug_is_rejected_before_a_session_is_created(client, db, user):
    r = client.post("/sessions", json={"slug": "no-such-problem"}, headers=_auth(user))
    assert r.status_code == 404
    assert db.query(Session).count() == 0
