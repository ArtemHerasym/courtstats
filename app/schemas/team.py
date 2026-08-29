from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator


class TeamCreate(BaseModel):
    name: str
    abbreviation: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("Team name cannot be blank")

        return value

    @field_validator("abbreviation")
    @classmethod
    def normalize_abbreviation(cls, value: str | None) -> str | None:
        if value is None:
            return None

        value = value.strip()

        return value or None


class TeamRead(BaseModel):
    id: int
    name: str
    abbreviation: str | None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)