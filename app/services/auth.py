from sqlalchemy import func, select
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)
from sqlalchemy.orm import Session

from app.core.security import (
    hash_password,
    verify_password,
)
from app.models.user import User


class UserAlreadyExistsError(Exception):
    pass


def get_user_by_username(
    db: Session,
    username: str,
) -> User | None:
    return db.scalar(
        select(User).where(
            func.lower(User.username)
            == username.strip().lower()
        )
    )


def create_user(
    db: Session,
    username: str,
    password: str,
) -> User:
    normalized_username = (
        username.strip()
    )

    if not normalized_username:
        raise ValueError(
            "Username cannot be empty."
        )

    if not password:
        raise ValueError(
            "Password cannot be empty."
        )

    existing_user = (
        get_user_by_username(
            db,
            normalized_username,
        )
    )

    if existing_user is not None:
        raise UserAlreadyExistsError(
            "A user with this username "
            "already exists."
        )

    user = User(
        username=normalized_username,
        password_hash=hash_password(
            password
        ),
        is_active=True,
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)

    except IntegrityError as exc:
        db.rollback()

        raise UserAlreadyExistsError(
            "A user with this username "
            "already exists."
        ) from exc

    except SQLAlchemyError:
        db.rollback()
        raise

    return user


def authenticate_user(
    db: Session,
    username: str,
    password: str,
) -> User | None:
    user = get_user_by_username(
        db,
        username,
    )

    if user is None:
        return None

    if not user.is_active:
        return None

    if not verify_password(
        password,
        user.password_hash,
    ):
        return None

    return user