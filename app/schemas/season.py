from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.models.season import SeasonStatus


class SeasonBase(BaseModel):
    name: str
    start_date: date | None = None
    end_date: date | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Season name cannot be empty")
        return value.strip()

    @model_validator(mode="after")
    def validate_date_range(self):
        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("End date cannot be earlier than start date")

        return self

class SeasonCreate(SeasonBase):
    team_id: int

class SeasonUpdate(BaseModel):
    team_id: int | None = None
    name: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    status: SeasonStatus | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None

        if not value.strip():
            raise ValueError("Season name cannot be empty")

        return value.strip()

    @model_validator(mode="after")
    def validate_date_range(self):

        if (
            self.start_date is not None
            and self.end_date is not None
            and self.end_date < self.start_date
        ):
            raise ValueError("End date cannot be earlier than start date")

        return self

class SeasonRead(SeasonBase):
    id: int
    team_id: int
    status: SeasonStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)