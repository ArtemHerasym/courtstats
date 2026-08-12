from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class PlayerBase(BaseModel):
    full_name: str
    display_name: str | None = None

    @field_validator('full_name')
    @classmethod
    def validate_full_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Player full name cannot be empty")

        return value.strip()

    @field_validator('display_name')
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not value.strip():
            raise ValueError("Player display name cannot be empty")

        return value.strip()


class PlayerCreate(PlayerBase):
    pass


class PlayerUpdate(BaseModel):
    full_name: str | None = None
    display_name: str | None = None

    @field_validator("full_name")
    @classmethod
    def validate_full_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not value.strip():
            raise ValueError("Player full name cannot be empty")

        return value.strip()

    @field_validator("display_name")
    @classmethod
    def validate_display_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not value.strip():
            raise ValueError("Player display name cannot be empty")

        return value.strip()


class PlayerRead(PlayerBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
