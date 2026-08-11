from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.season import SeasonCreate, SeasonRead, SeasonUpdate
from app.services.season import (
    SeasonNameConflictError,
    SeasonNotFoundError,
    create_season,
    get_season,
    list_seasons,
    update_season,
)


router = APIRouter(
    prefix="/seasons",
    tags=["seasons"],
)


@router.post(
    "",
    response_model=SeasonRead,
    status_code=status.HTTP_201_CREATED,
)
def create_season_route(
        season_data: SeasonCreate,
        db: Session = Depends(get_db),
):
    try:
        return create_season(db, season_data)
    except SeasonNameConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

@router.get(
    "",
    response_model=list[SeasonRead],
)
def list_seasons_route(
        db: Session = Depends(get_db),
):
    return list_seasons(db)

@router.get(
    "/{season_id}",
    response_model=SeasonRead,
)
def get_season_route(
        season_id: int,
        db: Session = Depends(get_db),
):
    try:
        return get_season(db, season_id)
    except SeasonNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

@router.patch(
    "/{season_id}",
    response_model=SeasonRead,
)
def update_season_route(
    season_id: int,
    season_data: SeasonUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_season(db, season_id, season_data)
    except SeasonNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except SeasonNameConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc