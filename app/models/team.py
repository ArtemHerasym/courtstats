from __future__ import annotations
from sqlalchemy import CheckConstraint, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.mixins import TimestampMixin


class Team(TimestampMixin, Base):
    __tablename__ = 'teams'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    abbreviation: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint(
            "btrim(name) <> ''",
            name="ck_teams_name_not_blank",
        ),
        Index(
            "uq_teams_name_ci",
            func.lower(name),
            unique=True,
        ),
    )

    seasons: Mapped[list["Season"]] = relationship(
        back_populates="team",
    )

    opponent_games: Mapped[list["Game"]] = relationship(
        back_populates="opponent_team",
    )
