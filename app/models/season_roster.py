from __future__ import annotations
from enum import Enum as PyEnum

from sqlalchemy import Enum as SQLEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class RosterStatus(str, PyEnum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    LEFT_TEAM = "LEFT_TEAM"


class SeasonRoster(TimestampMixin, Base):
    __tablename__ = "season_rosters"
    id: Mapped[int] = mapped_column(primary_key=True)
    season_id: Mapped[int] = mapped_column(ForeignKey("seasons.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    jersey_number: Mapped[int | None] = mapped_column(nullable=True)
    position: Mapped[str | None] = mapped_column(String, nullable=True)
    grade_level: Mapped[str | None] = mapped_column(String, nullable=True)

    status: Mapped[RosterStatus] = mapped_column(
        SQLEnum(RosterStatus, name="roster_status"),
        nullable=False,
        default=RosterStatus.ACTIVE,
    )

    __table_args__ = (
        UniqueConstraint(
            "season_id",
            "player_id",
            name="uq_season_rosters_season_player",
        ),
    )

    season: Mapped["Season"] = relationship(
        back_populates="season_rosters",
    )

    player: Mapped["Player"] = relationship(
        back_populates="season_rosters",
    )

    game_stats: Mapped[list["PlayerGameStats"]] = relationship(
        back_populates="season_roster",
    )
