from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import (
    IntegrityError,
    SQLAlchemyError,
)
from sqlalchemy.orm import Session

from app.models.external_game_player_stats import (
    ExternalGamePlayerStats,
)
from app.models.game import GameStatus
from app.models.player_game_stats import (
    ParticipationStatus,
)
from app.schemas.external_game_player_stats import (
    ExternalGamePlayerStatsBase,
    ExternalGamePlayerStatsCreate,
    ExternalGamePlayerStatsUpdate,
)
from app.services.external_game import (
    get_external_game,
    validate_external_game_completion,
)
from app.services.player import get_player


class ExternalGamePlayerStatsNotFoundError(
    Exception
):
    pass


class ExternalGamePlayerStatsConflictError(
    Exception
):
    pass


RAW_STAT_FIELDS = (
    "three_point_attempts",
    "three_point_makes",
    "two_point_attempts",
    "two_point_makes",
    "free_throw_attempts",
    "free_throw_makes",
    "turnovers",
    "assists",
    "offensive_rebounds",
    "defensive_rebounds",
    "steals",
    "deflections",
    "personal_fouls",
)


def _ensure_stats_entry_available(
    db: Session,
    external_game_id: int,
    player_id: int,
    exclude_stats_id: int | None = None,
) -> None:
    statement = select(
        ExternalGamePlayerStats
    ).where(
        ExternalGamePlayerStats.external_game_id
        == external_game_id,
        ExternalGamePlayerStats.player_id
        == player_id,
    )

    if exclude_stats_id is not None:
        statement = statement.where(
            ExternalGamePlayerStats.id
            != exclude_stats_id
        )

    existing = db.scalar(statement)

    if existing is not None:
        raise ExternalGamePlayerStatsConflictError(
            (
                "External game player stats already "
                "exist for this game and player."
            )
        )


def _validate_stats_state(
    participation_status: (
        ParticipationStatus | None
    ),
    stats_values: dict[
        str,
        int | None,
    ],
) -> None:
    if participation_status is None:
        raise ValueError(
            (
                "External game player stats "
                "participation_status cannot be None"
            )
        )

    for field in RAW_STAT_FIELDS:
        if stats_values[field] is None:
            raise ValueError(
                (
                    "External game player stats "
                    f"{field} cannot be None"
                )
            )

    try:
        ExternalGamePlayerStatsBase(
            participation_status=(
                participation_status
            ),
            **{
                field: stats_values[field]
                for field in RAW_STAT_FIELDS
            },
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


def create_external_game_player_stats(
    db: Session,
    stats_data: ExternalGamePlayerStatsCreate,
) -> ExternalGamePlayerStats:
    game = get_external_game(
        db,
        stats_data.external_game_id,
    )

    get_player(
        db,
        stats_data.player_id,
    )

    _ensure_stats_entry_available(
        db,
        stats_data.external_game_id,
        stats_data.player_id,
    )

    stats_values = {
        field: getattr(
            stats_data,
            field,
        )
        for field in RAW_STAT_FIELDS
    }

    _validate_stats_state(
        stats_data.participation_status,
        stats_values,
    )

    stats = ExternalGamePlayerStats(
        **stats_data.model_dump()
    )

    try:
        db.add(stats)

        # Required so completion validation can
        # see the newly inserted row.
        db.flush()

        if game.status == GameStatus.COMPLETED:
            validate_external_game_completion(
                db,
                game.id,
            )

        db.commit()
        db.refresh(stats)

    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(
                exc.orig,
                "diag",
                None,
            ),
            "constraint_name",
            None,
        )

        if constraint_name == (
            "uq_external_game_player_stats_"
            "game_player"
        ):
            raise (
                ExternalGamePlayerStatsConflictError(
                    (
                        "External game player stats "
                        "already exist for this "
                        "game and player."
                    )
                )
            ) from exc

        raise

    except Exception:
        db.rollback()
        raise

    return stats


def get_external_game_player_stats(
    db: Session,
    stats_id: int,
) -> ExternalGamePlayerStats:
    stats = db.get(
        ExternalGamePlayerStats,
        stats_id,
    )

    if stats is None:
        raise ExternalGamePlayerStatsNotFoundError(
            (
                "External game player stats "
                f"with ID {stats_id} were not found."
            )
        )

    return stats


def list_external_game_player_stats(
    db: Session,
    external_game_id: int,
) -> list[ExternalGamePlayerStats]:
    get_external_game(
        db,
        external_game_id,
    )

    statement = (
        select(
            ExternalGamePlayerStats
        )
        .where(
            ExternalGamePlayerStats.external_game_id
            == external_game_id
        )
        .order_by(
            ExternalGamePlayerStats.id
        )
    )

    return list(
        db.scalars(statement).all()
    )


def update_external_game_player_stats(
    db: Session,
    stats_id: int,
    stats_data: ExternalGamePlayerStatsUpdate,
) -> ExternalGamePlayerStats:
    stats = get_external_game_player_stats(
        db,
        stats_id,
    )

    update_data = stats_data.model_dump(
        exclude_unset=True
    )

    final_external_game_id = (
        update_data.get(
            "external_game_id",
            stats.external_game_id,
        )
    )

    final_player_id = update_data.get(
        "player_id",
        stats.player_id,
    )

    final_participation_status = (
        update_data.get(
            "participation_status",
            stats.participation_status,
        )
    )

    final_stats_values = {
        field: update_data.get(
            field,
            getattr(
                stats,
                field,
            ),
        )
        for field in RAW_STAT_FIELDS
    }

    if final_external_game_id is None:
        raise ValueError(
            (
                "External game player stats "
                "external_game_id cannot be None"
            )
        )

    if final_player_id is None:
        raise ValueError(
            (
                "External game player stats "
                "player_id cannot be None"
            )
        )

    source_game = get_external_game(
        db,
        stats.external_game_id,
    )

    destination_game = get_external_game(
        db,
        final_external_game_id,
    )

    get_player(
        db,
        final_player_id,
    )

    _ensure_stats_entry_available(
        db,
        final_external_game_id,
        final_player_id,
        exclude_stats_id=stats.id,
    )

    _validate_stats_state(
        final_participation_status,
        final_stats_values,
    )

    try:
        for field, value in (
            update_data.items()
        ):
            setattr(
                stats,
                field,
                value,
            )

        db.flush()

        # If a row leaves or changes inside a
        # completed source game, ensure that game
        # still satisfies completion rules.
        if (
            source_game.status
            == GameStatus.COMPLETED
        ):
            validate_external_game_completion(
                db,
                source_game.id,
            )

        # If the row moved to another completed
        # game, validate that destination as well.
        if (
            destination_game.id
            != source_game.id
            and destination_game.status
            == GameStatus.COMPLETED
        ):
            validate_external_game_completion(
                db,
                destination_game.id,
            )

        db.commit()
        db.refresh(stats)

    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(
                exc.orig,
                "diag",
                None,
            ),
            "constraint_name",
            None,
        )

        if constraint_name == (
            "uq_external_game_player_stats_"
            "game_player"
        ):
            raise (
                ExternalGamePlayerStatsConflictError(
                    (
                        "External game player stats "
                        "already exist for this "
                        "game and player."
                    )
                )
            ) from exc

        raise

    except Exception:
        db.rollback()
        raise

    return stats