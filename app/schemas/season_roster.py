from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.season_roster import RosterStatus


class SeasonRosterBase(BaseModel):
    jersey_number: int | None = None
    position: str | None = None
    grade_level: str | None = None
    status: RosterStatus = RosterStatus.ACTIVE

    @field_validator("position", "grade_level")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not value.strip():
            raise ValueError("Value cannot be empty")

        return value.strip()


class SeasonRosterCreate(SeasonRosterBase):
    season_id: int
    player_id: int


class SeasonRosterUpdate(BaseModel):
    season_id: int | None = None
    player_id: int | None = None
    jersey_number: int | None = None
    position: str | None = None
    grade_level: str | None = None
    status: RosterStatus | None = None

    @field_validator("position", "grade_level")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not value.strip():
            raise ValueError("Value cannot be empty")

        return value.strip()


class SeasonRosterRead(SeasonRosterBase):
    id: int
    season_id: int
    player_id: int
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)