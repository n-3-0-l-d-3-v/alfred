"""Database engine + session factory. SQLite for local dev, Postgres in prod
(swap `LEETLEARN_DATABASE_URL`).

Schema management is Alembic. `init_db()` runs `alembic upgrade head` rather
than `Base.metadata.create_all` — `create_all` only creates tables that don't
exist yet, it never adds a column to a table that's already there. That is a
real, reproducible failure mode, not a hypothetical one: a `leetlearn.db` left
over from before the `platform` column was added silently keeps its old
schema forever, and every request that touches `sessions.platform` 500s with
`no such column: sessions.platform` — which cascades into every downstream
feature (hints, review, personas) looking generic, because the request never
got far enough to read the learner's actual code. Running the real migrations
at startup fixes both a brand-new database and a stale one, uniformly.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings

_settings = get_settings()

# check_same_thread only matters for SQLite + threaded servers.
_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}

engine = create_engine(_settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

_API_ROOT = Path(__file__).resolve().parent.parent


def init_db() -> None:
    """Bring the schema up to `head`. Safe to call on a fresh DB, an already
    up-to-date one, or a stale one — Alembic only applies what's missing.

    Targets whatever `get_settings().database_url` resolves to at call time —
    `migrations/env.py` re-reads Settings itself rather than trusting whatever
    URL is on the `Config` object, so the app and `alembic upgrade head` run
    from a terminal are always pointed at the same database. (Tests that need
    a different target monkeypatch `LEETLEARN_DATABASE_URL` and clear
    `get_settings`'s cache — see `tests/test_migrations.py` — rather than
    reloading this module, which would corrupt its globals for every test
    that runs afterward in the same process.)
    """
    from alembic.command import upgrade
    from alembic.config import Config

    cfg = Config(str(_API_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(_API_ROOT / "migrations"))
    cfg.attributes["configure_logger"] = False
    upgrade(cfg, "head")


def is_sqlite() -> bool:
    return _settings.database_url.startswith("sqlite")


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
