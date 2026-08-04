"""What happens on a passing submission: flip the AC gate, award XP (clean
solves are worth more than hinted ones), and advance the streak."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from ..models import Session, User, XpEvent
from . import streaks

CLEAN_SOLVE_XP = 50
HINT_PENALTY = 10
MIN_SOLVE_XP = 10


def on_verdict(db: DbSession, user: User, session: Session, verdict: str) -> dict:
    """Process a submission verdict. Returns a summary for the client.

    Only the first Accepted verdict for a session flips `solved_at` and awards XP;
    re-submitting an already-solved problem is a no-op for scoring.
    """
    accepted = verdict.strip().lower() in {"accepted", "ac", "pass", "passed"}

    if not accepted:
        return {"solved": session.solved, "accepted": False, "xp_awarded": 0}

    if session.solved:
        return {"solved": True, "accepted": True, "xp_awarded": 0, "already_solved": True}

    session.solved_at = datetime.now()
    clean = session.hints_used == 0
    xp = CLEAN_SOLVE_XP if clean else max(MIN_SOLVE_XP, CLEAN_SOLVE_XP - HINT_PENALTY * session.hints_used)

    db.add(XpEvent(user_id=user.id, kind="solve_clean" if clean else "solve_hinted", amount=xp))
    s = streaks.touch(db, user.id)
    db.commit()

    return {
        "solved": True,
        "accepted": True,
        "clean": clean,
        "hints_used": session.hints_used,
        "xp_awarded": xp,
        "streak_current": s.current,
        "streak_longest": s.longest,
    }


def total_xp(db: DbSession, user_id: int) -> int:
    stmt = select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.user_id == user_id)
    return int(db.execute(stmt).scalar_one())
