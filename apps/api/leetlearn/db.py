"""Database engine + session factory. SQLite for local dev, Postgres in prod
(swap `LEETLEARN_DATABASE_URL`).

Schema management is Alembic (`alembic upgrade head`). `init_db` remains only
as a convenience for SQLite dev and the test suite: `create_all` silently skips
tables that already exist, so on a real database it would let a schema drift
away from the migration history without anyone noticing.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .config import get_settings
from .models import Base

_settings = get_settings()

# check_same_thread only matters for SQLite + threaded servers.
_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}

engine = create_engine(_settings.database_url, connect_args=_connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    """Create tables directly. Only safe where migrations aren't in play."""
    Base.metadata.create_all(bind=engine)


def is_sqlite() -> bool:
    return _settings.database_url.startswith("sqlite")


def get_db() -> Iterator[Session]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
