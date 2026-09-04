from __future__ import annotations

from datetime import date

from sqlalchemy import (
    CheckConstraint,
    Date,
    Enum as SQLEnum,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.game import GameStatus, VenueType
from app.models.mixins import TimestampMixin


class ExternalGame(TimestampMixin, Base):
    __tablename__ = "external_games"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )

    name: Mapped[str] = mapped_column(
        String,
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
        SQLEnum(
            VenueType,
            name="venue_type",
        ),
        nullable=False,
    )

    opponent_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    status: Mapped[GameStatus] = mapped_column(
        SQLEnum(
            GameStatus,
            name="game_status",
        ),
        nullable=False,
        default=GameStatus.DRAFT,
    )

    notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_external_games_name_not_blank",
        ),
        CheckConstraint(
            (
                "opponent_score IS NULL "
                "OR opponent_score >= 0"
            ),
            name="ck_external_games_opponent_score_nonnegative",
        ),
    )

    opponent_team: Mapped["Team"] = relationship()

    player_stats: Mapped[
        list["ExternalGamePlayerStats"]
    ] = relationship(
        back_populates="external_game",
    )