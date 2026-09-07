"""FastAPI surface for Alfred.

Auth is GitHub OAuth -> signed JWT (see `auth.py`); the `llt_<user_id>` dev
bypass survives only for local work and is off by default.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .analysis import analyze
from .analysis.registry import supported_languages
from .auth import AuthError, current_user, exchange_github_code, issue_token, upsert_github_user
from .config import get_settings
from .db import get_db, init_db
from . import problem_meta
from .gamification import budget, progress, streaks
from .mentor import personas
from .mentor.cards import CardStore
from .mentor.llm import Mentor
from .mentor.service import BudgetError, CardMissingError, HintGateError, HintService
from .models import CardFeedback, Session, User

settings = get_settings()
cards = CardStore().load_dir()
mentor = Mentor(settings)
hints = HintService(cards, mentor)

@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Runs the real Alembic migrations, not a schema shortcut — safe on a
    # fresh database, a current one, or a stale one left over from an older
    # checkout (see db.py for why that distinction matters here).
    init_db()
    yield


app = FastAPI(title="Alfred API", version="0.1.0", lifespan=lifespan)

# The extension panel is an extension-origin page calling a different host, so
# it needs CORS. Origins are explicit rather than "*" — an allow-all API that
# accepts Authorization headers is an open door for any site the user visits.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=r"^(chrome-extension|moz-extension)://[a-z0-9-]+$",
    allow_methods=["GET", "POST"],
    allow_headers=["authorization", "content-type"],
)


# --- request bodies ----------------------------------------------------------


class DevLogin(BaseModel):
    email: str
    handle: str | None = None


class GithubLogin(BaseModel):
    code: str
    redirect_uri: str | None = None


class StartSession(BaseModel):
    slug: str
    language: str = "python"
    # Defaults to leetcode so existing clients keep working unchanged.
    platform: str = "leetcode"
    # What the page said about the problem. Optional: an older extension build,
    # or an adapter for a site with nothing to read, simply omits it and the
    # problem is taught from the pattern-free ladder instead.
    title: str | None = None
    difficulty: str | None = None
    topics: list[str] = []
    statement: str | None = None


class AnalyzeIn(BaseModel):
    language: str = "python"
    code: str


class HintIn(BaseModel):
    level: int
    code: str | None = None
    personalized: bool = False


class VerdictIn(BaseModel):
    verdict: str
    code: str | None = None


class ReviewIn(BaseModel):
    code: str
    persona: str = "mentor"
    failed_attempts: int = 0


class FeedbackIn(BaseModel):
    slug: str
    level: int | None = None
    reason: str = "unclear"  # unclear | wrong | gives_away | other
    note: str | None = None


# --- endpoints ---------------------------------------------------------------


@app.get("/health")
def health() -> dict:
    return {
        "ok": True,
        "cards": len(cards),
        "llm": "online" if mentor.available else "offline",
        "languages": supported_languages(),
        "personas": [p["key"] for p in personas.catalog()],
        # The panel reads these to decide which sign-in buttons to render.
        "auth": {
            "github": settings.github_oauth_configured,
            "dev": settings.dev_auth_enabled,
            "github_client_id": settings.github_client_id,
        },
    }


@app.post("/auth/github")
async def github_login(body: GithubLogin, db: DbSession = Depends(get_db)) -> dict:
    """Exchange a GitHub OAuth code for a Alfred JWT."""
    try:
        profile = await exchange_github_code(body.code, body.redirect_uri, settings)
        user = upsert_github_user(db, profile)
        return {
            "user_id": user.id,
            "token": issue_token(user, settings),
            "handle": user.handle,
            "avatar_url": user.avatar_url,
        }
    except AuthError as e:
        raise HTTPException(401, str(e))


@app.post("/auth/dev-login")
def dev_login(body: DevLogin, db: DbSession = Depends(get_db)) -> dict:
    """Local-development sign-in. Disabled unless `dev_auth_enabled` is set."""
    if not settings.dev_auth_enabled:
        raise HTTPException(403, "dev auth is disabled on this server — sign in with GitHub")
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None:
        user = User(email=body.email, handle=body.handle)
        db.add(user)
        db.commit()
    return {"user_id": user.id, "token": f"llt_{user.id}", "handle": user.handle}


@app.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "handle": user.handle,
        "avatar_url": user.avatar_url,
        "tone": user.tone,
        "skill_level": user.skill_level,
    }


@app.post("/analyze")
def analyze_code(body: AnalyzeIn, user: User = Depends(current_user)) -> dict:
    return analyze(body.language, body.code).to_dict()


@app.post("/sessions")
def start_session(body: StartSession, user: User = Depends(current_user), db: DbSession = Depends(get_db)) -> dict:
    """Open (or resume) this user's session for a problem.

    Resuming rather than always inserting is what makes the AC gate and the hint
    counter mean anything: a fresh row per panel-open would reset `hints_used`
    and re-lock a problem the learner already solved, so closing the sidebar
    would launder a hinted solve into a clean one.
    """
    # Record what the page told us before touching the card, so the card can be
    # rebuilt from it on any later request — see `ProblemMeta`.
    meta = problem_meta.remember(
        db,
        platform=body.platform,
        slug=body.slug,
        title=body.title,
        difficulty=body.difficulty,
        topics=body.topics,
        statement=body.statement,
    )
    # No 404 any more. A problem nobody authored a card for is generated from
    # the pattern it looks like, or taught from first principles when no pattern
    # is clear enough to claim. Refusing to open the session was the single
    # largest hole in the product: the knowledge base covers a few dozen
    # problems and the site has thousands, so the common case was a dead panel.
    card = cards.get_or_synthesize(body.slug, **problem_meta.as_kwargs(meta))

    s = db.scalar(
        select(Session)
        .where(
            Session.user_id == user.id,
            Session.platform == body.platform,
            Session.slug == body.slug,
        )
        .order_by(Session.id.desc())
    )
    if s is None:
        s = Session(user_id=user.id, platform=body.platform, slug=body.slug, language=body.language)
        db.add(s)
    elif s.language != body.language:
        s.language = body.language  # they switched language mid-problem
    db.commit()

    return {
        "session_id": s.id,
        "platform": s.platform,
        "slug": s.slug,
        "language": s.language,
        "solved": s.solved,
        "hints_used": s.hints_used,
        "resumed": s.hints_used > 0 or s.solved,
    }


def _load_session(session_id: int, user: User, db: DbSession) -> Session:
    s = db.get(Session, session_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(404, "session not found")
    return s


@app.post("/sessions/{session_id}/hint")
def get_hint(
    session_id: int,
    body: HintIn,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
) -> dict:
    s = _load_session(session_id, user, db)
    try:
        hint = hints.get_hint(db, user, s, body.level, code=body.code, personalized=body.personalized)
    except HintGateError as e:
        raise HTTPException(403, str(e))
    except BudgetError as e:
        raise HTTPException(429, str(e))
    except CardMissingError:
        raise HTTPException(404, "no card for this problem")
    return hint.model_dump()


@app.post("/sessions/{session_id}/verdict")
def submit_verdict(
    session_id: int,
    body: VerdictIn,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
) -> dict:
    s = _load_session(session_id, user, db)
    return progress.on_verdict(db, user, s, body.verdict)


@app.post("/sessions/{session_id}/review")
def review(
    session_id: int,
    body: ReviewIn,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
) -> dict:
    s = _load_session(session_id, user, db)
    try:
        return hints.review(
            db, s, body.code, persona=body.persona, failed_attempts=body.failed_attempts
        ).model_dump()
    except HintGateError as e:
        raise HTTPException(403, str(e))
    except CardMissingError:
        raise HTTPException(404, "no card for this problem")


class InterviewIn(BaseModel):
    code: str
    limit: int = 4


@app.post("/sessions/{session_id}/interview")
def interview(
    session_id: int,
    body: InterviewIn,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
) -> dict:
    """Interview questions about this submission. Answers withheld — see below."""
    s = _load_session(session_id, user, db)
    try:
        return {"questions": hints.interview(db, s, body.code, limit=body.limit)}
    except HintGateError as e:
        raise HTTPException(403, str(e))
    except CardMissingError:
        raise HTTPException(404, "no card for this problem")


@app.post("/sessions/{session_id}/interview/answers")
def interview_answers(
    session_id: int,
    body: InterviewIn,
    user: User = Depends(current_user),
    db: DbSession = Depends(get_db),
) -> dict:
    """Model answers, fetched once the learner has committed to their own.

    A separate call rather than a field on the previous response: if the answers
    travel with the questions they are one devtools tab away, and the entire
    value of the exercise is in answering before you see them.
    """
    s = _load_session(session_id, user, db)
    try:
        return {"answers": hints.interview_answers(db, s, body.code, limit=body.limit)}
    except HintGateError as e:
        raise HTTPException(403, str(e))
    except CardMissingError:
        raise HTTPException(404, "no card for this problem")


@app.get("/personas")
def list_personas() -> dict:
    """Review voices. Findings are identical across personas — only framing changes."""
    return {"personas": personas.catalog()}


@app.post("/feedback")
def report_card(body: FeedbackIn, user: User = Depends(current_user), db: DbSession = Depends(get_db)) -> dict:
    """'This hint was bad.' Drives the review queue for auto-generated cards."""
    db.add(CardFeedback(user_id=user.id, slug=body.slug, level=body.level, reason=body.reason, note=body.note))
    db.commit()
    return {"ok": True, "thanks": "Logged — this card goes into the review queue."}


@app.get("/sessions/{session_id}/unlocked")
def unlocked(session_id: int, user: User = Depends(current_user), db: DbSession = Depends(get_db)) -> dict:
    """The post-AC firehose. 403 until the problem is solved."""
    s = _load_session(session_id, user, db)
    try:
        return hints.post_ac_payload(db, s).model_dump()
    except HintGateError as e:
        raise HTTPException(403, str(e))
    except CardMissingError:
        raise HTTPException(404, "no card for this problem")


@app.get("/sessions/{session_id}/card")
def card_view(session_id: int, user: User = Depends(current_user), db: DbSession = Depends(get_db)) -> dict:
    """Card content, redacted by AC state: pre-AC hides all solution code."""
    s = _load_session(session_id, user, db)
    meta = problem_meta.lookup(db, s.platform, s.slug)
    card = cards.get_or_synthesize(s.slug, **problem_meta.as_kwargs(meta))
    view = {
        "slug": card.slug,
        "title": card.title,
        "difficulty": card.difficulty,
        "topics": card.topics,
        "understanding": card.understanding,
        "patterns": [p.model_dump() for p in card.patterns],
        "solved": s.solved,
        # The panel has always rendered an "unverified" badge off this field,
        # and the endpoint never sent it — so every generated card was shown
        # with the same authority as a hand-checked one, and the report link
        # next to it had nothing to explain itself.
        "verified": card.verified,
        "generated_by": card.generated_by,
    }
    if s.solved:
        view["approaches"] = [a.model_dump() for a in card.approaches]
        view["complexity"] = card.complexity
        view["pitfalls"] = card.pitfalls
        view["edge_cases"] = card.edge_cases
        view["rewrite_challenges"] = card.rewrite_challenges
    return view


@app.get("/progress")
def get_progress(user: User = Depends(current_user), db: DbSession = Depends(get_db)) -> dict:
    s = streaks.get_or_create(db, user.id)
    db.commit()
    return {
        "xp_total": progress.total_xp(db, user.id),
        "streak_current": s.current,
        "streak_longest": s.longest,
        "freezes_left": s.freezes_left,
        "card_hints_left_today": budget.remaining(db, user.id, "card", settings.card_hints_per_day),
        "llm_calls_left_today": budget.remaining(db, user.id, "llm", settings.llm_calls_per_day),
    }
