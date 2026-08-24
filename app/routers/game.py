from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.game import GameCreate, GameRead, GameUpdate
from app.services.game import (
    GameNotFoundError,
    GameOpponentConflictError,
    GameSeasonStatsConflictError,
    OpponentTeamNotFoundError,
    create_game,
    get_game,
    list_games,
    update_game,
)
from app.services.season import SeasonNotFoundError


router = APIRouter(
    prefix="/games",
    tags=["games"],
)


@router.post(
    "",
    response_model=GameRead,
    status_code=status.HTTP_201_CREATED,
)
def create_game_route(
    game_data: GameCreate,
    db: Session = Depends(get_db),
):
    try:
        return create_game(db, game_data)

    except (
        SeasonNotFoundError,
        OpponentTeamNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except GameOpponentConflictError as exc:
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
    response_model=list[GameRead],
    status_code=status.HTTP_200_OK,
)
def list_games_route(
    db: Session = Depends(get_db),
):
    return list_games(db)


@router.get(
    "/{game_id}",
    response_model=GameRead,
)
def get_game_route(
        game_id: int,
        db: Session = Depends(get_db),
):
    try:
        return get_game(db, game_id)
    except GameNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{game_id}",
    response_model=GameRead,
)
def update_game_route(
        game_id: int,
        game_data: GameUpdate,
        db: Session = Depends(get_db),
):
    try:
        return update_game(db, game_id, game_data)
    except (
        GameNotFoundError,
        SeasonNotFoundError,
        OpponentTeamNotFoundError,
    ) as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


    except (
            GameOpponentConflictError,
            GameSeasonStatsConflictError,
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