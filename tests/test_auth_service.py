from app.core.security import hash_password
from app.models.user import User
from app.services.auth import (
    authenticate_user,
    get_user_by_username,
)


def test_username_lookup_is_case_insensitive(
    db_session,
):
    user = User(
        username="Coach",
        password_hash=hash_password("password123"),
    )

    db_session.add(user)
    db_session.commit()

    found = get_user_by_username(
        db_session,
        "COACH",
    )

    assert found is not None
    assert found.id == user.id


def test_authenticate_user_with_valid_credentials(
    db_session,
):
    user = User(
        username="coach",
        password_hash=hash_password("correct-password"),
    )

    db_session.add(user)
    db_session.commit()

    authenticated = authenticate_user(
        db_session,
        "coach",
        "correct-password",
    )

    assert authenticated is not None
    assert authenticated.id == user.id


def test_authenticate_user_rejects_wrong_password(
    db_session,
):
    user = User(
        username="coach",
        password_hash=hash_password("correct-password"),
    )

    db_session.add(user)
    db_session.commit()

    assert authenticate_user(
        db_session,
        "coach",
        "wrong-password",
    ) is None


def test_authenticate_user_rejects_inactive_user(
    db_session,
):
    user = User(
        username="coach",
        password_hash=hash_password("correct-password"),
        is_active=False,
    )

    db_session.add(user)
    db_session.commit()

    assert authenticate_user(
        db_session,
        "coach",
        "correct-password",
    ) is None