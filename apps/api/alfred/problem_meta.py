"""Store and recall what a platform told us about a problem.

The extension reads a problem's title, difficulty, topic tags and statement from
the page. Those are the inputs archetype inference runs on, so they decide
whether a learner on an unauthored problem gets the right pattern taught or the
pattern-free fallback. They therefore have to outlive the request that carried
them: only `POST /sessions` sends them, while hints, reviews and interviews all
need the same card, potentially hours and one restart later.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .models import ProblemMeta

# Long enough to keep the worked examples, which sit after the task description
# and are parsed for concrete inputs (see `mentor.examples`). The original 2000
# was chosen when only keywords were read from this and would cut the examples
# off exactly on the problems whose descriptions are longest.
MAX_STATEMENT = 12000


def remember(
    db: DbSession,
    platform: str,
    slug: str,
    title: str | None = None,
    difficulty: str | None = None,
    topics=None,
    statement: str | None = None,
) -> ProblemMeta:
    """Upsert what we know about a problem, keeping the richer of old and new.

    Fields are merged rather than overwritten because the client's two readers
    differ in what they can see: the GraphQL path returns topic tags, the DOM
    fallback cannot. A learner whose first visit succeeded and whose second fell
    back to scraping must not lose the tags they already had — that would
    silently downgrade the teaching on a problem that was working.
    """
    row = db.scalar(
        select(ProblemMeta).where(ProblemMeta.platform == platform, ProblemMeta.slug == slug)
    )
    if row is None:
        row = ProblemMeta(platform=platform, slug=slug)
        db.add(row)

    joined = ",".join(t.strip().lower() for t in (topics or []) if t and t.strip())
    if title:
        row.title = title[:256]
    if difficulty:
        row.difficulty = difficulty[:16]
    if joined:
        row.topics = joined[:512]
    if statement:
        row.statement = statement[:MAX_STATEMENT]

    db.commit()
    return row


def lookup(db: DbSession, platform: str, slug: str) -> ProblemMeta | None:
    return db.scalar(
        select(ProblemMeta).where(ProblemMeta.platform == platform, ProblemMeta.slug == slug)
    )


def as_kwargs(meta: ProblemMeta | None) -> dict:
    """Shape a row for `CardStore.get_or_synthesize`. Empty dict when unknown."""
    if meta is None:
        return {}
    return {
        "title": meta.title,
        "difficulty": meta.difficulty,
        "topics": meta.topic_list,
        "statement": meta.statement,
    }
