from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.dependencies import get_db
from app.schemas.player import PlayerCreate, PlayerRead, PlayerUpdate
from app.services.player import (
    PlayerNotFoundError,
    create_player,
    get_player,
    list_players,
    update_player,
)

router = APIRouter(
    prefix="/players",
    tags=["players"],
)


@router.post(
    "",
    response_model=PlayerRead,
    status_code=status.HTTP_201_CREATED,
)
def create_player_route(
        player_data: PlayerCreate,
        db: Session = Depends(get_db),
):
    return create_player(db, player_data)


@router.get(
    "",
    response_model=list[PlayerRead],
)
def list_players_route(
        db: Session = Depends(get_db),
):
    return list_players(db)


@router.get(
    "/{player_id}",
    response_model=PlayerRead,
)
def get_player_route(
        player_id: int,
        db: Session = Depends(get_db),
):
    try:
        return get_player(db, player_id)
    except PlayerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{player_id}",
    response_model=PlayerRead,
)
def update_player_route(
        player_id: int,
        player_data: PlayerUpdate,
        db: Session = Depends(get_db),
):
    try:
        return update_player(db, player_id, player_data)
    except PlayerNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(exc),
        ) from exc
