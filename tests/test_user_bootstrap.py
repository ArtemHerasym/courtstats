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
        "test-password-15",
    )

    user = authenticate_user(
        db_session,
        "courtstats-coach",
        "test-password-15",
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
        "first-password-15",
    )

    with pytest.raises(
        UserAlreadyExistsError
    ):
        create_user(
            db_session,
            "coach",
            "second-password-15",
        )


def test_create_user_rejects_blank_username(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="Username cannot be blank",
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
        match="Password must be at least 8 characters",
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


def test_create_user_trims_and_preserves_username_case(
    db_session,
):
    user = create_user(
        db_session,
        "  CoachJordan  ",
        "valid-password-15",
    )

    assert user.username == "CoachJordan"


def test_create_user_allows_one_character_username(
    db_session,
):
    user = create_user(
        db_session,
        "J",
        "valid-password-15",
    )

    assert user.username == "J"


def test_create_user_rejects_username_over_50_characters(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="50 characters or fewer",
    ):
        create_user(
            db_session,
            "u" * 51,
            "valid-password-15",
        )


def test_create_user_rejects_password_under_8_characters(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="at least 8 characters",
    ):
        create_user(
            db_session,
            "coach",
            "p" * 7,
        )


def test_create_user_rejects_password_over_128_characters(
    db_session,
):
    with pytest.raises(
        ValueError,
        match="128 characters or fewer",
    ):
        create_user(
            db_session,
            "coach",
            "p" * 129,
        )


@pytest.mark.parametrize(
    "password_length",
    [8, 128],
)
def test_create_user_allows_password_boundary_lengths(
    db_session,
    password_length,
):
    password = "p" * password_length
    user = create_user(
        db_session,
        f"coach-{password_length}",
        password,
    )

    assert verify_password(
        password,
        user.password_hash,
    )
    assert user.password_hash.startswith("$argon2")


def test_create_user_does_not_trim_password(
    db_session,
):
    password = "  password-with-spaces  "
    user = create_user(
        db_session,
        "coach",
        password,
    )

    assert verify_password(
        password,
        user.password_hash,
    )
    assert not verify_password(
        password.strip(),
        user.password_hash,
    )
