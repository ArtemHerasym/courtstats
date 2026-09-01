from app.core.security import (
    generate_csrf_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_not_plaintext():
    password = "secure-test-password"

    hashed = hash_password(password)

    assert hashed != password


def test_correct_password_verifies():
    password = "secure-test-password"
    hashed = hash_password(password)

    assert verify_password(
        password,
        hashed,
    ) is True


def test_incorrect_password_fails():
    hashed = hash_password(
        "correct-password"
    )

    assert verify_password(
        "wrong-password",
        hashed,
    ) is False


def test_csrf_tokens_are_random():
    first = generate_csrf_token()
    second = generate_csrf_token()

    assert first
    assert second
    assert first != second