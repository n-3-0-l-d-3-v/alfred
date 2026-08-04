"""FastAPI surface for the LeetLearn dev slice.

Auth here is a DEV STUB (token == "llt_<user_id>"); replace with magic-link or
OAuth->JWT for the Phase 0 completion milestone. Everything else — the AC gate,
budgets, streaks, offline review — is the real implementation.
"""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from .analysis import analyze
from .analysis.registry import supported_languages
from .config import get_settings
from .db import get_db, init_db
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
    init_db()
    yield


app = FastAPI(title="LeetLearn API", version="0.1.0", lifespan=lifespan)


# --- auth (dev stub) ---------------------------------------------------------


def current_user(
    authorization: str | None = Header(default=None), db: DbSession = Depends(get_db)
) -> User:
    if not authorization or not authorization.startswith("Bearer llt_"):
        raise HTTPException(401, "missing or malformed dev token (expected 'Bearer llt_<id>')")
    try:
        user_id = int(authorization.removeprefix("Bearer llt_"))
    except ValueError:
        raise HTTPException(401, "bad dev token")
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(401, "unknown user")
    return user


# --- request bodies ----------------------------------------------------------


class DevLogin(BaseModel):
    email: str
    handle: str | None = None



class StartSession(BaseModel):
    slug: str
    language: str = "python"


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
    }


@app.post("/auth/dev-login")
def dev_login(body: DevLogin, db: DbSession = Depends(get_db)) -> dict:
    if not settings.dev_auth_enabled:
        raise HTTPException(403, "dev auth disabled")
    user = db.scalar(select(User).where(User.email == body.email))
    if user is None:
        user = User(email=body.email, handle=body.handle)
        db.add(user)
        db.commit()
    return {"user_id": user.id, "token": f"llt_{user.id}", "handle": user.handle}


@app.get("/me")
def me(user: User = Depends(current_user)) -> dict:
    return {"id": user.id, "email": user.email, "handle": user.handle, "tone": user.tone, "skill_level": user.skill_level}


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
    if cards.get(body.slug) is None:
        raise HTTPException(404, f"no problem card for '{body.slug}' yet (KB covers {cards.slugs()})")

    s = db.scalar(
        select(Session)
        .where(Session.user_id == user.id, Session.slug == body.slug)
        .order_by(Session.id.desc())
    )
    if s is None:
        s = Session(user_id=user.id, slug=body.slug, language=body.language)
        db.add(s)
    elif s.language != body.language:
        s.language = body.language  # they switched language mid-problem
    db.commit()

    return {
        "session_id": s.id,
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
            s, body.code, persona=body.persona, failed_attempts=body.failed_attempts
        ).model_dump()
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
        return hints.post_ac_payload(s).model_dump()
    except HintGateError as e:
        raise HTTPException(403, str(e))
    except CardMissingError:
        raise HTTPException(404, "no card for this problem")


@app.get("/sessions/{session_id}/card")
def card_view(session_id: int, user: User = Depends(current_user), db: DbSession = Depends(get_db)) -> dict:
    """Card content, redacted by AC state: pre-AC hides all solution code."""
    s = _load_session(session_id, user, db)
    card = cards.get(s.slug)
    if card is None:
        raise HTTPException(404, "no card")
    view = {
        "slug": card.slug,
        "title": card.title,
        "difficulty": card.difficulty,
        "topics": card.topics,
        "understanding": card.understanding,
        "patterns": [p.model_dump() for p in card.patterns],
        "solved": s.solved,
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
