from sqlalchemy import func, select
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)
from sqlalchemy.orm import Session

from app.models.team import Team
from app.schemas.team import TeamCreate


class TeamNameConflictError(Exception):
    pass


def _normalize_team_name(
    name: str,
) -> str:
    normalized_name = name.strip()

    if not normalized_name:
        raise ValueError(
            "Team name cannot be blank"
        )

    return normalized_name


def find_team_by_name(
    db: Session,
    name: str,
) -> Team | None:
    normalized_name = _normalize_team_name(
        name
    )

    statement = select(Team).where(
        func.lower(Team.name)
        == normalized_name.lower()
    )

    return db.scalar(statement)


def create_team(
    db: Session,
    team_data: TeamCreate,
) -> Team:
    existing_team = find_team_by_name(
        db,
        team_data.name,
    )

    if existing_team is not None:
        raise TeamNameConflictError(
            "A team with this name already exists."
        )

    team = Team(
        **team_data.model_dump()
    )

    try:
        db.add(team)
        db.commit()
        db.refresh(team)

    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(
                exc.orig,
                "diag",
                None,
            ),
            "constraint_name",
            None,
        )

        if (
            constraint_name
            == "uq_teams_name_ci"
        ):
            raise TeamNameConflictError(
                (
                    "A team with this name "
                    "already exists."
                )
            ) from exc

        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return team


def list_teams(
    db: Session,
) -> list[Team]:
    statement = select(Team).order_by(
        func.lower(Team.name),
        Team.id,
    )

    return list(
        db.scalars(statement).all()
    )