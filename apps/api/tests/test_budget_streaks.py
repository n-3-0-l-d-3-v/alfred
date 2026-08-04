from datetime import date, datetime, timedelta, timezone

import pytest

from leetlearn.gamification import budget, progress, streaks
from leetlearn.mentor.service import BudgetError
from leetlearn.models import HintEvent, Session


def _solved_session(db, user, slug="two-sum"):
    s = Session(user_id=user.id, slug=slug, language="python")
    db.add(s)
    db.commit()
    return s


def test_card_hint_cap_enforced(db, user, service, monkeypatch):
    # Tighten the cap to 3 for the test.
    monkeypatch.setattr(service, "_settings_card_cap", lambda: 3)
    s = _solved_session(db, user)
    for _ in range(3):
        service.get_hint(db, user, s, 1)
    assert budget.remaining(db, user.id, "card", 3) == 0
    with pytest.raises(BudgetError):
        service.get_hint(db, user, s, 1)


def test_hint_events_are_stamped_in_utc(db, user):
    """Half one of the cost fence: rows are written on the UTC clock.

    This assertion is timezone-independent — it fails on *any* machine if the
    column default ever goes back to a local-time clock, rather than only on
    machines whose offset happens to expose it.
    """
    db.add(HintEvent(user_id=user.id, session_id=1, level=1, source="card", cost=0))
    db.commit()
    ev = db.query(HintEvent).one()
    drift = abs(ev.at - datetime.now(timezone.utc).replace(tzinfo=None))
    assert drift < timedelta(minutes=1), f"hint_events.at is not on the UTC clock (drift {drift})"


def test_budget_day_boundary_is_utc_not_local(db, user, monkeypatch):
    """Half two: the cap counts against a UTC midnight.

    Pinned at 22:30 UTC — a moment that is already *tomorrow* in any timezone
    ahead of UTC+02:00. Under the old local-midnight boundary an event written
    seconds ago sorted as "yesterday" and the cap counted zero, so the daily
    limit stopped applying for the first offset-hours of every local day.
    """
    now = datetime(2026, 8, 3, 22, 30)
    monkeypatch.setattr(budget, "utcnow", lambda: now)

    db.add(HintEvent(user_id=user.id, session_id=1, level=1, source="card", cost=0, at=now - timedelta(minutes=1)))
    db.add(HintEvent(user_id=user.id, session_id=1, level=1, source="card", cost=0, at=now - timedelta(hours=25)))
    db.commit()

    assert budget.used_today(db, user.id, "card") == 1
    assert budget.remaining(db, user.id, "card", 3) == 2


def test_clean_solve_awards_more_than_hinted(db, user, service):
    clean = _solved_session(db, user, "two-sum")
    r1 = progress.on_verdict(db, user, clean, "Accepted")
    assert r1["xp_awarded"] == 50
    assert r1["clean"] is True

    hinted = _solved_session(db, user, "valid-parentheses")
    service.get_hint(db, user, hinted, 1)
    service.get_hint(db, user, hinted, 2)
    r2 = progress.on_verdict(db, user, hinted, "Accepted")
    assert r2["xp_awarded"] == 30  # 50 - 2*10
    assert r2["clean"] is False


def test_resolve_is_idempotent(db, user):
    s = _solved_session(db, user)
    first = progress.on_verdict(db, user, s, "Accepted")
    second = progress.on_verdict(db, user, s, "Accepted")
    assert first["xp_awarded"] == 50
    assert second["xp_awarded"] == 0
    assert second.get("already_solved")


def test_streak_increments_on_consecutive_days(db, user):
    today = date(2026, 7, 20)
    streaks.touch(db, user.id, today=today)
    streaks.touch(db, user.id, today=today + timedelta(days=1))
    s = streaks.touch(db, user.id, today=today + timedelta(days=2))
    assert s.current == 3
    assert s.longest == 3


def test_streak_freeze_covers_one_missed_day(db, user):
    today = date(2026, 7, 20)
    streaks.touch(db, user.id, today=today)
    # skip a day -> gap of 2 -> freeze covers it
    s = streaks.touch(db, user.id, today=today + timedelta(days=2))
    assert s.current == 2
    assert s.freezes_left == 1


def test_streak_breaks_after_long_gap(db, user):
    today = date(2026, 7, 20)
    streaks.touch(db, user.id, today=today)
    s = streaks.touch(db, user.id, today=today + timedelta(days=5))
    assert s.current == 1


def test_offline_review_reads_signals(db, user, service):
    s = _solved_session(db, user, "two-sum")
    progress.on_verdict(db, user, s, "Accepted")
    # A brute-force O(n^2) solution to an O(n)-target problem should be flagged.
    code = "for i in range(len(nums)):\n    for j in range(i+1, len(nums)):\n        if nums[i]+nums[j]==target:\n            return [i,j]"
    r = service.review(s, code)
    assert r.complexity_time == "O(n^2)"
    assert r.target_time == "O(n)"
    assert r.verdict == "works — can be sharper"
    # the robustness lens must name the scale at which this actually breaks
    robustness = next(sec for sec in r.sections if sec.lens == "robustness")
    assert any("TLE" in f for f in robustness.findings)
