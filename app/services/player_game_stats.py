from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from pydantic import ValidationError
from app.models.game import GameStatus

from app.schemas.player_game_stats import (
    PlayerGameStatsBase,
    PlayerGameStatsCreate,
    PlayerGameStatsUpdate,
)
from app.services.game import (
    get_game,
    validate_game_completion,
)
from app.services.season_roster import get_season_roster

from app.models.player_game_stats import (
    ParticipationStatus,
    PlayerGameStats,
)


class PlayerGameStatsNotFoundError(Exception):
    pass


class PlayerGameStatsSeasonMismatchError(Exception):
    pass


class PlayerGameStatsConflictError(Exception):
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


def _ensure_same_season(
    game,
    season_roster,
) -> None:
    if game.season_id != season_roster.season_id:
        raise PlayerGameStatsSeasonMismatchError(
            "Game and season roster must belong to the same season."
        )


def _ensure_stats_entry_available(
    db: Session,
    game_id: int,
    season_roster_id: int,
    exclude_stats_id: int | None = None,
) -> None:
    statement = select(PlayerGameStats).where(
        PlayerGameStats.game_id == game_id,
        PlayerGameStats.season_roster_id == season_roster_id,
    )

    if exclude_stats_id is not None:
        statement = statement.where(
            PlayerGameStats.id != exclude_stats_id
        )

    existing_stats = db.scalar(statement)

    if existing_stats is not None:
        raise PlayerGameStatsConflictError(
            "Player game stats already exist for this game and roster entry."
        )


def _validate_stats_state(
    participation_status: ParticipationStatus | None,
    stats_values: dict[str, int | None],
) -> None:
    if participation_status is None:
        raise ValueError(
            "Player game stats participation_status cannot be None"
        )

    for field in RAW_STAT_FIELDS:
        if stats_values[field] is None:
            raise ValueError(
                f"Player game stats {field} cannot be None"
            )

    try:
        PlayerGameStatsBase(
            participation_status=participation_status,
            **{
                field: stats_values[field]
                for field in RAW_STAT_FIELDS
            },
        )
    except ValidationError as exc:
        first_error = exc.errors()[0]
        message = first_error["msg"]

        if message.startswith("Value error, "):
            message = message.removeprefix("Value error, ")

        raise ValueError(message) from exc


def _ensure_completed_game_keeps_played_player(
    db: Session,
    source_game,
    stats: PlayerGameStats,
    final_game_id: int,
    final_participation_status: ParticipationStatus,
) -> None:
    if source_game.status != GameStatus.COMPLETED:
        return

    if stats.participation_status != ParticipationStatus.PLAYED:
        return

    keeps_played_row_on_same_game = (
        final_game_id == source_game.id
        and final_participation_status == ParticipationStatus.PLAYED
    )

    if keeps_played_row_on_same_game:
        return

    statement = select(PlayerGameStats.id).where(
        PlayerGameStats.game_id == source_game.id,
        PlayerGameStats.participation_status == ParticipationStatus.PLAYED,
        PlayerGameStats.id != stats.id,
    )

    other_played_stats_id = db.scalar(statement)

    if other_played_stats_id is None:
        raise PlayerGameStatsConflictError(
            "Completed game requires at least one PLAYED player game stats row"
        )


def create_player_game_stats(
    db: Session,
    stats_data: PlayerGameStatsCreate,
) -> PlayerGameStats:
    game = get_game(
        db,
        stats_data.game_id,
    )

    season_roster = get_season_roster(
        db,
        stats_data.season_roster_id,
    )

    _ensure_same_season(
        game,
        season_roster,
    )

    _ensure_stats_entry_available(
        db,
        stats_data.game_id,
        stats_data.season_roster_id,
    )

    stats_values = {
        field: getattr(stats_data, field)
        for field in RAW_STAT_FIELDS
    }

    _validate_stats_state(
        stats_data.participation_status,
        stats_values,
    )

    stats = PlayerGameStats(
        **stats_data.model_dump()
    )

    try:
        db.add(stats)
        db.commit()
        db.refresh(stats)

    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "uq_player_game_stats_game_roster":
            raise PlayerGameStatsConflictError(
                "Player game stats already exist for this game and roster entry."
            ) from exc

        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return stats


def get_player_game_stats(
    db: Session,
    stats_id: int,
) -> PlayerGameStats:
    stats = db.get(PlayerGameStats, stats_id)

    if stats is None:
        raise PlayerGameStatsNotFoundError(
            f"Player game stats with ID {stats_id} were not found."
        )

    return stats

def list_player_game_stats(
    db: Session,
) -> list[PlayerGameStats]:
    statement = select(PlayerGameStats).order_by(
        PlayerGameStats.id
    )

    return list(db.scalars(statement).all())


def update_player_game_stats(
    db: Session,
    stats_id: int,
    stats_data: PlayerGameStatsUpdate,
) -> PlayerGameStats:
    stats = get_player_game_stats(
        db,
        stats_id,
    )

    update_data = stats_data.model_dump(
        exclude_unset=True
    )

    final_game_id = update_data.get(
        "game_id",
        stats.game_id,
    )

    final_season_roster_id = update_data.get(
        "season_roster_id",
        stats.season_roster_id,
    )

    final_participation_status = update_data.get(
        "participation_status",
        stats.participation_status,
    )

    final_stats_values = {
        field: update_data.get(
            field,
            getattr(stats, field),
        )
        for field in RAW_STAT_FIELDS
    }

    if final_game_id is None:
        raise ValueError(
            "Player game stats game_id cannot be None"
        )

    if final_season_roster_id is None:
        raise ValueError(
            "Player game stats season_roster_id cannot be None"
        )

    source_game = get_game(
        db,
        stats.game_id,
    )

    game = get_game(
        db,
        final_game_id,
    )

    season_roster = get_season_roster(
        db,
        final_season_roster_id,
    )

    _ensure_same_season(
        game,
        season_roster,
    )

    _ensure_stats_entry_available(
        db,
        final_game_id,
        final_season_roster_id,
        exclude_stats_id=stats.id,
    )

    _validate_stats_state(
        final_participation_status,
        final_stats_values,
    )

    _ensure_completed_game_keeps_played_player(
        db,
        source_game,
        stats,
        final_game_id,
        final_participation_status,
    )

    for field, value in update_data.items():
        setattr(stats, field, value)

    try:
        db.commit()
        db.refresh(stats)

    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "uq_player_game_stats_game_roster":
            raise PlayerGameStatsConflictError(
                "Player game stats already exist for this game and roster entry."
            ) from exc

        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return stats


def list_player_game_stats_for_game(
    db: Session,
    game_id: int,
) -> list[PlayerGameStats]:
    get_game(db, game_id)

    statement = (
        select(PlayerGameStats)
        .where(PlayerGameStats.game_id == game_id)
        .order_by(PlayerGameStats.season_roster_id)
    )

    return list(db.scalars(statement).all())


def save_player_game_stats_draft(
    db: Session,
    game_id: int,
    stats_rows: list[PlayerGameStatsCreate],
) -> list[PlayerGameStats]:
    game = get_game(db, game_id)

    if game.status != GameStatus.DRAFT:
        raise PlayerGameStatsConflictError(
            "Player statistics can only be draft-saved for a DRAFT game."
        )

    seen_roster_ids: set[int] = set()

    # Validate every submitted row BEFORE modifying the database.
    for stats_data in stats_rows:
        if stats_data.game_id != game_id:
            raise PlayerGameStatsConflictError(
                "Submitted player statistics belong to a different game."
            )

        if stats_data.season_roster_id in seen_roster_ids:
            raise PlayerGameStatsConflictError(
                "Duplicate season roster entry in submitted statistics."
            )

        seen_roster_ids.add(stats_data.season_roster_id)

        season_roster = get_season_roster(
            db,
            stats_data.season_roster_id,
        )

        _ensure_same_season(
            game,
            season_roster,
        )

        stats_values = {
            field: getattr(stats_data, field)
            for field in RAW_STAT_FIELDS
        }

        _validate_stats_state(
            stats_data.participation_status,
            stats_values,
        )

    statement = select(PlayerGameStats).where(
        PlayerGameStats.game_id == game_id
    )

    existing_stats = list(
        db.scalars(statement).all()
    )

    existing_by_roster_id = {
        stats.season_roster_id: stats
        for stats in existing_stats
    }

    saved_rows: list[PlayerGameStats] = []

    try:
        for stats_data in stats_rows:
            existing = existing_by_roster_id.get(
                stats_data.season_roster_id
            )

            if existing is None:
                stats = PlayerGameStats(
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
                        getattr(stats_data, field),
                    )

                saved_rows.append(existing)

        # ONE commit for the entire roster.
        db.commit()

        for stats in saved_rows:
            db.refresh(stats)

    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "uq_player_game_stats_game_roster":
            raise PlayerGameStatsConflictError(
                "Duplicate player statistics were detected."
            ) from exc

        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return saved_rows

def _apply_player_game_stats_rows(
    db: Session,
    game,
    stats_rows: list[PlayerGameStatsCreate],
) -> list[PlayerGameStats]:
    seen_roster_ids: set[int] = set()

    # Validate the entire submission before changing ORM objects.
    for stats_data in stats_rows:
        if stats_data.game_id != game.id:
            raise PlayerGameStatsConflictError(
                "Submitted player statistics belong to a different game."
            )

        if stats_data.season_roster_id in seen_roster_ids:
            raise PlayerGameStatsConflictError(
                "Duplicate season roster entry in submitted statistics."
            )

        seen_roster_ids.add(
            stats_data.season_roster_id
        )

        season_roster = get_season_roster(
            db,
            stats_data.season_roster_id,
        )

        _ensure_same_season(
            game,
            season_roster,
        )

        stats_values = {
            field: getattr(stats_data, field)
            for field in RAW_STAT_FIELDS
        }

        _validate_stats_state(
            stats_data.participation_status,
            stats_values,
        )

    statement = select(PlayerGameStats).where(
        PlayerGameStats.game_id == game.id
    )

    existing_stats = list(
        db.scalars(statement).all()
    )

    existing_by_roster_id = {
        stats.season_roster_id: stats
        for stats in existing_stats
    }

    saved_rows: list[PlayerGameStats] = []

    for stats_data in stats_rows:
        existing = existing_by_roster_id.get(
            stats_data.season_roster_id
        )

        if existing is None:
            stats = PlayerGameStats(
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
                    getattr(stats_data, field),
                )

            saved_rows.append(existing)

    return saved_rows

def save_player_game_stats(
    db: Session,
    game_id: int,
    stats_rows: list[PlayerGameStatsCreate],
    opponent_score: int | None,
) -> list[PlayerGameStats]:
    game = get_game(
        db,
        game_id,
    )

    try:
        saved_rows = _apply_player_game_stats_rows(
            db,
            game,
            stats_rows,
        )

        game.opponent_score = opponent_score

        # Make staged stats visible to completion queries.
        db.flush()

        if game.status == GameStatus.COMPLETED:
            validate_game_completion(
                db,
                game.id,
                game.game_date,
                game.opponent_score,
            )

        db.commit()

        for stats in saved_rows:
            db.refresh(stats)

        db.refresh(game)

    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if (
            constraint_name
            == "uq_player_game_stats_game_roster"
        ):
            raise PlayerGameStatsConflictError(
                "Duplicate player statistics were detected."
            ) from exc

        raise

    except Exception:
        db.rollback()
        raise

    return saved_rows

def finalize_game_with_stats(
    db: Session,
    game_id: int,
    stats_rows: list[PlayerGameStatsCreate],
    opponent_score: int | None,
) -> list[PlayerGameStats]:
    game = get_game(
        db,
        game_id,
    )

    if game.status != GameStatus.DRAFT:
        raise PlayerGameStatsConflictError(
            "Only a DRAFT game can be finalized."
        )

    try:
        saved_rows = _apply_player_game_stats_rows(
            db,
            game,
            stats_rows,
        )

        game.opponent_score = opponent_score

        # Flush inserts/updates without committing them.
        db.flush()

        validate_game_completion(
            db,
            game.id,
            game.game_date,
            game.opponent_score,
        )

        game.status = GameStatus.COMPLETED

        db.commit()

        for stats in saved_rows:
            db.refresh(stats)

        db.refresh(game)

    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if (
            constraint_name
            == "uq_player_game_stats_game_roster"
        ):
            raise PlayerGameStatsConflictError(
                "Duplicate player statistics were detected."
            ) from exc

        raise

    except Exception:
        db.rollback()
        raise

    return saved_rows