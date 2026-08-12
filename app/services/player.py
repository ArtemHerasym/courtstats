from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.player import Player
from app.schemas.player import PlayerCreate, PlayerUpdate

class PlayerNotFoundError(Exception):
    pass

def create_player(db: Session, player_data: PlayerCreate) -> Player:
    player = Player(**player_data.model_dump())

    try:
        db.add(player)
        db.commit()
        db.refresh(player)
    except SQLAlchemyError:
        db.rollback()
        raise

    return player

def get_player(db: Session, player_id: int) -> Player:
    player = db.get(Player, player_id)

    if player is None:
        raise PlayerNotFoundError(
            f"Player with ID {player_id} was not found."
        )

    return player

def list_players(db: Session) -> list[Player]:
    statement = select(Player).order_by(Player.id)

    return list(db.scalars(statement).all())

def update_player(
        db: Session,
        player_id: int,
        player_data: PlayerUpdate,
) -> Player:
    player = get_player(db, player_id)

    update_data = player_data.model_dump(exclude_unset=True)

    final_full_name = update_data.get("full_name", player.full_name)

    if final_full_name is None:
        raise ValueError("Player full_name cannot be None")

    for field, value in update_data.items():
        setattr(player, field, value)

    try:
        db.commit()
        db.refresh(player)
    except SQLAlchemyError:
        db.rollback()
        raise

    return player