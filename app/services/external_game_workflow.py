from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
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
)
from app.services.external_game import (
    get_external_game,
    validate_external_game_completion,
)
from app.services.external_game_player_stats import (
    ExternalGamePlayerStatsConflictError,
    RAW_STAT_FIELDS,
)
from app.services.player import get_player


def _raise_validation_error(
    exc: ValidationError,
) -> None:
    message = exc.errors()[0]["msg"]

    if message.startswith("Value error, "):
        message = message.removeprefix(
            "Value error, "
        )

    raise ValueError(message) from exc


def _validate_stats_data(
    stats_data: ExternalGamePlayerStatsCreate,
) -> None:
    stats_values = {
        field: getattr(stats_data, field)
        for field in RAW_STAT_FIELDS
    }

    try:
        ExternalGamePlayerStatsBase(
            participation_status=(
                stats_data.participation_status
            ),
            **stats_values,
        )

    except ValidationError as exc:
        _raise_validation_error(exc)


def sync_external_game_players(
    db: Session,
    external_game_id: int,
    player_ids: list[int],
) -> list[ExternalGamePlayerStats]:
    game = get_external_game(
        db,
        external_game_id,
    )

    if game.status != GameStatus.DRAFT:
        raise ExternalGamePlayerStatsConflictError(
            (
                "Player selection can only be changed "
                "while the external game is DRAFT."
            )
        )

    if len(player_ids) != len(set(player_ids)):
        raise ExternalGamePlayerStatsConflictError(
            "Duplicate player selection is not allowed."
        )

    for player_id in player_ids:
        get_player(
            db,
            player_id,
        )

    statement = (
        select(ExternalGamePlayerStats)
        .where(
            ExternalGamePlayerStats.external_game_id
            == external_game_id
        )
        .order_by(
            ExternalGamePlayerStats.id
        )
    )

    existing_rows = list(
        db.scalars(statement).all()
    )

    existing_by_player_id = {
        row.player_id: row
        for row in existing_rows
    }

    selected_player_ids = set(
        player_ids
    )

    try:
        for row in existing_rows:
            if (
                row.player_id
                not in selected_player_ids
            ):
                db.delete(row)

        for player_id in player_ids:
            if player_id in existing_by_player_id:
                continue

            row = ExternalGamePlayerStats(
                external_game_id=external_game_id,
                player_id=player_id,
                participation_status=(
                    ParticipationStatus.PLAYED
                ),
                three_point_attempts=0,
                three_point_makes=0,
                two_point_attempts=0,
                two_point_makes=0,
                free_throw_attempts=0,
                free_throw_makes=0,
                turnovers=0,
                assists=0,
                offensive_rebounds=0,
                defensive_rebounds=0,
                steals=0,
                deflections=0,
                personal_fouls=0,
            )

            db.add(row)

        db.flush()
        db.commit()

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
                        "Duplicate player selection "
                        "was detected."
                    )
                )
            ) from exc

        raise

    except Exception:
        db.rollback()
        raise

    result_statement = (
        select(ExternalGamePlayerStats)
        .where(
            ExternalGamePlayerStats.external_game_id
            == external_game_id
        )
        .order_by(
            ExternalGamePlayerStats.id
        )
    )

    return list(
        db.scalars(
            result_statement
        ).all()
    )


def _apply_external_game_stats_rows(
    db: Session,
    game,
    stats_rows: list[
        ExternalGamePlayerStatsCreate
    ],
) -> list[ExternalGamePlayerStats]:
    seen_player_ids: set[int] = set()

    for stats_data in stats_rows:
        if (
            stats_data.external_game_id
            != game.id
        ):
            raise (
                ExternalGamePlayerStatsConflictError(
                    (
                        "Submitted player statistics "
                        "belong to a different "
                        "external game."
                    )
                )
            )

        if (
            stats_data.player_id
            in seen_player_ids
        ):
            raise (
                ExternalGamePlayerStatsConflictError(
                    (
                        "Duplicate player in submitted "
                        "external game statistics."
                    )
                )
            )

        seen_player_ids.add(
            stats_data.player_id
        )

        get_player(
            db,
            stats_data.player_id,
        )

        _validate_stats_data(
            stats_data
        )

    statement = select(
        ExternalGamePlayerStats
    ).where(
        ExternalGamePlayerStats.external_game_id
        == game.id
    )

    existing_rows = list(
        db.scalars(statement).all()
    )

    existing_by_player_id = {
        row.player_id: row
        for row in existing_rows
    }

    saved_rows: list[
        ExternalGamePlayerStats
    ] = []

    for stats_data in stats_rows:
        existing = existing_by_player_id.get(
            stats_data.player_id
        )

        if existing is None:
            stats = ExternalGamePlayerStats(
                **stats_data.model_dump()
            )

            db.add(stats)
            saved_rows.append(stats)

        else:
            existing.participation_status = (
                stats_data.participation_status
            )

            for field in RAW_STAT_FIELDS:
                setattr(
                    existing,
                    field,
                    getattr(
                        stats_data,
                        field,
                    ),
                )

            saved_rows.append(existing)

    return saved_rows


def _raise_integrity_conflict(
    exc: IntegrityError,
) -> None:
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
                    "Duplicate player statistics "
                    "were detected."
                )
            )
        ) from exc

    raise exc


def save_external_game_stats(
    db: Session,
    external_game_id: int,
    stats_rows: list[
        ExternalGamePlayerStatsCreate
    ],
    opponent_score: int | None,
) -> list[ExternalGamePlayerStats]:
    game = get_external_game(
        db,
        external_game_id,
    )

    if (
        opponent_score is not None
        and opponent_score < 0
    ):
        raise ValueError(
            (
                "Opponent score must be "
                "a nonnegative integer."
            )
        )

    try:
        saved_rows = (
            _apply_external_game_stats_rows(
                db,
                game,
                stats_rows,
            )
        )

        game.opponent_score = opponent_score

        db.flush()

        if game.status == GameStatus.COMPLETED:
            validate_external_game_completion(
                db,
                game.id,
            )

        db.commit()

        for stats in saved_rows:
            db.refresh(stats)

        db.refresh(game)

    except IntegrityError as exc:
        db.rollback()
        _raise_integrity_conflict(exc)

    except Exception:
        db.rollback()
        raise

    return saved_rows


def finalize_external_game_with_stats(
    db: Session,
    external_game_id: int,
    stats_rows: list[
        ExternalGamePlayerStatsCreate
    ],
    opponent_score: int | None,
) -> list[ExternalGamePlayerStats]:
    game = get_external_game(
        db,
        external_game_id,
    )

    if game.status != GameStatus.DRAFT:
        raise ExternalGamePlayerStatsConflictError(
            (
                "Only a DRAFT external game "
                "can be finalized."
            )
        )

    if (
        opponent_score is not None
        and opponent_score < 0
    ):
        raise ValueError(
            (
                "Opponent score must be "
                "a nonnegative integer."
            )
        )

    try:
        saved_rows = (
            _apply_external_game_stats_rows(
                db,
                game,
                stats_rows,
            )
        )

        game.opponent_score = opponent_score

        # Make all staged stats and the score
        # visible to completion validation.
        db.flush()

        validate_external_game_completion(
            db,
            game.id,
        )

        # Only change status after every
        # completion requirement has passed.
        game.status = GameStatus.COMPLETED

        db.flush()

        # One commit for stats + score + status.
        db.commit()

        for stats in saved_rows:
            db.refresh(stats)

        db.refresh(game)

    except IntegrityError as exc:
        db.rollback()
        _raise_integrity_conflict(exc)

    except Exception:
        db.rollback()
        raise

    return saved_rows