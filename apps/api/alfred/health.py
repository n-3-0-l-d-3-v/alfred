"""Health payload shared by the HTTP `/health` route and the `alfred --health`
CLI command (see `__main__.py`) — the ecosystem's `agent.yaml` contract points
`health_check_command` at the latter so an orchestrator can check Alfred is
alive without going through a browser or an HTTP client.

Keeps every field the extension panel already branches on (`ok`, `cards`,
`llm`, `languages`, `auth`) and adds the KPIs an orchestrator cares about:
version, DB connectivity, whether the optional LLM path is configured, and
today's hint/model-call counts against their daily caps.
"""

from __future__ import annotations

from datetime import datetime, time

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session as DbSession

from .config import Settings, get_settings
from .models import HintEvent, utcnow

VERSION = "0.1.0"


def _db_connectivity(db: DbSession | None) -> dict:
    if db is None:
        return {"connected": False, "error": "no session available"}
    try:
        db.execute(select(1))
        return {"connected": True, "error": None}
    except SQLAlchemyError as exc:  # pragma: no cover - defensive
        return {"connected": False, "error": str(exc)}


def _usage_today(db: DbSession | None, source: str, cap: int) -> dict:
    """Aggregate (not per-user) count of `source` hint_events today, against
    the per-user daily cap — a system-wide KPI, not a per-user budget check
    (see gamification/budget.py for the per-user enforcement itself).
    """
    if db is None:
        return {"used_today": None, "cap_per_user": cap}
    try:
        start = datetime.combine(utcnow().date(), time.min)
        stmt = select(func.count()).select_from(HintEvent).where(
            HintEvent.source == source,
            HintEvent.at >= start,
        )
        used = int(db.execute(stmt).scalar_one())
    except SQLAlchemyError:  # pragma: no cover - defensive
        used = None
    return {"used_today": used, "cap_per_user": cap}


def build_health_payload(
    *,
    cards: int,
    mentor_available: bool,
    languages: list[str],
    personas: list[str],
    settings: Settings | None = None,
    db: DbSession | None = None,
) -> dict:
    settings = settings or get_settings()
    db_info = _db_connectivity(db)
    ok = db_info["connected"] if db is not None else True

    return {
        "ok": ok,
        "version": VERSION,
        "cards": cards,
        "llm": "online" if mentor_available else "offline",
        "languages": languages,
        "personas": personas,
        "auth": {
            "github": settings.github_oauth_configured,
            "dev": settings.dev_auth_enabled,
            "github_client_id": settings.github_client_id,
        },
        "db": db_info,
        # `personal-token` guarantee: the optional LLM path, when configured,
        # uses a key the operator supplied themselves (ALFRED_ANTHROPIC_API_KEY
        # / legacy LEETLEARN_ANTHROPIC_API_KEY) — never a shared pool. See
        # agent.yaml and README "Personal-token guarantee".
        "llm_configured": bool(settings.anthropic_api_key),
        "llm_backend_setting": settings.llm_backend,
        # Only "card" and "llm" are ever written to hint_events.source today
        # (see mentor/service.py); llm_reviews_per_day is a configured cap
        # with no dedicated source yet, so it is reported as a limit only.
        "usage_today": {
            "card": _usage_today(db, "card", settings.card_hints_per_day),
            "llm": _usage_today(db, "llm", settings.llm_calls_per_day),
            "llm_review": {"used_today": None, "cap_per_user": settings.llm_reviews_per_day},
        },
        "vault": {
            "configured": bool(getattr(settings, "vault_path", None)),
        },
    }
