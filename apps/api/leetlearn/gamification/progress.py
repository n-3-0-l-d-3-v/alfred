"""What happens on a passing submission: flip the AC gate, award XP (clean
solves are worth more than hinted ones), and advance the streak."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from ..models import Session, User, XpEvent, utcnow
from . import streaks

CLEAN_SOLVE_XP = 50
HINT_PENALTY = 10
MIN_SOLVE_XP = 10

# XP kinds that represent "you finished this problem", as opposed to future
# non-solve awards (daily goal, streak milestones) which may repeat per slug.
SOLVE_KINDS = ("solve_clean", "solve_hinted")


def already_scored(db: DbSession, user_id: int, slug: str) -> bool:
    """Has this user ever been awarded solve XP for this problem?

    The AC gate itself is per-session, which is correct — each attempt at a
    problem earns its own teaching surface. Scoring is not: a session row costs
    nothing to create, so without a per-(user, slug) check a learner could
    re-collect the clean-solve bonus indefinitely by reopening the panel on a
    problem they already finished.
    """
    stmt = select(XpEvent.id).where(
        XpEvent.user_id == user_id,
        XpEvent.slug == slug,
        XpEvent.kind.in_(SOLVE_KINDS),
    ).limit(1)
    return db.execute(stmt).first() is not None


def on_verdict(db: DbSession, user: User, session: Session, verdict: str) -> dict:
    """Process a submission verdict. Returns a summary for the client.

    Only the first Accepted verdict for a session flips `solved_at`, and solve
    XP is awarded at most once per (user, problem) across all sessions.
    """
    accepted = verdict.strip().lower() in {"accepted", "ac", "pass", "passed"}

    if not accepted:
        return {"solved": session.solved, "accepted": False, "xp_awarded": 0}

    if session.solved:
        return {"solved": True, "accepted": True, "xp_awarded": 0, "already_solved": True}

    session.solved_at = utcnow()
    clean = session.hints_used == 0

    # Re-solving a problem still unlocks the post-AC surface and still counts as
    # activity for the streak — it just doesn't pay out again.
    repeat = already_scored(db, user.id, session.slug)
    xp = 0 if repeat else (
        CLEAN_SOLVE_XP if clean
        else max(MIN_SOLVE_XP, CLEAN_SOLVE_XP - HINT_PENALTY * session.hints_used)
    )

    if xp:
        db.add(XpEvent(
            user_id=user.id,
            kind="solve_clean" if clean else "solve_hinted",
            amount=xp,
            slug=session.slug,
        ))
    s = streaks.touch(db, user.id)
    db.commit()

    return {
        "solved": True,
        "accepted": True,
        "clean": clean,
        "repeat_solve": repeat,
        "hints_used": session.hints_used,
        "xp_awarded": xp,
        "streak_current": s.current,
        "streak_longest": s.longest,
    }


def total_xp(db: DbSession, user_id: int) -> int:
    stmt = select(func.coalesce(func.sum(XpEvent.amount), 0)).where(XpEvent.user_id == user_id)
    return int(db.execute(stmt).scalar_one())
