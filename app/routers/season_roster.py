from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.season_roster import (
    SeasonRosterCreate,
    SeasonRosterRead,
    SeasonRosterUpdate,
)
from app.services.player import PlayerNotFoundError
from app.services.season import SeasonNotFoundError
from app.services.season_roster import (
    SeasonRosterJerseyConflictError,
    SeasonRosterMembershipConflictError,
    SeasonRosterNotFoundError,
    create_season_roster,
    get_season_roster,
    list_season_rosters,
    update_season_roster,
)


router = APIRouter(
    prefix="/season-rosters",
    tags=["season-rosters"],
)


@router.post(
    "",
    response_model=SeasonRosterRead,
    status_code=status.HTTP_201_CREATED,
)
def create_season_roster_route(
    roster_data: SeasonRosterCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_season_roster(db, roster_data)

    except (SeasonNotFoundError, PlayerNotFoundError) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    except (
        SeasonRosterMembershipConflictError,
        SeasonRosterJerseyConflictError,
    ) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e


@router.get(
    "",
    response_model=list[SeasonRosterRead],
)
def list_season_rosters_route(
    db: Session = Depends(get_db),
):
    return list_season_rosters(db)


@router.get(
    "/{roster_id}",
    response_model=SeasonRosterRead,
)
def get_season_roster_route(
    roster_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_season_roster(db, roster_id)

    except SeasonRosterNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e


@router.patch(
    "/{roster_id}",
    response_model=SeasonRosterRead,
)
def update_season_roster_route(
    roster_id: int,
    roster_data: SeasonRosterUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_season_roster(
            db,
            roster_id,
            roster_data,
        )

    except (
        SeasonRosterNotFoundError,
        SeasonNotFoundError,
        PlayerNotFoundError,
    ) as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        ) from e

    except (
        SeasonRosterMembershipConflictError,
        SeasonRosterJerseyConflictError,
    ) as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(e),
        ) from e

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(e),
        ) from e