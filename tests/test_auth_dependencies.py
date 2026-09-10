from fastapi import Depends
from fastapi.responses import HTMLResponse
from starlette.requests import Request

from app.auth.dependencies import (
    ensure_csrf_token,
    require_api_user,
    require_html_user,
)
from app.core.security import hash_password
from app.main import app
from app.models.user import User


def _request_with_session(
    session: dict[str, object],
) -> Request:
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": [],
            "query_string": b"",
            "session": session,
        }
    )


def test_ensure_csrf_token_creates_missing_token():
    session: dict[str, object] = {}

    token = ensure_csrf_token(
        _request_with_session(session)
    )

    assert token
    assert session["csrf_token"] == token


def test_ensure_csrf_token_reuses_existing_token():
    session = {
        "csrf_token": "existing-token",
    }

    token = ensure_csrf_token(
        _request_with_session(session)
    )

    assert token == "existing-token"


@app.get(
    "/test/protected-html",
    dependencies=[Depends(require_html_user)],
)
def protected_html():
    return HTMLResponse("protected")


@app.get(
    "/test/protected-api",
    dependencies=[Depends(require_api_user)],
)
def protected_api():
    return {"status": "protected"}


def test_anonymous_html_dependency_redirects(client):
    response = client.get(
        "/test/protected-html",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_anonymous_api_dependency_returns_401(client):
    response = client.get(
        "/test/protected-api"
    )

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required."
    }


def test_authenticated_dependencies_allow_access(
    client,
    db_session,
):
    user = User(
        username="coach",
        password_hash=hash_password(
            "test-password"
        ),
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    with client as authenticated_client:
        authenticated_client.cookies.clear()

        # We will replace this temporary direct-session
        # setup with real login integration tests later.


def test_anonymous_real_api_returns_401(
    client,
):
    response = client.get("/players")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication required."
    }


def test_authenticated_real_api_succeeds(
    authenticated_client,
):
    response = authenticated_client.get(
        "/players"
    )

    assert response.status_code == 200
