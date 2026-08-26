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


def test_the_same_slug_on_two_platforms_gets_two_sessions(client, db, user):
    """Problem ids are only unique within a site.

    Without the platform in the key, opening "two-sum" on another judge would
    resume the LeetCode session — inheriting its hint count and its solved
    state, so a problem you had never seen would already be unlocked.
    """
    a = client.post("/sessions", json={"slug": "two-sum", "platform": "leetcode"}, headers=_auth(user)).json()
    b = client.post("/sessions", json={"slug": "two-sum", "platform": "hackerrank"}, headers=_auth(user)).json()

    assert a["session_id"] != b["session_id"]
    assert a["platform"] == "leetcode"
    assert b["platform"] == "hackerrank"
    assert db.query(Session).filter(Session.slug == "two-sum").count() == 2


def test_platform_defaults_to_leetcode_for_older_clients(client, user):
    r = client.post("/sessions", json={"slug": "two-sum"}, headers=_auth(user)).json()
    assert r["platform"] == "leetcode"


def test_an_unauthored_problem_opens_a_session_instead_of_404ing(client, db, user):
    """The knowledge base covers a few dozen problems; the site has thousands.

    Refusing the rest was the largest hole in the product — a learner on any
    problem nobody had hand-authored got a dead panel. A card is now generated
    from the pattern the problem looks like, so the session opens.
    """
    r = client.post(
        "/sessions",
        json={
            "slug": "some-unauthored-problem",
            "title": "999. Some Unauthored Problem",
            "difficulty": "Medium",
            "topics": ["array", "hash-table"],
            "statement": "return indices of the two numbers such that they add up to target",
        },
        headers=_auth(user),
    )
    assert r.status_code == 200, r.text
    assert db.query(Session).count() == 1


def test_a_generated_card_is_marked_unverified(client, user):
    """Generated content must never be presented as checked. The panel badges
    this, and the badge is what makes the report link make sense."""
    s = client.post(
        "/sessions",
        json={"slug": "another-unauthored-problem", "title": "1000. Another",
              "difficulty": "Easy", "topics": ["array"]},
        headers=_auth(user),
    ).json()
    card = client.get(f"/sessions/{s['session_id']}/card", headers=_auth(user)).json()
    assert card["verified"] is False


def test_an_authored_card_is_never_replaced_by_a_generated_one(client, user):
    """Hand-written cards have been checked line by line; a generalisation must
    not displace a specialist's version of a problem just because tags arrived."""
    s = client.post(
        "/sessions",
        json={"slug": "two-sum", "title": "wrong title", "topics": ["tree", "graph"]},
        headers=_auth(user),
    ).json()
    card = client.get(f"/sessions/{s['session_id']}/card", headers=_auth(user)).json()
    assert card["verified"] is True
    assert card["title"] != "wrong title"
