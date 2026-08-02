from __future__ import annotations
from datetime import date
from enum import Enum as PyEnum

from sqlalchemy import Date, Enum as SQLEnum, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class VenueType(str, PyEnum):
    HOME = "HOME"
    AWAY = "AWAY"
    NEUTRAL = "NEUTRAL"


class GameStatus(str, PyEnum):
    DRAFT = "DRAFT"
    COMPLETED = "COMPLETED"


class Game(TimestampMixin, Base):
    __tablename__ = "games"
    id: Mapped[int] = mapped_column(primary_key=True)

    season_id: Mapped[int] = mapped_column(
        ForeignKey("seasons.id"),
        nullable=False,
    )

    opponent_team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id"),
        nullable=False,
    )

    game_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
    )

    venue_type: Mapped[VenueType] = mapped_column(
        SQLEnum(VenueType, name="venue_type"),
        nullable=False,
    )

    status: Mapped[GameStatus] = mapped_column(
        SQLEnum(GameStatus, name="game_status"),
        nullable=False,
        default=GameStatus.DRAFT,
    )

    opponent_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    season: Mapped["Season"] = relationship(
        back_populates="games",
    )

    opponent_team: Mapped["Team"] = relationship(
        back_populates="opponent_games",
    )

    player_game_stats: Mapped[list["PlayerGameStats"]] = relationship(
        back_populates="game",
    )
