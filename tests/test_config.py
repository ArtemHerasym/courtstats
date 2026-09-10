import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _base_environment(
    monkeypatch,
):
    monkeypatch.delenv(
        "SIGNUP_ACCESS_CODE",
        raising=False,
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        (
            "postgresql+psycopg://"
            "user:password@localhost/"
            "courtstats"
        ),
    )

    monkeypatch.setenv(
        "SESSION_SECRET",
        "x" * 64,
    )


def test_development_allows_non_secure_cookie(
    monkeypatch,
):
    _base_environment(
        monkeypatch,
    )

    monkeypatch.setenv(
        "APP_ENV",
        "development",
    )

    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "false",
    )

    config = Settings(
        _env_file=None,
    )

    assert (
        config.is_production
        is False
    )

    assert (
        config.session_cookie_secure
        is False
    )


def test_production_requires_secure_cookie(
    monkeypatch,
):
    _base_environment(
        monkeypatch,
    )

    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )

    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "false",
    )

    with pytest.raises(
        ValidationError,
        match=(
            "SESSION_COOKIE_SECURE"
        ),
    ):
        Settings(
            _env_file=None,
        )


def test_production_rejects_short_secret(
    monkeypatch,
):
    _base_environment(
        monkeypatch,
    )

    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )

    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "true",
    )

    monkeypatch.setenv(
        "SESSION_SECRET",
        "too-short",
    )

    with pytest.raises(
        ValidationError,
        match="SESSION_SECRET",
    ):
        Settings(
            _env_file=None,
        )


def test_production_rejects_placeholder_secret(
    monkeypatch,
):
    _base_environment(
        monkeypatch,
    )

    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )

    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "true",
    )

    monkeypatch.setenv(
        "SESSION_SECRET",
        (
            "replace_with_a_long_random_secret"
        ),
    )

    with pytest.raises(
        ValidationError,
        match="SESSION_SECRET",
    ):
        Settings(
            _env_file=None,
        )


def test_secure_production_config_is_valid(
    monkeypatch,
):
    _base_environment(
        monkeypatch,
    )

    monkeypatch.setenv(
        "APP_ENV",
        "production",
    )

    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "true",
    )

    config = Settings(
        _env_file=None,
    )

    assert (
        config.is_production
        is True
    )

    assert (
        config.session_cookie_secure
        is True
    )


def test_missing_signup_code_disables_signup(
    monkeypatch,
):
    _base_environment(monkeypatch)
    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "false",
    )

    config = Settings(_env_file=None)

    assert config.signup_access_code is None
    assert config.signup_enabled is False


def test_blank_signup_code_disables_signup(
    monkeypatch,
):
    _base_environment(monkeypatch)
    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "false",
    )
    monkeypatch.setenv(
        "SIGNUP_ACCESS_CODE",
        "   ",
    )

    config = Settings(_env_file=None)

    assert config.signup_enabled is False


def test_configured_signup_code_enables_signup(
    monkeypatch,
):
    _base_environment(monkeypatch)
    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "false",
    )
    monkeypatch.setenv(
        "SIGNUP_ACCESS_CODE",
        "pilot-school-code",
    )

    config = Settings(_env_file=None)

    assert config.signup_enabled is True


def test_production_allows_signup_to_remain_disabled(
    monkeypatch,
):
    _base_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "true",
    )

    config = Settings(_env_file=None)

    assert config.signup_enabled is False


def test_production_accepts_strong_signup_code(
    monkeypatch,
):
    _base_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "true",
    )
    monkeypatch.setenv(
        "SIGNUP_ACCESS_CODE",
        "a-unique-random-school-code-2026",
    )

    config = Settings(_env_file=None)

    assert config.signup_enabled is True


def test_production_rejects_short_signup_code(
    monkeypatch,
):
    _base_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "true",
    )
    monkeypatch.setenv(
        "SIGNUP_ACCESS_CODE",
        "too-short",
    )

    with pytest.raises(
        ValidationError,
        match="SIGNUP_ACCESS_CODE",
    ) as exc_info:
        Settings(_env_file=None)

    assert "too-short" not in str(exc_info.value)


def test_production_rejects_placeholder_signup_code(
    monkeypatch,
):
    _base_environment(monkeypatch)
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "true",
    )
    monkeypatch.setenv(
        "SIGNUP_ACCESS_CODE",
        "replace_with_a_long_random_secret",
    )

    with pytest.raises(
        ValidationError,
        match="SIGNUP_ACCESS_CODE",
    ):
        Settings(_env_file=None)


def test_signup_code_is_hidden_from_settings_repr(
    monkeypatch,
):
    _base_environment(monkeypatch)
    monkeypatch.setenv(
        "SESSION_COOKIE_SECURE",
        "false",
    )
    secret = "private-school-access-code"
    monkeypatch.setenv(
        "SIGNUP_ACCESS_CODE",
        secret,
    )

    config = Settings(_env_file=None)

    assert secret not in repr(config)
