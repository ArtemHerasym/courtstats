import pytest

from app.core.security import (
    verify_password,
)
from app.services.auth import (
    UserAlreadyExistsError,
    authenticate_user,
    create_user,
)


def test_create_user_hashes_password(
    db_session,
):
    user = create_user(
        db_session,
        "coach",
        "secure-password",
    )

    assert user.id is not None
    assert user.username == "coach"
    assert user.is_active is True

    assert (
        user.password_hash
        != "secure-password"
    )

    assert verify_password(
        "secure-password",
        user.password_hash,
    )


def test_created_user_can_authenticate(
    db_session,
):
    create_user(
        db_session,
        "courtstats-coach",
        "test-password",
    )

    user = authenticate_user(
        db_session,
        "courtstats-coach",
        "test-password",
    )

    assert user is not None

    assert (
        user.username
        == "courtstats-coach"
    )


def test_duplicate_username_is_case_insensitive(
    db_session,
):
    create_user(
        db_session,
        "Coach",
        "first-password",
    )

    with pytest.raises(
        UserAlreadyExistsError
    ):
        create_user(
            db_session,
            "coach",
            "second-password",
        )


def test_create_user_rejects_blank_username(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="Username cannot be empty",
    ):
        create_user(
            db_session,
            "   ",
            "password",
        )


def test_create_user_rejects_blank_password(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="Password cannot be empty",
    ):
        create_user(
            db_session,
            "coach",
            "",
        )


def test_authentication_rejects_wrong_password(
    db_session,
):
    create_user(
        db_session,
        "coach",
        "correct-password",
    )

    user = authenticate_user(
        db_session,
        "coach",
        "wrong-password",
    )

    assert user is None