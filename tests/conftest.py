import pytest

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app.models
from app.core.config import settings
from app.database.base import Base
from fastapi.testclient import TestClient

from app.database.dependencies import get_db
from app.main import app

@pytest.fixture(scope="session")
def test_engine():
    if settings.test_database_url is None:
        raise RuntimeError("TEST_DATABASE_URL is not configured.")

    test_url = make_url(settings.test_database_url)
    development_url = make_url(settings.database_url)

    if test_url.database is None or not test_url.database.endswith("_test"):
        raise RuntimeError("Test database name must end with '_test'.")

    if test_url.database == development_url.database:
        raise RuntimeError("Test database must be different from development database.")

    engine = create_engine(
        settings.test_database_url,
        pool_pre_ping=True,
    )

    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)
    engine.dispose()

@pytest.fixture(scope="session")
def testing_session_factory(test_engine):
    return sessionmaker(
        bind=test_engine,
        autoflush=False,
        expire_on_commit=False,
    )

@pytest.fixture()
def db_session(test_engine, testing_session_factory):
    connection = test_engine.connect()
    transaction = connection.begin()

    session = testing_session_factory(
        bind=connection,
        join_transaction_mode="create_savepoint",
    )

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()

@pytest.fixture()
def client(db_session):
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()