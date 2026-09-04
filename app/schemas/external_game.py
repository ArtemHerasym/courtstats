from datetime import date, datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)

from app.models.game import (
    GameStatus,
    VenueType,
)


class ExternalGameBase(BaseModel):
    name: str
    game_date: date
    venue_type: VenueType
    opponent_score: int | None = Field(
        default=None,
        ge=0,
    )
    status: GameStatus = GameStatus.DRAFT
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str,
    ) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "External game name cannot be blank"
            )

        return value


class ExternalGameCreate(ExternalGameBase):
    opponent_team_id: int


class ExternalGameUpdate(BaseModel):
    name: str | None = None
    opponent_team_id: int | None = None
    game_date: date | None = None
    venue_type: VenueType | None = None
    opponent_score: int | None = Field(
        default=None,
        ge=0,
    )
    status: GameStatus | None = None
    notes: str | None = None

    @field_validator("name")
    @classmethod
    def validate_name(
        cls,
        value: str | None,
    ) -> str | None:
        if value is None:
            return None

        value = value.strip()

        if not value:
            raise ValueError(
                "External game name cannot be blank"
            )

        return value


class ExternalGameRead(ExternalGameBase):
    id: int
    opponent_team_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )