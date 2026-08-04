from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from leetlearn.mentor.cards import CardStore
from leetlearn.mentor.llm import Mentor
from leetlearn.mentor.service import HintService
from leetlearn.models import Base, User
from leetlearn.config import Settings


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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

