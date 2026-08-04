"""Daily caps. This is the mechanism that makes a free tier survivable: a user
cannot exceed `cap` events of a given source per day, so worst-case spend is
bounded and known in advance.

`source` is "card" (free DB reads, generous cap) or "llm" (paid model calls,
tight cap). Day boundaries are server-local for the dev slice; per-user timezone
handling is a Phase 3 refinement.
"""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from ..models import HintEvent


def used_today(db: DbSession, user_id: int, source: str) -> int:
    start = datetime.combine(datetime.now().date(), time.min)
    stmt = select(func.count()).select_from(HintEvent).where(
        HintEvent.user_id == user_id,
        HintEvent.source == source,
        HintEvent.at >= start,
    )
    return int(db.execute(stmt).scalar_one())


def remaining(db: DbSession, user_id: int, source: str, cap: int) -> int:
    """How many `source` events this user may still trigger today (never < 0)."""
    return max(0, cap - used_today(db, user_id, source))
