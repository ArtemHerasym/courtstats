from app.core.security import hash_password
from app.models.user import User


def _create_user(
    db_session,
    *,
    username: str = "coach",
    password: str = "secure-password",
    is_active: bool = True,
) -> User:
    user = User(
        username=username,
        password_hash=hash_password(password),
        is_active=is_active,
    )

    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return user


def test_login_page_is_public(client):
    response = client.get("/login")

    assert response.status_code == 200
    assert "text/html" in response.headers[
        "content-type"
    ]
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text


def test_valid_login_creates_session(
    client,
    db_session,
):
    _create_user(db_session)

    response = client.post(
        "/login",
        data={
            "username": "coach",
            "password": "secure-password",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"

    cookie = response.headers[
        "set-cookie"
    ].lower()

    assert "courtstats_session=" in cookie
    assert "httponly" in cookie
    assert "samesite=lax" in cookie

    protected_response = client.get("/")

    assert protected_response.status_code == 200


def test_login_is_case_insensitive_for_username(
    client,
    db_session,
):
    _create_user(
        db_session,
        username="TestCoach",
    )

    response = client.post(
        "/login",
        data={
            "username": "testcoach",
            "password": "secure-password",
        },
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_invalid_password_returns_generic_error(
    client,
    db_session,
):
    _create_user(db_session)

    response = client.post(
        "/login",
        data={
            "username": "coach",
            "password": "wrong-password",
        },
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert (
        "Invalid username or password."
        in response.text
    )

    protected_response = client.get(
        "/",
        follow_redirects=False,
    )

    assert protected_response.status_code == 303
    assert (
        protected_response.headers["location"]
        == "/login"
    )


def test_inactive_user_cannot_login(
    client,
    db_session,
):
    _create_user(
        db_session,
        is_active=False,
    )

    response = client.post(
        "/login",
        data={
            "username": "coach",
            "password": "secure-password",
        },
        follow_redirects=False,
    )

    assert response.status_code == 401
    assert (
        "Invalid username or password."
        in response.text
    )