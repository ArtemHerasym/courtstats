from sqlalchemy import delete, func, or_, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.game import Game, GameStatus
from app.models.external_game import ExternalGame
from app.models.external_game_player_stats import ExternalGamePlayerStats
from app.models.player_game_stats import ParticipationStatus, PlayerGameStats
from app.models.season_roster import SeasonRoster
from app.schemas.player import (
    PlayerCreate,
    PlayerUpdate,
)


class PlayerNotFoundError(Exception):
    pass


class PlayerDeletionConflictError(Exception):
    pass


PLAYER_DELETION_CONFLICT_MESSAGE = (
    "Player cannot be deleted because they are the only PLAYED participant "
    "in a completed game. Correct or delete that game first."
)


def delete_player(db: Session, player_id: int) -> None:
    """Validate completed games before removing any of a player's history."""
    try:
        with db.no_autoflush:
            player = get_player(db, player_id)
            roster_ids = select(SeasonRoster.id).where(SeasonRoster.player_id == player_id)
            played_game_ids = select(PlayerGameStats.game_id).where(
                PlayerGameStats.season_roster_id.in_(roster_ids),
                PlayerGameStats.participation_status == ParticipationStatus.PLAYED,
            )
            # Lock shared game rows in a stable order so simultaneous player
            # deletions cannot both count a participant the other removes.
            games = db.scalars(select(Game).where(Game.id.in_(played_game_ids))
                               .order_by(Game.id).with_for_update()
                               .execution_options(populate_existing=True)).all()
            for game in games:
                if game.status != GameStatus.COMPLETED:
                    continue
                other_played = db.scalar(select(PlayerGameStats.id).where(
                    PlayerGameStats.game_id == game.id,
                    PlayerGameStats.season_roster_id.not_in(roster_ids),
                    PlayerGameStats.participation_status == ParticipationStatus.PLAYED,
                ).limit(1))
                if other_played is None:
                    raise PlayerDeletionConflictError(PLAYER_DELETION_CONFLICT_MESSAGE)

            played_external_ids = select(ExternalGamePlayerStats.external_game_id).where(
                ExternalGamePlayerStats.player_id == player_id,
                ExternalGamePlayerStats.participation_status == ParticipationStatus.PLAYED,
            )
            external_games = db.scalars(select(ExternalGame).where(
                ExternalGame.id.in_(played_external_ids),
            ).order_by(ExternalGame.id).with_for_update()
              .execution_options(populate_existing=True)).all()
            for game in external_games:
                if game.status != GameStatus.COMPLETED:
                    continue
                other_played = db.scalar(select(ExternalGamePlayerStats.id).where(
                    ExternalGamePlayerStats.external_game_id == game.id,
                    ExternalGamePlayerStats.player_id != player_id,
                    ExternalGamePlayerStats.participation_status == ParticipationStatus.PLAYED,
                ).limit(1))
                if other_played is None:
                    raise PlayerDeletionConflictError(PLAYER_DELETION_CONFLICT_MESSAGE)

        db.execute(delete(PlayerGameStats).where(PlayerGameStats.season_roster_id.in_(roster_ids)))
        db.execute(delete(ExternalGamePlayerStats).where(ExternalGamePlayerStats.player_id == player_id))
        db.execute(delete(SeasonRoster).where(SeasonRoster.player_id == player_id))
        db.expire(player, ["season_rosters"])
        db.delete(player)
        db.commit()
    except (SQLAlchemyError, PlayerDeletionConflictError):
        db.rollback()
        raise


def create_player(
    db: Session,
    player_data: PlayerCreate,
) -> Player:
    player = Player(
        **player_data.model_dump()
    )

    try:
        db.add(player)
        db.commit()
        db.refresh(player)

    except SQLAlchemyError:
        db.rollback()
        raise

    return player


def create_players(
    db: Session,
    players_data: list[PlayerCreate],
) -> list[Player]:
    if not players_data:
        return []

    players = [
        Player(
            **player_data.model_dump()
        )
        for player_data in players_data
    ]

    try:
        db.add_all(players)
        db.commit()

        for player in players:
            db.refresh(player)

    except Exception:
        db.rollback()
        raise

    return players


def get_player(
    db: Session,
    player_id: int,
) -> Player:
    player = db.get(
        Player,
        player_id,
    )

    if player is None:
        raise PlayerNotFoundError(
            (
                f"Player with ID {player_id} "
                "was not found."
            )
        )

    return player


def list_players(
    db: Session,
) -> list[Player]:
    statement = select(
        Player
    ).order_by(
        Player.id
    )

    return list(
        db.scalars(statement).all()
    )


def search_players(
    db: Session,
    query: str,
) -> list[Player]:
    normalized_query = query.strip()

    if not normalized_query:
        return []

    search_value = normalized_query.lower()

    statement = (
        select(Player)
        .where(
            or_(
                func.lower(
                    Player.full_name
                ).contains(
                    search_value,
                    autoescape=True,
                ),
                func.lower(
                    Player.display_name
                ).contains(
                    search_value,
                    autoescape=True,
                ),
            )
        )
        .order_by(
            func.lower(
                Player.full_name
            ),
            Player.id,
        )
    )

    return list(
        db.scalars(statement).all()
    )


def update_player(
    db: Session,
    player_id: int,
    player_data: PlayerUpdate,
) -> Player:
    player = get_player(
        db,
        player_id,
    )

    update_data = (
        player_data.model_dump(
            exclude_unset=True
        )
    )

    final_full_name = update_data.get(
        "full_name",
        player.full_name,
    )

    if final_full_name is None:
        raise ValueError(
            "Player full_name cannot be None"
        )

    for field, value in (
        update_data.items()
    ):
        setattr(
            player,
            field,
            value,
        )

    try:
        db.commit()
        db.refresh(player)

    except SQLAlchemyError:
        db.rollback()
        raise

    return player
