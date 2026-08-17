from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.game import GameStatus, VenueType


class GameBase(BaseModel):
    game_date: date
    venue_type: VenueType
    status: GameStatus = GameStatus.DRAFT
    opponent_score: int | None = Field(default=None, ge=0)
    notes: str | None = None


class GameCreate(GameBase):
    season_id: int
    opponent_team_id: int


class GameUpdate(BaseModel):
    season_id: int | None = None
    opponent_team_id: int | None = None
    game_date: date | None = None
    venue_type: VenueType | None = None
    status: GameStatus | None = None
    opponent_score: int | None = Field(default=None, ge=0)
    notes: str | None = None


class GameRead(GameBase):
    id: int
    season_id: int
    opponent_team_id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)