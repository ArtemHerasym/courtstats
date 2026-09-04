from datetime import date

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.external_game import ExternalGame
from app.models.external_game_player_stats import (
    ExternalGamePlayerStats,
)
from app.models.game import GameStatus
from app.models.player_game_stats import (
    ParticipationStatus,
)
from app.models.team import Team
from app.schemas.external_game import (
    ExternalGameCreate,
    ExternalGameUpdate,
)
from app.schemas.external_game_player_stats import (
    ExternalGamePlayerStatsBase,
)


class ExternalGameNotFoundError(Exception):
    pass


class ExternalGameOpponentNotFoundError(Exception):
    pass


def _get_opponent_team(
    db: Session,
    opponent_team_id: int,
) -> Team:
    opponent = db.get(
        Team,
        opponent_team_id,
    )

    if opponent is None:
        raise ExternalGameOpponentNotFoundError(
            (
                "Opponent team with ID "
                f"{opponent_team_id} was not found."
            )
        )

    return opponent


def _ensure_new_external_game_is_draft(
    status: GameStatus,
) -> None:
    if status != GameStatus.DRAFT:
        raise ValueError(
            "New external games must start as DRAFT"
        )


def _validate_basic_external_game_state(
    name: str | None,
    game_date: date | None,
    venue_type,
    status: GameStatus | None,
    opponent_score: int | None,
) -> None:
    if name is None or not name.strip():
        raise ValueError(
            "External game name cannot be blank"
        )

    if game_date is None:
        raise ValueError(
            "External game game_date cannot be None"
        )

    if venue_type is None:
        raise ValueError(
            "External game venue_type cannot be None"
        )

    if status is None:
        raise ValueError(
            "External game status cannot be None"
        )

    if (
        opponent_score is not None
        and opponent_score < 0
    ):
        raise ValueError(
            "Opponent score cannot be negative"
        )


def _validate_stats_row(
    stats: ExternalGamePlayerStats,
) -> None:
    try:
        ExternalGamePlayerStatsBase(
            participation_status=(
                stats.participation_status
            ),
            three_point_attempts=(
                stats.three_point_attempts
            ),
            three_point_makes=(
                stats.three_point_makes
            ),
            two_point_attempts=(
                stats.two_point_attempts
            ),
            two_point_makes=(
                stats.two_point_makes
            ),
            free_throw_attempts=(
                stats.free_throw_attempts
            ),
            free_throw_makes=(
                stats.free_throw_makes
            ),
            turnovers=stats.turnovers,
            assists=stats.assists,
            offensive_rebounds=(
                stats.offensive_rebounds
            ),
            defensive_rebounds=(
                stats.defensive_rebounds
            ),
            steals=stats.steals,
            deflections=stats.deflections,
            personal_fouls=(
                stats.personal_fouls
            ),
        )

    except ValidationError as exc:
        first_error = exc.errors()[0]
        message = first_error["msg"]

        if message.startswith(
            "Value error, "
        ):
            message = message.removeprefix(
                "Value error, "
            )

        raise ValueError(message) from exc


def create_external_game(
    db: Session,
    game_data: ExternalGameCreate,
) -> ExternalGame:
    _get_opponent_team(
        db,
        game_data.opponent_team_id,
    )

    _ensure_new_external_game_is_draft(
        game_data.status,
    )

    _validate_basic_external_game_state(
        game_data.name,
        game_data.game_date,
        game_data.venue_type,
        game_data.status,
        game_data.opponent_score,
    )

    game = ExternalGame(
        **game_data.model_dump()
    )

    try:
        db.add(game)
        db.commit()
        db.refresh(game)

    except SQLAlchemyError:
        db.rollback()
        raise

    return game


def get_external_game(
    db: Session,
    external_game_id: int,
) -> ExternalGame:
    game = db.get(
        ExternalGame,
        external_game_id,
    )

    if game is None:
        raise ExternalGameNotFoundError(
            (
                "External game with ID "
                f"{external_game_id} was not found."
            )
        )

    return game


def list_external_games(
    db: Session,
) -> list[ExternalGame]:
    statement = (
        select(ExternalGame)
        .order_by(
            ExternalGame.game_date.desc(),
            ExternalGame.id.desc(),
        )
    )

    return list(
        db.scalars(statement).all()
    )


def validate_external_game_completion(
    db: Session,
    external_game_id: int,
) -> None:
    game = get_external_game(
        db,
        external_game_id,
    )

    _validate_basic_external_game_state(
        game.name,
        game.game_date,
        game.venue_type,
        GameStatus.COMPLETED,
        game.opponent_score,
    )

    _get_opponent_team(
        db,
        game.opponent_team_id,
    )

    if game.game_date > date.today():
        raise ValueError(
            "Future-dated external game cannot be completed"
        )

    if game.opponent_score is None:
        raise ValueError(
            (
                "Completed external game requires "
                "an opponent score"
            )
        )

    statement = (
        select(ExternalGamePlayerStats)
        .where(
            ExternalGamePlayerStats.external_game_id
            == game.id
        )
        .order_by(
            ExternalGamePlayerStats.id
        )
    )

    stats_rows = list(
        db.scalars(statement).all()
    )

    if not stats_rows:
        raise ValueError(
            (
                "Completed external game requires "
                "at least one player stats row"
            )
        )

    if not any(
        stats.participation_status
        == ParticipationStatus.PLAYED
        for stats in stats_rows
    ):
        raise ValueError(
            (
                "Completed external game requires "
                "at least one PLAYED player stats row"
            )
        )

    for stats in stats_rows:
        _validate_stats_row(stats)


def update_external_game(
    db: Session,
    external_game_id: int,
    game_data: ExternalGameUpdate,
) -> ExternalGame:
    game = get_external_game(
        db,
        external_game_id,
    )

    update_data = game_data.model_dump(
        exclude_unset=True
    )

    final_name = update_data.get(
        "name",
        game.name,
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

    if final_opponent_team_id is None:
        raise ValueError(
            (
                "External game opponent_team_id "
                "cannot be None"
            )
        )

    _get_opponent_team(
        db,
        final_opponent_team_id,
    )

    _validate_basic_external_game_state(
        final_name,
        final_game_date,
        final_venue_type,
        final_status,
        final_opponent_score,
    )

    try:
        for field, value in (
            update_data.items()
        ):
            setattr(
                game,
                field,
                value,
            )

        # Make the complete proposed state visible
        # before lifecycle validation.
        db.flush()

        if (
            final_status
            == GameStatus.COMPLETED
        ):
            validate_external_game_completion(
                db,
                game.id,
            )

        db.commit()
        db.refresh(game)

    except Exception:
        db.rollback()
        raise

    return game