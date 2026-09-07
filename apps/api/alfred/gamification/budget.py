"""Daily caps. This is the mechanism that makes a free tier survivable: a user
cannot exceed `cap` events of a given source per day, so worst-case spend is
bounded and known in advance.

`source` is "card" (free DB reads, generous cap) or "llm" (paid model calls,
tight cap).

Day boundaries are **UTC**, matching `models.utcnow()` — the clock every
timestamp in the schema is written with. Comparing UTC-stamped rows against a
server-*local* midnight is what previously let the cap read zero for the first
UTC-offset hours of each day. Per-user timezone boundaries are a Phase 3
refinement; until then the two clocks must at least be the same clock.
"""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from ..models import HintEvent, utcnow


def used_today(db: DbSession, user_id: int, source: str) -> int:
    start = datetime.combine(utcnow().date(), time.min)
    stmt = select(func.count()).select_from(HintEvent).where(
        HintEvent.user_id == user_id,
        HintEvent.source == source,
        HintEvent.at >= start,
    )
    return int(db.execute(stmt).scalar_one())


def remaining(db: DbSession, user_id: int, source: str, cap: int) -> int:
    """How many `source` events this user may still trigger today (never < 0)."""
    return max(0, cap - used_today(db, user_id, source))
