from __future__ import annotations

import os

# Set before anything calls `get_settings()` (it is lru_cached, so the first
# call wins). Dev auth is off by default in the app so a misconfigured
# deployment fails closed; the suite drives endpoints with `llt_` tokens and
# opts back in here deliberately.
os.environ.setdefault("LEETLEARN_DEV_AUTH_ENABLED", "true")
os.environ.setdefault("LEETLEARN_JWT_SECRET", "test-secret-not-used-in-prod-long-enough-for-hs256")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from leetlearn.mentor.cards import CardStore
from leetlearn.mentor.llm import Mentor
from leetlearn.mentor.service import HintService
from leetlearn.models import Base, User
from leetlearn.config import Settings


@pytest.fixture
def db():
    # StaticPool pins every checkout to one connection. SQLite gives each
    # connection its own private :memory: database, and TestClient runs the app
    # on a separate thread — without this the endpoint tests would open a second,
    # empty database and every query would 'no such table'.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, expire_on_commit=False)
    s = Session()
    try:
        yield s
    finally:
        s.close()


@pytest.fixture
def user(db):
    u = User(email="dev@leetlearn.test", handle="dev")
    db.add(u)
    db.commit()
    return u


@pytest.fixture
def cards():
    return CardStore().load_dir()


@pytest.fixture
def service(cards):
    # No API key => offline mentor; card/heuristic paths only.
    return HintService(cards, Mentor(Settings(anthropic_api_key=None)))


@pytest.fixture
def client(db):
    """TestClient wired to the in-memory `db` fixture.

    `get_db` is overridden rather than letting the app open its own session, so
    endpoint tests and the ORM fixtures observe the same rows.
    """
    from fastapi.testclient import TestClient

    from leetlearn.db import get_db
    from leetlearn.main import app

    app.dependency_overrides[get_db] = lambda: db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
