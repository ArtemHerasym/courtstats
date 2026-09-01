import secrets

from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(
    plain_password: str,
    hashed_password: str,
) -> bool:
    return password_hash.verify(
        plain_password,
        hashed_password,
    )


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def csrf_tokens_match(
    expected_token: str | None,
    submitted_token: str | None,
) -> bool:
    if not expected_token or not submitted_token:
        return False

    return secrets.compare_digest(
        expected_token,
        submitted_token,
    )