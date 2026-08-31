from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session

from app.models.season_roster import RosterStatus, SeasonRoster
from app.schemas.season_roster import SeasonRosterCreate, SeasonRosterUpdate
from app.services.player import get_player
from app.services.season import get_season


class SeasonRosterNotFoundError(Exception):
    pass


class SeasonRosterMembershipConflictError(Exception):
    pass


class SeasonRosterJerseyConflictError(Exception):
    pass

def _ensure_membership_available(
         db: Session,
         season_id: int,
         player_id: int,
         exclude_roster_id: int | None = None,
 ) -> None:
     statement = select(SeasonRoster).where(
         SeasonRoster.season_id == season_id,
         SeasonRoster.player_id == player_id,
     )
     if exclude_roster_id is not None:
         statement = statement.where(
             SeasonRoster.id != exclude_roster_id
         )
     existing_membership = db.scalar(statement)
     if existing_membership is not None:
         raise SeasonRosterMembershipConflictError(
             "Player is already on this seasons roster."
         )

def _ensure_active_jersey_available(
        db: Session,
        season_id: int,
        jersey_number: int | None,
        status: RosterStatus,
        exclude_roster_id: int | None = None,
):
    if jersey_number is None:
        return

    if status != RosterStatus.ACTIVE:
        return

    statement = select(SeasonRoster).where(
        SeasonRoster.season_id == season_id,
        SeasonRoster.jersey_number == jersey_number,
        SeasonRoster.status == RosterStatus.ACTIVE,
    )

    if exclude_roster_id is not None:
        statement = statement.where(
            SeasonRoster.id != exclude_roster_id
        )

    existing_roster = db.scalar(statement)

    if existing_roster is not None:
        raise SeasonRosterJerseyConflictError(
            f"Jersey number {jersey_number} is already assigned "
            "to an active player in this seasons."
        )

def create_season_roster(
        db: Session,
        roster_data: SeasonRosterCreate,
) -> SeasonRoster:
    get_season(db, roster_data.season_id)
    get_player(db, roster_data.player_id)

    _ensure_membership_available(
        db,
        roster_data.season_id,
        roster_data.player_id,
    )

    _ensure_active_jersey_available(
        db,
        roster_data.season_id,
        roster_data.jersey_number,
        roster_data.status,
    )

    roster = SeasonRoster(**roster_data.model_dump())

    try:
        db.add(roster)
        db.commit()
        db.refresh(roster)
    except IntegrityError as exc:
        db.rollback()
        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )
        if constraint_name == "uq_season_rosters_season_player":
            raise SeasonRosterMembershipConflictError(
                "Player is already on this seasons roster."
            ) from exc

        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return roster


def get_season_roster(
    db: Session,
    roster_id: int,
) -> SeasonRoster:

    roster = db.get(SeasonRoster, roster_id)

    if roster is None:
        raise SeasonRosterNotFoundError(
            f"Season roster entry with ID {roster_id} was not found."
        )

    return roster

def list_season_rosters(
    db: Session,
) -> list[SeasonRoster]:

    statement = select(SeasonRoster).order_by(SeasonRoster.id)

    return list(db.scalars(statement).all())

def update_season_roster(
        db: Session,
        roster_id: int,
        roster_data: SeasonRosterUpdate,
) -> SeasonRoster:

    roster = get_season_roster(db, roster_id)

    update_data = roster_data.model_dump(exclude_unset=True)

    final_jersey_number = update_data.get(
        "jersey_number",
        roster.jersey_number,
    )

    final_status = update_data.get(
        "status",
        roster.status,
    )

    final_season_id = update_data.get(
        "season_id",
        roster.season_id,
    )

    final_player_id = update_data.get(
        "player_id",
        roster.player_id,
    )

    if final_season_id is None:
        raise ValueError("Season roster season_id cannot be None")

    if final_player_id is None:
        raise ValueError("Season roster player_id cannot be None")

    if final_status is None:
        raise ValueError("Season roster status cannot be None")

    get_season(db, final_season_id)
    get_player(db, final_player_id)

    _ensure_membership_available(
        db,
        final_season_id,
        final_player_id,
        exclude_roster_id=roster.id,
    )

    _ensure_active_jersey_available(
        db,
        final_season_id,
        final_jersey_number,
        final_status,
        exclude_roster_id=roster.id,
    )

    for field, value in update_data.items():
        setattr(roster, field, value)

    try:
        db.commit()
        db.refresh(roster)

    except IntegrityError as exc:
        db.rollback()

        constraint_name = getattr(
            getattr(exc.orig, "diag", None),
            "constraint_name",
            None,
        )

        if constraint_name == "uq_season_rosters_season_player":
            raise SeasonRosterMembershipConflictError(
                "Player is already on this seasons roster."
            ) from exc

        raise

    except SQLAlchemyError:
        db.rollback()
        raise

    return roster


def list_season_rosters_for_season(
    db: Session,
    season_id: int,
) -> list[SeasonRoster]:
    get_season(db, season_id)

    statement = (
        select(SeasonRoster)
        .where(SeasonRoster.season_id == season_id)
        .order_by(
            SeasonRoster.jersey_number.asc().nulls_last(),
            SeasonRoster.id,
        )
    )

    return list(db.scalars(statement).all())