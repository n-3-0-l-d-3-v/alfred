"""Streak bookkeeping (Duolingo mechanics): consecutive active days, with a
small number of freezes that cover a single missed day."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy.orm import Session as DbSession

from ..config import get_settings
from ..models import Streak


def get_or_create(db: DbSession, user_id: int) -> Streak:
    s = db.get(Streak, user_id)
    if s is None:
        s = Streak(user_id=user_id, freezes_left=get_settings().streak_freezes_default)
        db.add(s)
        db.flush()
    return s


def touch(db: DbSession, user_id: int, today: date | None = None) -> Streak:
    """Register activity for `today`. Idempotent within a day."""
    today = today or date.today()
    s = get_or_create(db, user_id)

    if s.last_active_date == today:
        return s  # already counted today

    if s.last_active_date is None:
        s.current = 1
    else:
        gap = (today - s.last_active_date).days
        if gap == 1:
            s.current += 1
        elif gap == 2 and s.freezes_left > 0:
            # one missed day, covered by a freeze — streak survives
            s.freezes_left -= 1
            s.current += 1
        else:
            s.current = 1  # broken

    s.longest = max(s.longest, s.current)
    s.last_active_date = today
    return s
