from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.game import Game, GameStatus
from app.models.team import Team
from app.schemas.game import GameCreate, GameUpdate
from app.services.season import get_season
from app.models.player_game_stats import (
    ParticipationStatus,
    PlayerGameStats,
)


class GameNotFoundError(Exception):
    pass


class OpponentTeamNotFoundError(Exception):
    pass


class GameOpponentConflictError(Exception):
    pass


class GameSeasonStatsConflictError(Exception):
    pass


def _get_opponent_team(
    db: Session,
    opponent_team_id: int,
) -> Team:
    opponent_team = db.get(Team, opponent_team_id)

    if opponent_team is None:
        raise OpponentTeamNotFoundError(
            f"Opponent team with ID {opponent_team_id} was not found."
        )

    return opponent_team


def _ensure_opponent_is_not_season_team(
    season_team_id: int,
    opponent_team_id: int,
) -> None:
    if season_team_id == opponent_team_id:
        raise GameOpponentConflictError(
            "Opponent team cannot be the same team as the season team."
        )


def _ensure_new_game_is_draft(
    status: GameStatus,
) -> None:
    if status != GameStatus.DRAFT:
        raise ValueError(
            "New games must start as DRAFT"
        )


def _ensure_completed_game_has_played_stats(
    db: Session,
    game_id: int,
    status: GameStatus,
) -> None:
    if status != GameStatus.COMPLETED:
        return

    statement = select(
        PlayerGameStats.participation_status
    ).where(
        PlayerGameStats.game_id == game_id
    )

    participation_statuses = list(
        db.scalars(statement).all()
    )

    if not participation_statuses:
        raise ValueError(
            "Completed game requires at least one player game stats row"
        )

    if ParticipationStatus.PLAYED not in participation_statuses:
        raise ValueError(
            "Completed game requires at least one PLAYED player game stats row"
        )


def _validate_game_state(
    game_date: date,
    status: GameStatus,
    opponent_score: int | None,
) -> None:
    if opponent_score is not None and opponent_score < 0:
        raise ValueError("Opponent score cannot be negative")

    if status == GameStatus.COMPLETED and opponent_score is None:
        raise ValueError(
            "Completed game requires an opponent score"
        )

    if (
        status == GameStatus.COMPLETED
        and game_date > date.today()
    ):
        raise ValueError(
            "Future-dated game cannot be completed"
        )

def validate_game_completion(
    db: Session,
    game_id: int,
    game_date: date,
    opponent_score: int | None,
) -> None:
    _validate_game_state(
        game_date,
        GameStatus.COMPLETED,
        opponent_score,
    )

    _ensure_completed_game_has_played_stats(
        db,
        game_id,
        GameStatus.COMPLETED,
    )

def _ensure_game_season_can_change(
    db: Session,
    game_id: int,
    current_season_id: int,
    final_season_id: int,
) -> None:
    if final_season_id == current_season_id:
        return

    statement = select(PlayerGameStats.id).where(
        PlayerGameStats.game_id == game_id
    )

    existing_stats_id = db.scalar(statement)

    if existing_stats_id is not None:
        raise GameSeasonStatsConflictError(
            "Game season cannot be changed after player game stats exist."
        )

def create_game(
        db: Session,
        game_data: GameCreate,
) -> Game:
    season = get_season(db, game_data.season_id)

    opponent_team = _get_opponent_team(
        db,
        game_data.opponent_team_id,
    )

    _ensure_opponent_is_not_season_team(
        season.team_id,
        opponent_team.id,
    )

    _ensure_new_game_is_draft(
        game_data.status,
    )

    _validate_game_state(
        game_data.game_date,
        game_data.status,
        game_data.opponent_score,
    )

    game = Game(**game_data.model_dump())

    try:
        db.add(game)
        db.commit()
        db.refresh(game)
    except SQLAlchemyError:
        db.rollback()
        raise

    return game


def get_game(
    db: Session,
    game_id: int,
) -> Game:
    game = db.get(Game, game_id)

    if game is None:
        raise GameNotFoundError(
            f"Game with ID {game_id} was not found."
        )

    return game


def list_games(
    db: Session,
) -> list[Game]:
    statement = select(Game).order_by(Game.id)

    return list(db.scalars(statement).all())


def update_game(
    db: Session,
    game_id: int,
    game_data: GameUpdate,
) -> Game:
    game = get_game(db, game_id)

    update_data = game_data.model_dump(exclude_unset=True)

    final_season_id = update_data.get(
        "season_id",
        game.season_id,
    )

    final_opponent_team_id = update_data.get(
        "opponent_team_id",
        game.opponent_team_id,
    )

    final_game_date = update_data.get(
        "game_date",
        game.game_date,
    )

    final_venue_type = update_data.get(
        "venue_type",
        game.venue_type,
    )

    final_status = update_data.get(
        "status",
        game.status,
    )

    final_opponent_score = update_data.get(
        "opponent_score",
        game.opponent_score,
    )


    if final_season_id is None:
        raise ValueError("Game season_id cannot be None")

    if final_opponent_team_id is None:
        raise ValueError("Game opponent_team_id cannot be None")

    if final_game_date is None:
        raise ValueError("Game game_date cannot be None")

    if final_venue_type is None:
        raise ValueError("Game venue_type cannot be None")

    if final_status is None:
        raise ValueError("Game status cannot be None")

    _ensure_game_season_can_change(
        db,
        game.id,
        game.season_id,
        final_season_id,
    )

    season = get_season(
        db,
        final_season_id,
    )

    opponent_team = _get_opponent_team(
        db,
        final_opponent_team_id,
    )

    _ensure_opponent_is_not_season_team(
        season.team_id,
        opponent_team.id,
    )

    if final_status == GameStatus.COMPLETED:
        validate_game_completion(
            db,
            game.id,
            final_game_date,
            final_opponent_score,
        )
    else:
        _validate_game_state(
            final_game_date,
            final_status,
            final_opponent_score,
        )

    for field, value in update_data.items():
        setattr(game, field, value)

    try:
        db.commit()
        db.refresh(game)

    except SQLAlchemyError:
        db.rollback()
        raise

    return game