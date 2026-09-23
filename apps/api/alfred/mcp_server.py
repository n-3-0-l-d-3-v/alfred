"""Alfred MCP server — exposes the core Socratic-mentor capabilities as MCP
tools over stdio, so a future orchestrator agent in this ecosystem can call
Alfred directly without going through the browser extension.

Follows the same shape as the sibling "Friday" agent's own MCP server
(mcp.server.mcpserver.MCPServer, one @server.tool per capability, plain-text
returns): a global `server`, tools registered as decorated functions, `main()`
runs it over stdio.

Register once:
    claude mcp add --transport stdio -s user alfred -- python -m alfred.mcp_server

CRITICAL: stdio transport uses stdout for the protocol itself. `_quiet()`
redirects stdout to stderr for the duration of a tool call so nothing Alfred's
internals print (there normally isn't anything, but the DB/migration layer
can) corrupts the stream.

Every tool operates against one local, non-interactive user (`_LOCAL_USER_EMAIL`)
on a dedicated "mcp" platform, since this is a personal, single-user tool
without a browser session to authenticate — the AC gate, daily caps, and
personal-token LLM guarantee all still apply exactly as they do for the
extension; only the auth transport is skipped.
"""

from __future__ import annotations

import contextlib
import sys

from mcp.server.mcpserver import MCPServer

server = MCPServer(
    name="alfred",
    instructions=(
        "Alfred is a Socratic coding mentor for LeetCode-style problems. It "
        "refuses to hand over solution code before the user has a passing "
        "submission themselves (the 'AC gate') — get_hint only ever returns "
        "code-free nudges pre-solve, and get_review / get_interview_questions "
        "both refuse until submit_for_ac_gate has recorded an accepted verdict "
        "for that problem.\n\n"
        "Typical flow: get_hint while the user is stuck -> once they pass on "
        "the real judge, call submit_for_ac_gate with their verdict -> then "
        "get_review and/or get_interview_questions unlock for that code."
    ),
)

_LOCAL_USER_EMAIL = "mcp@alfred.local"
_LOCAL_PLATFORM = "mcp"


@contextlib.contextmanager
def _quiet():
    """Keep stdout free for the MCP protocol; redirect any incidental prints
    (Alembic, etc.) to stderr for the duration of a tool call.
    """
    original = sys.stdout
    sys.stdout = sys.stderr
    try:
        yield
    finally:
        sys.stdout = original


def _hint_service():
    from .config import get_settings
    from .mentor.cards import CardStore
    from .mentor.llm import Mentor
    from .mentor.service import HintService

    settings = get_settings()
    cards = CardStore().load_dir()
    return HintService(cards, Mentor(settings))


def _local_user(db):
    from sqlalchemy import select

    from .models import User

    user = db.scalar(select(User).where(User.email == _LOCAL_USER_EMAIL))
    if user is None:
        user = User(email=_LOCAL_USER_EMAIL, handle="mcp")
        db.add(user)
        db.commit()
    return user


def _session_for(db, user, slug: str, language: str):
    from sqlalchemy import select

    from .models import Session

    s = db.scalar(
        select(Session)
        .where(Session.user_id == user.id, Session.platform == _LOCAL_PLATFORM, Session.slug == slug)
        .order_by(Session.id.desc())
    )
    if s is None:
        s = Session(user_id=user.id, platform=_LOCAL_PLATFORM, slug=slug, language=language)
        db.add(s)
        db.commit()
    elif language and s.language != language:
        s.language = language
        db.commit()
    return s


@contextlib.contextmanager
def _db_session():
    """A DB session bound to *whatever* `get_settings().database_url` resolves
    to right now — not `alfred.db`'s module-level `SessionLocal`, which is
    bound once at import time. A long-running MCP server only ever sees one
    settings.database_url in practice, but tests set `ALFRED_DATABASE_URL` per
    test to a throwaway file and must not leak into (or be corrupted by) the
    process-wide `alfred.db` engine other test modules rely on.
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from .config import get_settings
    from .db import init_db

    init_db()  # re-reads settings itself; safe on a fresh, current, or stale DB
    settings = get_settings()
    connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
    engine = create_engine(settings.database_url, connect_args=connect_args)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = session_factory()
    try:
        yield db
    finally:
        db.close()
        engine.dispose()


# --------------------------------------------------------------------------- #
# Tools
# --------------------------------------------------------------------------- #


@server.tool(
    description=(
        "Get a Socratic hint for a problem, by LeetCode-style slug (e.g. "
        "'two-sum'). Levels 1-4 are always code-free; level 5 (full solution) "
        "is refused until submit_for_ac_gate has recorded a passing verdict for "
        "this slug — that refusal is the AC gate, not a bug. Pass the user's "
        "current code and personalized=true to get a hint tailored to what "
        "they've actually written (costs one of their daily LLM calls; falls "
        "back to the free card path if that budget is spent or no code-mentor "
        "key is configured)."
    )
)
def get_hint(slug: str, level: int, code: str = "", personalized: bool = False, language: str = "python") -> str:
    from .mentor.service import BudgetError, CardMissingError, HintGateError

    with _quiet(), _db_session() as db:
        hints = _hint_service()
        user = _local_user(db)
        session = _session_for(db, user, slug, language)
        try:
            hint = hints.get_hint(db, user, session, level, code=code or None, personalized=personalized)
        except HintGateError as e:
            return f"Gate refused this request: {e}"
        except BudgetError as e:
            return f"Daily budget hit: {e}"
        except CardMissingError:
            return f"No Problem Card could be built for '{slug}'."
    return (
        f"[level {hint.level}, {hint.kind} via {hint.source}] {hint.nudge}\n"
        f"Hints remaining today: {hint.hints_remaining_today}"
    )


@server.tool(
    description=(
        "Record a submission verdict for a problem, flipping the AC gate open "
        "on an accepted one. This is the ONLY way get_review and "
        "get_interview_questions unlock for a slug — Alfred never infers a pass "
        "from code alone. `verdict` should be what the judge said, e.g. "
        "'Accepted', 'Wrong Answer', 'Time Limit Exceeded'."
    )
)
def submit_for_ac_gate(slug: str, verdict: str, language: str = "python") -> str:
    from .gamification import progress

    with _quiet(), _db_session() as db:
        user = _local_user(db)
        session = _session_for(db, user, slug, language)
        result = progress.on_verdict(db, user, session, verdict)

    if not result.get("accepted"):
        return f"'{verdict}' recorded — not an accepted verdict, gate stays closed for '{slug}'."
    if result.get("already_solved"):
        return f"'{slug}' was already solved; gate stays open, no XP awarded again."
    return (
        f"Accepted. Gate open for '{slug}'. "
        f"XP awarded: {result.get('xp_awarded', 0)} "
        f"({'clean' if result.get('clean') else 'hinted, ' + str(result.get('hints_used', 0)) + ' hint(s)'}). "
        f"Streak: {result.get('streak_current', 0)} day(s)."
    )


@server.tool(
    description=(
        "Get a multi-lens code review for a problem the user has already "
        "passed (via submit_for_ac_gate). Free and offline — never calls an "
        "LLM. `persona` selects the reviewer voice: mentor, roast, "
        "interviewer, pragmatist, professor, or deadpan. Refuses with a clear "
        "message if the AC gate for this slug is not open yet."
    )
)
def get_review(slug: str, code: str, persona: str = "mentor", failed_attempts: int = 0, language: str = "python") -> str:
    from .mentor.service import CardMissingError, HintGateError

    with _quiet(), _db_session() as db:
        hints = _hint_service()
        user = _local_user(db)
        session = _session_for(db, user, slug, language)
        try:
            review = hints.review(db, session, code, persona=persona, failed_attempts=failed_attempts)
        except HintGateError as e:
            return f"Gate refused this request: {e}"
        except CardMissingError:
            return f"No Problem Card could be built for '{slug}'."

    lines = [
        f"[{review.persona_label}] {review.headline}",
        f"Verdict: {review.verdict}",
        f"Complexity: {review.complexity_time} time / {review.complexity_space} space "
        f"(target: {review.target_time})",
    ]
    if review.what_you_did_well:
        lines.append("Did well: " + "; ".join(review.what_you_did_well))
    if review.try_next:
        lines.append("Try next: " + "; ".join(review.try_next))
    if review.failure_gallery:
        lines.append(f"Failure gallery: {len(review.failure_gallery)} case(s) — {review.failure_intro}")
    return "\n".join(lines)


@server.tool(
    description=(
        "Get interview-mode questions generated from the user's own accepted "
        "submission for a problem (requires submit_for_ac_gate to have opened "
        "the gate for this slug first). Answers are withheld by design — this "
        "is meant to be worked through, not read."
    )
)
def get_interview_questions(slug: str, code: str, limit: int = 4, language: str = "python") -> str:
    from .mentor.service import CardMissingError, HintGateError

    with _quiet(), _db_session() as db:
        hints = _hint_service()
        user = _local_user(db)
        session = _session_for(db, user, slug, language)
        try:
            questions = hints.interview(db, session, code, limit=limit)
        except HintGateError as e:
            return f"Gate refused this request: {e}"
        except CardMissingError:
            return f"No Problem Card could be built for '{slug}'."

    if not questions:
        return f"No interview questions generated for '{slug}'."
    return "\n".join(f"- ({q['key']}) {q['question']}" for q in questions)



@server.tool(description="List system-design practice scenarios (id, title).")
def sd_list() -> str:
    from alfred import sysdesign

    return "\n".join(f"{x['id']}: {x['title']}" for x in sysdesign.list_scenarios())


@server.tool(description="System-design Socratic hint. level 0=prompt, 1=clarify, 2=estimate, 3=components, 4=failure modes. Never reveals the reference design.")
def sd_hint(scenario: str, level: int = 0) -> str:
    from alfred import sysdesign

    try:
        return sysdesign.hint(scenario, level)
    except sysdesign.SysDesignError as e:
        return f"Error: {e}"


@server.tool(description="Submit your written design (80+ words). Returns rubric coverage, what you missed, and only then the reference design (the gate).")
def sd_review(scenario: str, design: str) -> str:
    from alfred import sysdesign

    try:
        return sysdesign.render_review(sysdesign.review(scenario, design))
    except sysdesign.SysDesignError as e:
        return f"Gate refused: {e}"


@server.tool(description="Explain a CS concept, building on the learner's own vault notes (local model, free). Returns the explanation, which notes it built on, and a check-your-understanding question.")
def explain_concept(concept: str) -> str:
    from .config import get_settings
    from .mentor.llm import Mentor

    with _quiet():
        result = Mentor(get_settings()).explain(concept)
    if result is None:
        return "No model backend available (start Ollama or set ALFRED_LLM_BACKEND)."
    parts = [result["explanation"]]
    if result["builds_on"]:
        parts.append("Builds on your notes: " + ", ".join(result["builds_on"]))
    parts.append("Check yourself: " + result["check_question"])
    return "\n\n".join(parts)


@server.tool(description="Start a quiz on a topic, generated only from the learner's own vault notes. Returns a quiz_id and numbered questions (answers hidden).")
def quiz_start(topic: str, n: int = 3) -> str:
    from . import quiz
    from .config import get_settings
    from .mentor.llm import Mentor

    try:
        with _quiet():
            settings = get_settings()
            q = quiz.start(settings, Mentor(settings), topic, n)
    except quiz.QuizError as e:
        return f"Error: {e}"
    lines = [f"quiz_id: {q.id}"] + [f"{i}. {x.question} (from: {x.source_note})" for i, x in enumerate(q.questions)]
    return chr(10).join(lines)


@server.tool(description="Answer question `index` of a quiz; returns score (0-2), feedback and the reference answer.")
def quiz_answer(quiz_id: str, index: int, answer: str) -> str:
    from . import quiz
    from .config import get_settings
    from .mentor.llm import Mentor

    try:
        with _quiet():
            q = quiz.load(quiz_id)
            res = quiz.answer(Mentor(get_settings()), q, index, answer)
    except quiz.QuizError as e:
        return f"Error: {e}"
    return f"score {res.score}/2. {res.feedback} Reference: {res.answer}"


@server.tool(description="Finish a quiz: records mastery and schedules the next spaced review in the vault.")
def quiz_finish(quiz_id: str) -> str:
    from . import quiz
    from .config import get_settings

    try:
        r = quiz.finish(get_settings(), quiz.load(quiz_id))
    except quiz.QuizError as e:
        return f"Error: {e}"
    return f"mastery {int(r['mastery'] * 100)}%, next review {r['next_due']} (in {r['interval_days']} days)"


def main() -> None:
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
