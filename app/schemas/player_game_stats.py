from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.player_game_stats import ParticipationStatus


class PlayerGameStatsBase(BaseModel):
    participation_status: ParticipationStatus

    three_point_attempts: int = Field(default=0, ge=0)
    three_point_makes: int = Field(default=0, ge=0)
    two_point_attempts: int = Field(default=0, ge=0)
    two_point_makes: int = Field(default=0, ge=0)
    free_throw_attempts: int = Field(default=0, ge=0)
    free_throw_makes: int = Field(default=0, ge=0)

    turnovers: int = Field(default=0, ge=0)
    assists: int = Field(default=0, ge=0)
    offensive_rebounds: int = Field(default=0, ge=0)
    defensive_rebounds: int = Field(default=0, ge=0)
    steals: int = Field(default=0, ge=0)
    deflections: int = Field(default=0, ge=0)
    personal_fouls: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_stat_relationships(self):
        if self.three_point_makes > self.three_point_attempts:
            raise ValueError(
                "Three-point makes cannot exceed three-point attempts"
            )

        if self.two_point_makes > self.two_point_attempts:
            raise ValueError(
                "Two-point makes cannot exceed two-point attempts"
            )

        if self.free_throw_makes > self.free_throw_attempts:
            raise ValueError(
                "Free-throw makes cannot exceed free-throw attempts"
            )

        if self.participation_status == ParticipationStatus.DID_NOT_PLAY:
            raw_stats = (
                self.three_point_attempts,
                self.three_point_makes,
                self.two_point_attempts,
                self.two_point_makes,
                self.free_throw_attempts,
                self.free_throw_makes,
                self.turnovers,
                self.assists,
                self.offensive_rebounds,
                self.defensive_rebounds,
                self.steals,
                self.deflections,
                self.personal_fouls,
            )

            if any(value != 0 for value in raw_stats):
                raise ValueError(
                    "DID_NOT_PLAY requires all statistics to be zero"
                )

        return self


class PlayerGameStatsCreate(PlayerGameStatsBase):
        game_id: int
        season_roster_id: int


class PlayerGameStatsUpdate(BaseModel):
    game_id: int | None = None
    season_roster_id: int | None = None
    participation_status: ParticipationStatus | None = None

    three_point_attempts: int | None = Field(default=None, ge=0)
    three_point_makes: int | None = Field(default=None, ge=0)
    two_point_attempts: int | None = Field(default=None, ge=0)
    two_point_makes: int | None = Field(default=None, ge=0)
    free_throw_attempts: int | None = Field(default=None, ge=0)
    free_throw_makes: int | None = Field(default=None, ge=0)

    turnovers: int | None = Field(default=None, ge=0)
    assists: int | None = Field(default=None, ge=0)
    offensive_rebounds: int | None = Field(default=None, ge=0)
    defensive_rebounds: int | None = Field(default=None, ge=0)
    steals: int | None = Field(default=None, ge=0)
    deflections: int | None = Field(default=None, ge=0)
    personal_fouls: int | None = Field(default=None, ge=0)


class PlayerGameStatsRead(PlayerGameStatsBase):
    id: int
    game_id: int
    season_roster_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
