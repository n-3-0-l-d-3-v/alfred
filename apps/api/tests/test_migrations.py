"""Migrations must stay in step with the models.

Alembic and SQLAlchemy drift apart silently: you add a column, the tests pass
because they build tables with `create_all`, and the mismatch only appears as a
500 against the deployed database. This runs the real migrations into a scratch
database and asserts autogenerate finds nothing left to do.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.command import upgrade
from alembic.config import Config
from alembic.migration import MigrationContext
from sqlalchemy import create_engine

from leetlearn.models import Base

API_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def migrated_engine(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("LEETLEARN_DATABASE_URL", url)

    # env.py resolves the URL through the cached Settings, so the cache has to
    # be dropped for the monkeypatched env var to take effect.
    from leetlearn.config import get_settings

    get_settings.cache_clear()
    try:
        cfg = Config(str(API_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
        upgrade(cfg, "head")
        yield create_engine(url)
    finally:
        get_settings.cache_clear()


def test_migrations_produce_the_model_schema(migrated_engine):
    with migrated_engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"compare_type": True})
        diff = compare_metadata(ctx, Base.metadata)

    assert diff == [], (
        "Models and migrations disagree. Run:\n"
        "  alembic revision --autogenerate -m 'describe the change'\n"
        f"Outstanding differences: {diff}"
    )
