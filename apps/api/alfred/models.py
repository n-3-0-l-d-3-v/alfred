"""SQLAlchemy models — the subset of the PLAN.md §4 schema needed for the
vertical slice: auth, sessions, the AC gate, hint budgets, streaks, XP.

Written in a Postgres-portable way (SQLAlchemy 2.0 typed style) even though
local dev uses SQLite. `mastery`/`problem_cards` tables land in Phase 3 — for
now cards live as JSON files loaded into memory (see `mentor.cards`).
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def utcnow() -> datetime:
    """Naive UTC — the single time source for every timestamp in the schema.

    Defaults are applied in Python, not via ``server_default=func.now()``. The
    server_default form delegates to the database clock, which is UTC on SQLite
    and Postgres, while the rest of the app reasoned in *local* time. In any
    timezone ahead of UTC that made a freshly written row land on "yesterday",
    so `budget.used_today` counted zero and the daily caps — the entire cost
    fence — silently stopped applying for the first UTC-offset hours of each
    local day. One clock, everywhere, is the fix.

    Naive-but-UTC rather than aware: SQLAlchemy's SQLite DATETIME type returns
    naive datetimes regardless of what was stored, so aware values would come
    back naive and every comparison would raise. Postgres migration keeps this
    working unchanged.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    handle: Mapped[str | None] = mapped_column(String(64), default=None)
    # GitHub's numeric user id, as a string. This — not the email or login, both
    # of which a user can change — is the stable identity we match accounts on.
    github_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, default=None)
    avatar_url: Mapped[str | None] = mapped_column(String(512), default=None)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    skill_level: Mapped[str] = mapped_column(String(16), default="beginner")
    tone: Mapped[str] = mapped_column(String(16), default="encourage")  # encourage | roast

    sessions: Mapped[list["Session"]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    # Which site this problem came from. Problem ids are only unique *within* a
    # platform — HackerRank and LeetCode both have a "two-sum" — so without this
    # a session on one would resume a session from the other, carrying its hint
    # count and solved state across. Cheap to add now, a data migration later.
    platform: Mapped[str] = mapped_column(String(32), default="leetcode", index=True)
    slug: Mapped[str] = mapped_column(String(128), index=True)
    language: Mapped[str] = mapped_column(String(24), default="python")
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
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
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class XpEvent(Base):
    __tablename__ = "xp_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    kind: Mapped[str] = mapped_column(String(32))
    amount: Mapped[int] = mapped_column()
    # Which problem earned this. Solve XP is awarded once per (user, slug) —
    # sessions are cheap to create, so per-session idempotence alone would let a
    # learner re-collect the clean-solve bonus by reopening the panel.
    slug: Mapped[str | None] = mapped_column(String(128), index=True, default=None)
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


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
    at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)


class Streak(Base):
    __tablename__ = "streaks"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), primary_key=True)
    current: Mapped[int] = mapped_column(default=0)
    longest: Mapped[int] = mapped_column(default=0)
    last_active_date: Mapped[date | None] = mapped_column(Date, default=None)
    freezes_left: Mapped[int] = mapped_column(default=2)


class ProblemMeta(Base):
    """What a platform told us about a problem: title, difficulty, tags, statement.

    Stored per problem rather than per session, because it is a property of the
    problem and identical for every learner who opens it.

    It exists so a card can be rebuilt after a restart. Cards for problems
    nobody authored are generated from this metadata (see `mentor.synth`), and
    the metadata itself is read by the extension from the page. Without a
    durable copy, any request that isn't a fresh `POST /sessions` — a hint, a
    review, a reload hours later — would have to regenerate the card from the
    slug alone, silently dropping from the inferred pattern to the pattern-free
    fallback. The learner would see the same problem taught two different ways
    depending on how long the server had been up.
    """

    __tablename__ = "problem_meta"

    id: Mapped[int] = mapped_column(primary_key=True)
    platform: Mapped[str] = mapped_column(String(32), default="leetcode", index=True)
    slug: Mapped[str] = mapped_column(String(128), index=True)
    title: Mapped[str | None] = mapped_column(String(256), default=None)
    difficulty: Mapped[str | None] = mapped_column(String(16), default=None)
    # Comma-separated: a handful of short slugs, only ever read as a whole, and
    # a join table would buy nothing but a join.
    topics: Mapped[str | None] = mapped_column(String(512), default=None)
    # Truncated on write — inference reads keywords, and the tail of a long
    # statement is examples and constraints rather than the task.
    statement: Mapped[str | None] = mapped_column(Text, default=None)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (UniqueConstraint("platform", "slug", name="uq_problem_meta_platform_slug"),)

    @property
    def topic_list(self) -> list[str]:
        return [t for t in (self.topics or "").split(",") if t]
