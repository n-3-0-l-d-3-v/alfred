from datetime import date, timedelta

import pytest

from leetlearn.gamification import budget, progress, streaks
from leetlearn.mentor.service import BudgetError
from leetlearn.models import Session


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
