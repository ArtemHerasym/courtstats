from app.core.security import (
    generate_csrf_token,
    hash_password,
    verify_signup_access_code,
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


def test_signup_access_code_must_match_exactly():
    configured_code = "school-access-code-value"

    assert verify_signup_access_code(
        configured_code,
        configured_code,
    ) is True
    assert verify_signup_access_code(
        f" {configured_code}",
        configured_code,
    ) is False
    assert verify_signup_access_code(
        "incorrect-code",
        configured_code,
    ) is False
    assert verify_signup_access_code(
        configured_code,
        None,
    ) is False
