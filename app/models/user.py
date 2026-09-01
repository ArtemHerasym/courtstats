from sqlalchemy import Boolean, CheckConstraint, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.mixins import TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
    )
    username: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    password_hash: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
    )

    __table_args__ = (
        CheckConstraint(
            "btrim(username) <> ''",
            name="ck_users_username_not_blank",
        ),
        Index(
            "uq_users_username_ci",
            func.lower(username),
            unique=True,
        ),
    )