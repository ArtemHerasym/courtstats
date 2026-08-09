from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.season import Season
from app.schemas.season import SeasonCreate, SeasonUpdate


class SeasonNotFoundError(Exception):
    pass


class SeasonNameConflictError(Exception):
    pass


def create_season(db: Session, season_data: SeasonCreate) -> Season:
    season = Season(**season_data.model_dump())
    existing_season = db.scalar(
        select(Season).where(
            Season.team_id == season_data.team_id,
            Season.name == season_data.name,
        )
    )
    if existing_season is not None:
        raise SeasonNameConflictError(
            "A season with this name already exists for this team."
        )
    try:
        db.add(season)
        db.commit()
        db.refresh(season)
    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "uq_seasons_team_name":
            raise SeasonNameConflictError(
                "A season with this name already exists for this team."
            ) from exc

        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return season

def get_season(db: Session, season_id: int) -> Season:
    season = db.get(Season, season_id)

    if season is None:
        raise SeasonNotFoundError(
            f"Season with ID {season_id} was not found."
        )

    return season

def list_seasons(db: Session) -> list[Season]:
    statement = select(Season).order_by(Season.id)

    return list(db.scalars(statement).all())

def update_season(
        db: Session,
        season_id: int,
        season_data: SeasonUpdate
) -> Season:
    season = get_season(db, season_id)

    update_data = season_data.model_dump(exclude_unset=True)

    final_team_id = update_data.get("team_id", season.team_id)
    final_name = update_data.get("name", season.name)
    final_start_date = update_data.get("start_date", season.start_date)
    final_end_date = update_data.get("end_date", season.end_date)
    final_status = update_data.get("status", season.status)


    if final_team_id is None:
        raise ValueError("Season team_id cannot be None")

    if final_name is None:
        raise ValueError("Season name cannot be None")

    if final_status is None:
        raise ValueError("Season status cannot be None")

    if (
            final_start_date is not None
            and final_end_date is not None
            and final_end_date < final_start_date
    ):
        raise ValueError("End date cannot be earlier than start date")

    existing_season = db.scalar(
        select(Season).where(
            Season.team_id == final_team_id,
            Season.name == final_name,
            Season.id != season.id,
        )
    )

    if existing_season is not None:
        raise SeasonNameConflictError(
            "A season with this name already exists for this team."
        )

    for field, value in update_data.items():
        setattr(season, field, value)

    try:
        db.commit()
        db.refresh(season)
    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "uq_seasons_team_name":
            raise SeasonNameConflictError(
                "A season with this name already exists for this team."
            ) from exc
        raise

    except SQLAlchemyError:
        db.rollback()
        raise



    return season