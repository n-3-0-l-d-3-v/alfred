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

from alfred.models import Base

API_ROOT = Path(__file__).resolve().parent.parent


@pytest.fixture
def migrated_engine(tmp_path, monkeypatch):
    url = f"sqlite:///{tmp_path / 'migrated.db'}"
    monkeypatch.setenv("ALFRED_DATABASE_URL", url)

    # env.py resolves the URL through the cached Settings, so the cache has to
    # be dropped for the monkeypatched env var to take effect.
    from alfred.config import get_settings

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


def test_init_db_heals_a_database_stuck_on_an_older_revision(tmp_path, monkeypatch):
    """Reproduces the exact failure a stale local checkout hits: a `alfred.db`
    created before the `platform` column existed, still sitting at the initial
    revision, with a server that just started up against it.

    Before this fix, `init_db()` called `Base.metadata.create_all`, which only
    creates missing tables — it never alters one that's already there. A
    database stuck at the initial revision stayed stuck forever, and every
    request touching `sessions.platform` 500'd with
    `no such column: sessions.platform`. That failure doesn't announce itself
    as a schema problem: it degrades every downstream feature (hints, review,
    personas) to generic content, because the request never got far enough to
    read the learner's code. `init_db()` now runs the real migrations, which
    heals a database in this state instead of leaving it broken.

    This calls `db.init_db()` itself — not a reimplementation of it — so a
    regression in the real function is what this test would catch. It follows
    the same monkeypatch-env-and-clear-the-settings-cache approach as
    `migrated_engine` above, and deliberately avoids reloading `alfred.db`:
    that module's `engine`/`SessionLocal` are shared, live objects other tests
    depend on, and reloading it to retarget them mid-suite is what corrupted
    every test in `test_sessions.py` the first time this test was written.
    """
    from alembic.command import upgrade
    from alembic.config import Config

    from alfred.config import get_settings
    from alfred.db import init_db

    url = f"sqlite:///{tmp_path / 'stale.db'}"
    monkeypatch.setenv("ALFRED_DATABASE_URL", url)
    get_settings.cache_clear()
    try:
        # Stop at the *first* migration only — simulates a checkout from before
        # the platform column was added.
        cfg = Config(str(API_ROOT / "alembic.ini"))
        cfg.set_main_option("script_location", str(API_ROOT / "migrations"))
        upgrade(cfg, "c75b833c2454")

        engine = create_engine(url)
        with engine.connect() as conn:
            columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(sessions)")}
        assert "platform" not in columns, "test setup didn't actually stop at the older revision"

        init_db()  # the real function main.py's lifespan calls on every boot

        with engine.connect() as conn:
            columns = {row[1] for row in conn.exec_driver_sql("PRAGMA table_info(sessions)")}
        assert "platform" in columns, "init_db() did not heal the stale schema"
    finally:
        get_settings.cache_clear()
