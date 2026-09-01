from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = Field(validation_alias="DATABASE_URL")

    test_database_url: str | None = Field(
        default=None,
        validation_alias="TEST_DATABASE_URL",
    )

    session_secret: str = Field(
        validation_alias="SESSION_SECRET",
    )

    session_cookie_secure: bool = Field(
        validation_alias="SESSION_COOKIE_SECURE",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()