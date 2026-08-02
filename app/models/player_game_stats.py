from __future__ import annotations
from enum import Enum as PyEnum

from sqlalchemy import CheckConstraint, Enum as SQLEnum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin

class ParticipationStatus(str, PyEnum):
    PLAYED = "PLAYED"
    DID_NOT_PLAY = "DID_NOT_PLAY"

class PlayerGameStats(TimestampMixin, Base):
    __tablename__ = "player_game_stats"

    id: Mapped[int] = mapped_column(primary_key=True)

    game_id: Mapped[int] = mapped_column(
        ForeignKey("games.id"),
        nullable=False,
    )

    season_roster_id: Mapped[int] = mapped_column(
        ForeignKey("season_rosters.id"),
        nullable=False,
    )
    participation_status: Mapped[ParticipationStatus] = mapped_column(
        SQLEnum(ParticipationStatus, name="participation_status"),
        nullable=False,
    )

    three_point_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    three_point_makes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    two_point_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    two_point_makes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    free_throw_attempts: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    free_throw_makes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    turnovers: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    assists: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    offensive_rebounds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    defensive_rebounds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    steals: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    deflections: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )
    personal_fouls: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
    )

    __table_args__ = (
        UniqueConstraint(
            "game_id",
            "season_roster_id",
            name="uq_player_game_stats_game_roster",
        ),
        CheckConstraint(
            "three_point_makes <= three_point_attempts",
            name="ck_player_game_stats_3pm_lte_3pa",
        ),
        CheckConstraint(
            "two_point_makes <= two_point_attempts",
            name="ck_player_game_stats_2pm_lte_2pa",
        ),
        CheckConstraint(
            "free_throw_makes <= free_throw_attempts",
            name="ck_player_game_stats_ftm_lte_fta",
        ),
        CheckConstraint(
            """
            three_point_attempts >= 0 AND
            three_point_makes >= 0 AND
            two_point_attempts >= 0 AND
            two_point_makes >= 0 AND
            free_throw_attempts >= 0 AND
            free_throw_makes >= 0 AND
            turnovers >= 0 AND
            assists >= 0 AND
            offensive_rebounds >= 0 AND
            defensive_rebounds >= 0 AND
            steals >= 0 AND
            deflections >= 0 AND
            personal_fouls >= 0
            """,
            name="ck_player_game_stats_nonnegative",
        ),
        CheckConstraint(
            """
            participation_status <> 'DID_NOT_PLAY' OR (
                three_point_attempts = 0 AND
                three_point_makes = 0 AND
                two_point_attempts = 0 AND
                two_point_makes = 0 AND
                free_throw_attempts = 0 AND
                free_throw_makes = 0 AND
                turnovers = 0 AND
                assists = 0 AND
                offensive_rebounds = 0 AND
                defensive_rebounds = 0 AND
                steals = 0 AND
                deflections = 0 AND
                personal_fouls = 0
            )
            """,
            name="ck_player_game_stats_dnp_zero_stats",
        ),
    )

    game: Mapped["Game"] = relationship(
        back_populates="player_game_stats",
    )

    season_roster: Mapped["SeasonRoster"] = relationship(
        back_populates="game_stats",
    )
