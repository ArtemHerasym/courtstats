import pytest
from pydantic import ValidationError

from app.core.config import Settings


def _base_environment(
    monkeypatch,
):
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
