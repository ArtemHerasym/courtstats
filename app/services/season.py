from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)
from sqlalchemy.orm import Session

from app.models.season import Season
from app.models.team import Team
from app.schemas.season import (
    SeasonCreate,
    SeasonUpdate,
)
from app.schemas.team import TeamCreate
from app.services.team import (
    TeamNameConflictError,
    find_team_by_name,
)


class SeasonNotFoundError(Exception):
    pass


class SeasonNameConflictError(Exception):
    pass


def _ensure_season_name_available(
    db: Session,
    team_id: int,
    name: str,
    *,
    exclude_season_id: int | None = None,
) -> None:
    statement = select(Season).where(
        Season.team_id == team_id,
        Season.name == name,
    )

    if exclude_season_id is not None:
        statement = statement.where(
            Season.id != exclude_season_id
        )

    existing_season = db.scalar(
        statement
    )

    if existing_season is not None:
        raise SeasonNameConflictError(
            (
                "A seasons with this name "
                "already exists for this team."
            )
        )


def _raise_known_season_integrity_error(
    exc: IntegrityError,
) -> None:
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
        == "uq_seasons_team_name"
    ):
        raise SeasonNameConflictError(
            (
                "A seasons with this name "
                "already exists for this team."
            )
        ) from exc

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

    raise exc


def create_season(
    db: Session,
    season_data: SeasonCreate,
) -> Season:
    _ensure_season_name_available(
        db,
        season_data.team_id,
        season_data.name,
    )

    season = Season(
        **season_data.model_dump()
    )

    try:
        db.add(season)
        db.commit()
        db.refresh(season)

    except IntegrityError as exc:
        db.rollback()

        _raise_known_season_integrity_error(
            exc
        )

    except SQLAlchemyError:
        db.rollback()
        raise

    return season


def create_season_for_team_name(
    db: Session,
    *,
    team_name: str,
    season_name: str,
    start_date: date | None = None,
    end_date: date | None = None,
) -> Season:
    normalized_team_name = (
        TeamCreate(
            name=team_name,
        ).name
    )

    existing_team = find_team_by_name(
        db,
        normalized_team_name,
    )

    try:
        if existing_team is None:
            team = Team(
                name=normalized_team_name,
                abbreviation=None,
            )

            db.add(team)

            # Obtain the Team ID without
            # committing the transaction.
            db.flush()

        else:
            team = existing_team

        season_data = SeasonCreate(
            team_id=team.id,
            name=season_name,
            start_date=start_date,
            end_date=end_date,
        )

        _ensure_season_name_available(
            db,
            team.id,
            season_data.name,
        )

        season = Season(
            **season_data.model_dump()
        )

        db.add(season)

        # Team and Season commit together.
        db.commit()
        db.refresh(season)

    except IntegrityError as exc:
        db.rollback()

        _raise_known_season_integrity_error(
            exc
        )

    except Exception:
        db.rollback()
        raise

    return season


def get_season(
    db: Session,
    season_id: int,
) -> Season:
    season = db.get(
        Season,
        season_id,
    )

    if season is None:
        raise SeasonNotFoundError(
            (
                f"Season with ID {season_id} "
                "was not found."
            )
        )

    return season


def list_seasons(
    db: Session,
) -> list[Season]:
    statement = select(
        Season
    ).order_by(
        Season.id
    )

    return list(
        db.scalars(statement).all()
    )


def update_season(
    db: Session,
    season_id: int,
    season_data: SeasonUpdate,
) -> Season:
    season = get_season(
        db,
        season_id,
    )

    update_data = (
        season_data.model_dump(
            exclude_unset=True
        )
    )

    final_team_id = update_data.get(
        "team_id",
        season.team_id,
    )

    final_name = update_data.get(
        "name",
        season.name,
    )

    final_start_date = update_data.get(
        "start_date",
        season.start_date,
    )

    final_end_date = update_data.get(
        "end_date",
        season.end_date,
    )

    final_status = update_data.get(
        "status",
        season.status,
    )

    if final_team_id is None:
        raise ValueError(
            "Season team_id cannot be None"
        )

    if final_name is None:
        raise ValueError(
            "Season name cannot be None"
        )

    if final_status is None:
        raise ValueError(
            "Season status cannot be None"
        )

    if (
        final_start_date is not None
        and final_end_date is not None
        and final_end_date
        < final_start_date
    ):
        raise ValueError(
            (
                "End date cannot be earlier "
                "than start date"
            )
        )

    _ensure_season_name_available(
        db,
        final_team_id,
        final_name,
        exclude_season_id=season.id,
    )

    for field, value in (
        update_data.items()
    ):
        setattr(
            season,
            field,
            value,
        )

    try:
        db.commit()
        db.refresh(season)

    except IntegrityError as exc:
        db.rollback()

        _raise_known_season_integrity_error(
            exc
        )

    except SQLAlchemyError:
        db.rollback()
        raise

    return season