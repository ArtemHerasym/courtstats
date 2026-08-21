from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.player_game_stats import (
    PlayerGameStatsCreate,
    PlayerGameStatsRead,
    PlayerGameStatsUpdate,
)
from app.services.game import GameNotFoundError
from app.services.player_game_stats import (
    PlayerGameStatsConflictError,
    PlayerGameStatsNotFoundError,
    PlayerGameStatsSeasonMismatchError,
    create_player_game_stats,
    get_player_game_stats,
    list_player_game_stats,
    update_player_game_stats,
)
from app.services.season_roster import SeasonRosterNotFoundError


router = APIRouter(
    prefix="/player-game-stats",
    tags=["player-game-stats"],
)


@router.post(
    "",
    response_model=PlayerGameStatsRead,
    status_code=status.HTTP_201_CREATED,
)
def create_player_game_stats_route(
    stats_data: PlayerGameStatsCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_player_game_stats(
            db,
            stats_data,
        )

    except (
        GameNotFoundError,
        SeasonRosterNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (
        PlayerGameStatsSeasonMismatchError,
        PlayerGameStatsConflictError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc


@router.get(
    "",
    response_model=list[PlayerGameStatsRead],
    status_code=status.HTTP_200_OK,
)
def list_player_game_stats_route(
    db: Session = Depends(get_db),
):
    return list_player_game_stats(db)


@router.get(
    "/{stats_id}",
    response_model=PlayerGameStatsRead,
    status_code=status.HTTP_200_OK,
)
def get_player_game_stats_route(
    stats_id: int,
    db: Session = Depends(get_db),
):
    try:
        return get_player_game_stats(
            db,
            stats_id,
        )

    except PlayerGameStatsNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{stats_id}",
    response_model=PlayerGameStatsRead,
    status_code=status.HTTP_200_OK,
)
def update_player_game_stats_route(
    stats_id: int,
    stats_data: PlayerGameStatsUpdate,
    db: Session = Depends(get_db),
):
    try:
        return update_player_game_stats(
            db,
            stats_id,
            stats_data,
        )

    except (
        PlayerGameStatsNotFoundError,
        GameNotFoundError,
        SeasonRosterNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except (
        PlayerGameStatsSeasonMismatchError,
        PlayerGameStatsConflictError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc