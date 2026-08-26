from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.statistics import (
    GameStatisticsRead,
    PlayerSeasonStatisticsRead,
    TeamSeasonStatisticsRead,
)
from app.services.game import GameNotFoundError
from app.services.season import SeasonNotFoundError
from app.services.season_roster import SeasonRosterNotFoundError
from app.services.statistics import (
    calculate_player_season_summary,
    calculate_team_season_summary,
    get_game_statistics,
)


router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
)


@router.get(
    "/games/{game_id}",
    response_model=GameStatisticsRead,
    status_code=status.HTTP_200_OK,
)
def get_game_statistics_route(
    game_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_game_statistics(
            db,
            game_id,
        )

    except GameNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get(
    "/season-rosters/{season_roster_id}",
    response_model=PlayerSeasonStatisticsRead,
    status_code=status.HTTP_200_OK,
)
def get_player_season_statistics_route(
    season_roster_id: int,
    db: Session = Depends(get_db),
):
    try:
        return calculate_player_season_summary(
            db,
            season_roster_id,
        )

    except SeasonRosterNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.get(
    "/seasons/{season_id}",
    response_model=TeamSeasonStatisticsRead,
    status_code=status.HTTP_200_OK,
)
def get_team_season_statistics_route(
    season_id: int,
    db: Session = Depends(get_db),
):
    try:
        return calculate_team_season_summary(
            db,
            season_id,
        )

    except SeasonNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc