"""SQLAlchemy models — the subset of the PLAN.md §4 schema needed for the
vertical slice: auth, sessions, the AC gate, hint budgets, streaks, XP.

Written in a Postgres-portable way (SQLAlchemy 2.0 typed style) even though
local dev uses SQLite. `mastery`/`problem_cards` tables land in Phase 3 — for
now cards live as JSON files loaded into memory (see `mentor.cards`).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    handle: Mapped[str | None] = mapped_column(String(64), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    skill_level: Mapped[str] = mapped_column(String(16), default="beginner")
    tone: Mapped[str] = mapped_column(String(16), default="encourage")  # encourage | roast

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    slug: Mapped[str] = mapped_column(String(128), index=True)
    language: Mapped[str] = mapped_column(String(24), default="python")
    started_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    # solved_at is the AC gate. NULL => pre-AC (Socratic only). Set => firehose open.
    solved_at: Mapped[datetime | None] = mapped_column(DateTime, default=None)
    hints_used: Mapped[int] = mapped_column(default=0)

    user: Mapped[User] = relationship(back_populates="sessions")

    @property
    def solved(self) -> bool:
        return self.solved_at is not None


class HintEvent(Base):
    __tablename__ = "hint_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("sessions.id"), index=True)
    level: Mapped[int] = mapped_column()
    # source drives the whole cost model: "card" = free DB read, "llm" = paid call.
    source: Mapped[str] = mapped_column(String(8))
    cost: Mapped[int] = mapped_column(default=0)  # hint-tokens spent
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class XpEvent(Base):
    __tablename__ = "xp_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column()
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class CardFeedback(Base):
    """A learner flagging a hint/card as bad. This is what makes auto-generated
    long-tail cards safe to ship: usage drives the review queue, not guesswork."""

    __tablename__ = "card_feedback"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    slug: Mapped[str] = mapped_column(String(128), index=True)
    level: Mapped[int | None] = mapped_column(default=None)  # which hint, if any
    reason: Mapped[str] = mapped_column(String(32))  # unclear | wrong | gives_away | other
    note: Mapped[str | None] = mapped_column(String(1000), default=None)
    at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), index=True)


class Streak(Base):
    __tablename__ = "streaks"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    current: Mapped[int] = mapped_column(default=0)
    longest: Mapped[int] = mapped_column(default=0)
    last_active_date: Mapped[date | None] = mapped_column(Date, default=None)
    freezes_left: Mapped[int] = mapped_column(default=2)
