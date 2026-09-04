from typing import Literal

from pydantic import (
    Field,
    model_validator,
)
from pydantic_settings import (
    BaseSettings,
    SettingsConfigDict,
)


class Settings(BaseSettings):
    database_url: str = Field(
        validation_alias="DATABASE_URL",
    )

    test_database_url: str | None = Field(
        default=None,
        validation_alias="TEST_DATABASE_URL",
    )

    app_env: Literal[
        "development",
        "production",
    ] = Field(
        default="development",
        validation_alias="APP_ENV",
    )

    session_secret: str = Field(
        validation_alias="SESSION_SECRET",
    )

    session_cookie_secure: bool = Field(
        validation_alias=(
            "SESSION_COOKIE_SECURE"
        ),
    )

    @property
    def is_production(self) -> bool:
        return (
            self.app_env
            == "production"
        )

    @model_validator(mode="after")
    def validate_production_security(
        self,
    ):
        if not self.is_production:
            return self

        insecure_secrets = {
            "replace_with_a_long_random_secret",
            "changeme",
            "change-me",
        }

        if (
            len(self.session_secret) < 32
            or self.session_secret
            in insecure_secrets
        ):
            raise ValueError(
                "Production SESSION_SECRET "
                "must be at least 32 characters "
                "and must not use a placeholder."
            )

        if not self.session_cookie_secure:
            raise ValueError(
                "SESSION_COOKIE_SECURE must "
                "be true in production."
            )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()