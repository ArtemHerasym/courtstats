from __future__ import annotations
from datetime import date
from enum import Enum as PyEnum

from sqlalchemy import Date, Enum as SQLEnum, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class SeasonStatus(str, PyEnum):
    SETUP = 'SETUP'
    ACTIVE = 'ACTIVE'
    COMPLETED = 'COMPLETED'


class Season(TimestampMixin, Base):
    __tablename__ = "seasons"
    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    name: Mapped[str] = mapped_column(String, nullable=False)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[SeasonStatus] = mapped_column(
        SQLEnum(SeasonStatus, name="season_status"),
        nullable=False,
        default=SeasonStatus.SETUP,
    )

    __table_args__ = (
        UniqueConstraint(
            "team_id",
            "name",
            name="uq_seasons_team_name",
        ),
    )

    team: Mapped["Team"] = relationship(
        back_populates="seasons",
    )

    season_rosters: Mapped[list["SeasonRoster"]] = relationship(
        back_populates="season",
    )

    games: Mapped[list["Game"]] = relationship(
        back_populates="season",
    )
