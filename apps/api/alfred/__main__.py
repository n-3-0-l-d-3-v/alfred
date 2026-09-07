"""`python -m alfred` — the renamed run command this project's `agent.yaml`
points `entrypoint` and `health_check_command` at.

  python -m alfred                 # serve the API on 127.0.0.1:8000
  python -m alfred --host 0.0.0.0 --port 8000 --reload
  python -m alfred --health        # print health JSON and exit, no server

`--health` builds the same payload as the HTTP `/health` route but opens its
own short-lived DB session and exits — no server needs to be running, which
is what lets an external orchestrator use it as a liveness/readiness probe
(`health_check_command: python -m alfred --health` in agent.yaml).
"""

from __future__ import annotations

import argparse
import json
import sys


def _run_health_check() -> int:
    from .analysis.registry import supported_languages
    from .config import get_settings
    from .db import SessionLocal, init_db
    from .health import build_health_payload
    from .mentor import personas
    from .mentor.cards import CardStore
    from .mentor.llm import Mentor

    settings = get_settings()
    cards = CardStore().load_dir()
    mentor = Mentor(settings)

    db = None
    try:
        init_db()
        db = SessionLocal()
    except Exception:  # pragma: no cover - defensive; report, don't crash
        db = None

    try:
        payload = build_health_payload(
            cards=len(cards),
            mentor_available=mentor.available,
            languages=supported_languages(),
            personas=[p["key"] for p in personas.catalog()],
            settings=settings,
            db=db,
        )
    finally:
        if db is not None:
            db.close()

    print(json.dumps(payload, indent=2))
    return 0 if payload["ok"] else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="alfred", description="Alfred learning-mentor API")
    parser.add_argument("--health", action="store_true", help="Print health JSON and exit (no server started).")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Auto-reload on source changes (dev only).")
    args = parser.parse_args(argv)

    if args.health:
        return _run_health_check()

    import uvicorn

    uvicorn.run("alfred.main:app", host=args.host, port=args.port, reload=args.reload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
