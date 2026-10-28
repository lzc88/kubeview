import os

os.environ["POSTGRES_DB"] = "payments_test"
os.environ["PROVIDER"] = "fake"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

import ecommerce.payments.db.models  # noqa: F401
from ecommerce.payments.config import settings
from ecommerce.payments.db.base import Base
from ecommerce.payments.db.db import engine, get_session
from ecommerce.payments.main import app


@pytest.fixture(scope="session", autouse=True)
def tables():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def session():
    with engine.connect() as connection:
        transaction = connection.begin()
        session = Session(
            bind=connection,
            join_transaction_mode="create_savepoint",
            expire_on_commit=False,
        )
        yield session
        session.close()
        transaction.rollback()


@pytest.fixture
def client(session, monkeypatch):
    monkeypatch.setattr(settings, "latency_ms", 0)
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
