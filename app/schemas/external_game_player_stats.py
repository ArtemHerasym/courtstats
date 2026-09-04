from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.models.player_game_stats import (
    ParticipationStatus,
)
from app.schemas.player_game_stats import (
    PlayerGameStatsBase,
)


class ExternalGamePlayerStatsBase(
    PlayerGameStatsBase
):
    pass


class ExternalGamePlayerStatsCreate(
    ExternalGamePlayerStatsBase
):
    external_game_id: int
    player_id: int


class ExternalGamePlayerStatsUpdate(BaseModel):
    external_game_id: int | None = None
    player_id: int | None = None
    participation_status: (
        ParticipationStatus | None
    ) = None

    three_point_attempts: int | None = Field(
        default=None,
        ge=0,
    )
    three_point_makes: int | None = Field(
        default=None,
        ge=0,
    )
    two_point_attempts: int | None = Field(
        default=None,
        ge=0,
    )
    two_point_makes: int | None = Field(
        default=None,
        ge=0,
    )
    free_throw_attempts: int | None = Field(
        default=None,
        ge=0,
    )
    free_throw_makes: int | None = Field(
        default=None,
        ge=0,
    )

    turnovers: int | None = Field(
        default=None,
        ge=0,
    )
    assists: int | None = Field(
        default=None,
        ge=0,
    )
    offensive_rebounds: int | None = Field(
        default=None,
        ge=0,
    )
    defensive_rebounds: int | None = Field(
        default=None,
        ge=0,
    )
    steals: int | None = Field(
        default=None,
        ge=0,
    )
    deflections: int | None = Field(
        default=None,
        ge=0,
    )
    personal_fouls: int | None = Field(
        default=None,
        ge=0,
    )


class ExternalGamePlayerStatsRead(
    ExternalGamePlayerStatsBase
):
    id: int
    external_game_id: int
    player_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )