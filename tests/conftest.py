import pytest
import re
from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

import app.models
from app.core.config import settings
from app.database.base import Base
from fastapi.testclient import TestClient

from app.database.dependencies import get_db
from app.main import app

from app.core.security import hash_password
from app.models.user import User

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


@pytest.fixture()
def logged_in_client(
    client,
    db_session,
):
    user = User(
        username="test-coach",
        password_hash=hash_password(
            "test-password",
        ),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    response = client.post(
        "/login",
        data={
            "username": "test-coach",
            "password": "test-password",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    return client


@pytest.fixture()
def authenticated_client(
    logged_in_client,
):
    response = logged_in_client.get(
        "/app/games/new"
    )

    assert response.status_code == 200

    match = re.search(
        r'name="csrf_token"\s+'
        r'value="([^"]+)"',
        response.text,
    )

    assert match is not None

    csrf_token = match.group(1)

    logged_in_client.headers.update(
        {
            "X-CSRF-Token": csrf_token,
        }
    )

    return logged_in_client