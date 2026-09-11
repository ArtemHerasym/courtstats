from typing import Literal

from pydantic import (
    Field,
    SecretStr,
    field_validator,
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

    signup_access_code: SecretStr | None = Field(
        default=None,
        validation_alias="SIGNUP_ACCESS_CODE",
    )

    @field_validator(
        "database_url",
        "test_database_url",
        mode="before",
    )
    @classmethod
    def normalize_postgresql_driver(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        if value.startswith(
            "postgres://"
        ):
            return (
                "postgresql+psycopg://"
                + value.removeprefix(
                    "postgres://"
                )
            )

        if value.startswith(
            "postgresql://"
        ):
            return (
                "postgresql+psycopg://"
                + value.removeprefix(
                    "postgresql://"
                )
            )

        return value

    @property
    def is_production(self) -> bool:
        return (
            self.app_env
            == "production"
        )

    @property
    def signup_enabled(self) -> bool:
        if self.signup_access_code is None:
            return False

        return bool(
            self.signup_access_code
            .get_secret_value()
            .strip()
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

        if self.signup_enabled:
            signup_access_code = (
                self.signup_access_code
                .get_secret_value()
            )
            signup_placeholders = {
                "changeme",
                "change-me",
                "replace-me",
                "signup-code",
                "school-access-code",
                (
                    "replace_with_a_long_"
                    "random_secret"
                ),
            }

            if (
                len(signup_access_code) < 24
                or signup_access_code.strip().lower()
                in signup_placeholders
            ):
                raise ValueError(
                    "Production SIGNUP_ACCESS_CODE "
                    "must be at least 24 characters "
                    "and must not use a placeholder."
                )

        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        hide_input_in_errors=True,
    )


settings = Settings()
