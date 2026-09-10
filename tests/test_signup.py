import re

import pytest
from pydantic import SecretStr
from sqlalchemy import func, select

from app.core.config import settings
from app.core.security import hash_password, verify_password
from app.models.user import User
from app.routes import auth as auth_routes


ACCESS_CODE = "private-school-access-code-2026"
VALID_PASSWORD = "valid-signup-password"
GENERIC_ERROR = (
    "Account could not be created with the "
    "provided information."
)


@pytest.fixture()
def signup_enabled(monkeypatch):
    monkeypatch.setattr(
        settings,
        "signup_access_code",
        SecretStr(ACCESS_CODE),
    )


def _signup_token(client) -> str:
    response = client.get("/signup")
    assert response.status_code == 200

    match = re.search(
        r'name="csrf_token"\s+'
        r'value="([^"]+)"',
        response.text,
    )
    assert match is not None
    return match.group(1)


def _signup_data(
    csrf_token: str,
    *,
    username: str = "NewCoach",
    password: str = VALID_PASSWORD,
    password_confirmation: str = VALID_PASSWORD,
    school_access_code: str = ACCESS_CODE,
) -> dict[str, str]:
    return {
        "csrf_token": csrf_token,
        "username": username,
        "password": password,
        "password_confirmation": password_confirmation,
        "school_access_code": school_access_code,
    }


def test_signup_page_is_public_and_creates_csrf_token(
    client,
    signup_enabled,
):
    response = client.get("/signup")

    assert response.status_code == 200
    assert 'action="/signup"' in response.text
    assert 'name="username"' in response.text
    assert 'name="password"' in response.text
    assert 'name="password_confirmation"' in response.text
    assert 'name="school_access_code"' in response.text
    assert 'minlength="8"' in response.text
    assert 'class="button auth-secondary-button"' in response.text
    assert 'href="/login"' in response.text
    assert _signup_token(client)


def test_authenticated_user_is_redirected_from_signup(
    client,
    db_session,
    signup_enabled,
):
    user = User(
        username="coach",
        password_hash=hash_password("existing-password"),
    )
    db_session.add(user)
    db_session.commit()

    login_response = client.post(
        "/login",
        data={
            "username": "coach",
            "password": "existing-password",
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 303

    response = client.get(
        "/signup",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/"


def test_signup_get_and_post_return_404_when_disabled(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "signup_access_code",
        SecretStr(ACCESS_CODE),
    )
    csrf_token = _signup_token(client)

    monkeypatch.setattr(
        settings,
        "signup_access_code",
        None,
    )

    get_response = client.get("/signup")
    post_response = client.post(
        "/signup",
        data=_signup_data(csrf_token),
    )

    assert get_response.status_code == 404
    assert post_response.status_code == 404


def test_login_signup_link_reflects_configuration(
    client,
    monkeypatch,
):
    monkeypatch.setattr(
        settings,
        "signup_access_code",
        None,
    )
    disabled_response = client.get("/login")

    monkeypatch.setattr(
        settings,
        "signup_access_code",
        SecretStr(ACCESS_CODE),
    )
    enabled_response = client.get("/login")

    assert 'href="/signup"' not in disabled_response.text
    assert "Don't have an account?" not in disabled_response.text
    assert 'href="/signup"' in enabled_response.text
    assert "Don't have an account?" in enabled_response.text
    assert (
        'class="button auth-secondary-button"'
        in enabled_response.text
    )


def test_valid_signup_creates_active_user_and_clears_session(
    client,
    db_session,
    signup_enabled,
):
    csrf_token = _signup_token(client)
    plaintext_password = VALID_PASSWORD

    response = client.post(
        "/signup",
        data=_signup_data(
            csrf_token,
            username="  CoachJordan  ",
            password=plaintext_password,
            password_confirmation=plaintext_password,
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login?created=1"

    user = db_session.scalar(
        select(User).where(
            User.username == "CoachJordan"
        )
    )
    assert user is not None
    assert user.is_active is True
    assert user.password_hash != plaintext_password
    assert user.password_hash.startswith("$argon2")
    assert verify_password(
        plaintext_password,
        user.password_hash,
    )
    assert not hasattr(user, "password_confirmation")
    assert not hasattr(user, "school_access_code")

    protected_response = client.get(
        "/",
        follow_redirects=False,
    )
    assert protected_response.status_code == 303


def test_login_shows_created_message_and_new_user_can_login(
    client,
    signup_enabled,
):
    csrf_token = _signup_token(client)
    signup_response = client.post(
        "/signup",
        data=_signup_data(csrf_token),
        follow_redirects=False,
    )
    assert signup_response.status_code == 303

    login_page = client.get("/login?created=1")
    assert (
        "Account created. You can now sign in."
        in login_page.text
    )

    login_response = client.post(
        "/login",
        data={
            "username": "newcoach",
            "password": VALID_PASSWORD,
        },
        follow_redirects=False,
    )
    assert login_response.status_code == 303
    assert login_response.headers["location"] == "/"


@pytest.mark.parametrize(
    ("username", "password", "confirmation", "message"),
    [
        (
            "   ",
            VALID_PASSWORD,
            VALID_PASSWORD,
            "Username cannot be blank.",
        ),
        (
            "u" * 51,
            VALID_PASSWORD,
            VALID_PASSWORD,
            "Username must be 50 characters or fewer.",
        ),
        (
            "coach",
            "p" * 7,
            "p" * 7,
            "Password must be at least 8 characters.",
        ),
        (
            "coach",
            "p" * 129,
            "p" * 129,
            "Password must be 128 characters or fewer.",
        ),
        (
            "coach",
            VALID_PASSWORD,
            "different-password",
            "Passwords do not match.",
        ),
    ],
)
def test_signup_validation_creates_no_user(
    client,
    db_session,
    signup_enabled,
    username,
    password,
    confirmation,
    message,
):
    response = client.post(
        "/signup",
        data=_signup_data(
            _signup_token(client),
            username=username,
            password=password,
            password_confirmation=confirmation,
        ),
    )

    assert response.status_code == 400
    assert message in response.text
    assert db_session.scalar(
        select(func.count()).select_from(User)
    ) == 0
    assert password not in response.text


def test_wrong_access_code_uses_generic_error_and_creates_no_user(
    client,
    db_session,
    signup_enabled,
):
    submitted_code = "incorrect-private-code"
    response = client.post(
        "/signup",
        data=_signup_data(
            _signup_token(client),
            school_access_code=submitted_code,
        ),
    )

    assert response.status_code == 400
    assert GENERIC_ERROR in response.text
    assert submitted_code not in response.text
    assert db_session.scalar(
        select(func.count()).select_from(User)
    ) == 0


def test_duplicate_username_uses_same_generic_error(
    client,
    db_session,
    signup_enabled,
):
    existing = User(
        username="NewCoach",
        password_hash=hash_password("existing-password"),
    )
    db_session.add(existing)
    db_session.commit()

    response = client.post(
        "/signup",
        data=_signup_data(
            _signup_token(client),
            username="newcoach",
        ),
    )

    assert response.status_code == 400
    assert GENERIC_ERROR in response.text
    assert db_session.scalar(
        select(func.count()).select_from(User)
    ) == 1


def test_signup_rejects_missing_and_invalid_csrf(
    client,
    signup_enabled,
):
    missing_response = client.post(
        "/signup",
        data=_signup_data(""),
    )
    invalid_response = client.post(
        "/signup",
        data=_signup_data("invalid-token"),
    )

    assert missing_response.status_code == 403
    assert invalid_response.status_code == 403


def test_invalid_access_code_is_checked_before_user_creation(
    client,
    signup_enabled,
    monkeypatch,
):
    called = False

    def fail_if_called(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("create_user must not be called")

    monkeypatch.setattr(
        auth_routes,
        "create_user",
        fail_if_called,
    )

    response = client.post(
        "/signup",
        data=_signup_data(
            _signup_token(client),
            school_access_code="wrong-code",
        ),
    )

    assert response.status_code == 400
    assert called is False


def test_signup_rate_limit_returns_generic_429(
    client,
    signup_enabled,
):
    csrf_token = _signup_token(client)

    for _ in range(5):
        response = client.post(
            "/signup",
            data=_signup_data(
                csrf_token,
                school_access_code="wrong-code",
            ),
        )
        assert response.status_code == 400

    response = client.post(
        "/signup",
        data=_signup_data(
            csrf_token,
            school_access_code="wrong-code",
        ),
    )

    assert response.status_code == 429
    assert response.text == "Too Many Requests"


def test_login_rate_limit_returns_generic_429(client):
    for _ in range(10):
        response = client.post(
            "/login",
            data={
                "username": "unknown",
                "password": "invalid-password",
            },
        )
        assert response.status_code == 401

    response = client.post(
        "/login",
        data={
            "username": "unknown",
            "password": "invalid-password",
        },
    )

    assert response.status_code == 429
    assert response.text == "Too Many Requests"
