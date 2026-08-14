import pytest

from app.models.player import Player
from app.models.season import Season
from app.models.season_roster import RosterStatus
from app.models.team import Team
from app.schemas.season_roster import SeasonRosterCreate, SeasonRosterUpdate
from app.services.player import PlayerNotFoundError
from app.services.season import SeasonNotFoundError
from app.services.season_roster import (
    SeasonRosterJerseyConflictError,
    SeasonRosterMembershipConflictError,
    SeasonRosterNotFoundError,
    create_season_roster,
    get_season_roster,
    list_season_rosters,
    update_season_roster,
)

def _create_team(db_session, name="Jordan Christian Preparatory"):
    team = Team(name=name)
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _create_season(db_session, team, name="2026-27"):
    season = Season(
        team_id=team.id,
        name=name,
    )
    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)
    return season


def _create_player(db_session, full_name="John Smith"):
    player = Player(full_name=full_name)
    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)
    return player

def test_create_season_roster(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)
    player = _create_player(db_session)

    roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=player.id,
            jersey_number=12,
            position="Guard",
            grade_level="Senior",
        ),
    )

    assert roster.id is not None
    assert roster.season_id == season.id
    assert roster.player_id == player.id
    assert roster.jersey_number == 12
    assert roster.position == "Guard"
    assert roster.grade_level == "Senior"
    assert roster.status == RosterStatus.ACTIVE
    assert roster.created_at is not None
    assert roster.updated_at is not None


def test_create_season_roster_rejects_missing_season(db_session):
    player = _create_player(db_session)

    with pytest.raises(SeasonNotFoundError):
        create_season_roster(
            db_session,
            SeasonRosterCreate(
                season_id=999999,
                player_id=player.id,
            ),
        )


def test_create_season_roster_rejects_missing_player(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)

    with pytest.raises(PlayerNotFoundError):
        create_season_roster(
            db_session,
            SeasonRosterCreate(
                season_id=season.id,
                player_id=999999,
            ),
        )


def test_create_season_roster_rejects_duplicate_membership(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)
    player = _create_player(db_session)

    create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=player.id,
            status=RosterStatus.INACTIVE,
        ),
    )

    with pytest.raises(SeasonRosterMembershipConflictError):
        create_season_roster(
            db_session,
            SeasonRosterCreate(
                season_id=season.id,
                player_id=player.id,
            ),
        )


def test_create_rejects_duplicate_active_jersey_in_same_season(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)

    first_player = _create_player(db_session, "First Player")
    second_player = _create_player(db_session, "Second Player")

    create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=first_player.id,
            jersey_number=12,
        ),
    )

    with pytest.raises(SeasonRosterJerseyConflictError):
        create_season_roster(
            db_session,
            SeasonRosterCreate(
                season_id=season.id,
                player_id=second_player.id,
                jersey_number=12,
            ),
        )


def test_create_allows_active_jersey_used_by_inactive_membership(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)

    first_player = _create_player(db_session, "First Player")
    second_player = _create_player(db_session, "Second Player")

    first_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=first_player.id,
            jersey_number=12,
            status=RosterStatus.INACTIVE,
        ),
    )

    second_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=second_player.id,
            jersey_number=12,
            status=RosterStatus.ACTIVE,
        ),
    )

    assert first_roster.status == RosterStatus.INACTIVE
    assert second_roster.status == RosterStatus.ACTIVE
    assert first_roster.jersey_number == second_roster.jersey_number == 12


def test_create_allows_same_active_jersey_in_different_seasons(db_session):
    team = _create_team(db_session)

    first_season = _create_season(db_session, team, "2025-26")
    second_season = _create_season(db_session, team, "2026-27")

    first_player = _create_player(db_session, "First Player")
    second_player = _create_player(db_session, "Second Player")

    first_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=first_season.id,
            player_id=first_player.id,
            jersey_number=12,
        ),
    )

    second_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=second_season.id,
            player_id=second_player.id,
            jersey_number=12,
        ),
    )

    assert first_roster.jersey_number == 12
    assert second_roster.jersey_number == 12


def test_get_season_roster_returns_existing_entry(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)
    player = _create_player(db_session)

    created_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=player.id,
        ),
    )

    roster = get_season_roster(
        db_session,
        created_roster.id,
    )

    assert roster.id == created_roster.id
    assert roster.season_id == season.id
    assert roster.player_id == player.id


def test_get_season_roster_raises_not_found(db_session):
    with pytest.raises(SeasonRosterNotFoundError):
        get_season_roster(db_session, 999999)


def test_list_season_rosters_returns_entries_in_id_order(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)

    first_player = _create_player(db_session, "First Player")
    second_player = _create_player(db_session, "Second Player")

    first_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=first_player.id,
        ),
    )

    second_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=second_player.id,
        ),
    )

    rosters = list_season_rosters(db_session)

    assert [roster.id for roster in rosters] == [
        first_roster.id,
        second_roster.id,
    ]


def test_update_season_roster_partial_update(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)
    player = _create_player(db_session)

    roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=player.id,
            jersey_number=12,
            position="Guard",
        ),
    )

    updated_roster = update_season_roster(
        db_session,
        roster.id,
        SeasonRosterUpdate(
            grade_level="Senior",
        ),
    )

    assert updated_roster.id == roster.id
    assert updated_roster.season_id == season.id
    assert updated_roster.player_id == player.id
    assert updated_roster.jersey_number == 12
    assert updated_roster.position == "Guard"
    assert updated_roster.grade_level == "Senior"
    assert updated_roster.status == RosterStatus.ACTIVE


def test_update_season_roster_can_clear_optional_field(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)
    player = _create_player(db_session)

    roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=player.id,
            position="Guard",
        ),
    )

    updated_roster = update_season_roster(
        db_session,
        roster.id,
        SeasonRosterUpdate(position=None),
    )

    assert updated_roster.position is None


def test_update_rejects_membership_conflict(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)

    first_player = _create_player(db_session, "First Player")
    second_player = _create_player(db_session, "Second Player")

    create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=first_player.id,
        ),
    )

    second_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=second_player.id,
        ),
    )

    with pytest.raises(SeasonRosterMembershipConflictError):
        update_season_roster(
            db_session,
            second_roster.id,
            SeasonRosterUpdate(
                player_id=first_player.id,
            ),
        )


def test_update_rejects_duplicate_active_jersey(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)

    first_player = _create_player(db_session, "First Player")
    second_player = _create_player(db_session, "Second Player")

    create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=first_player.id,
            jersey_number=12,
        ),
    )

    second_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=second_player.id,
            jersey_number=7,
        ),
    )

    with pytest.raises(SeasonRosterJerseyConflictError):
        update_season_roster(
            db_session,
            second_roster.id,
            SeasonRosterUpdate(
                jersey_number=12,
            ),
        )


def test_update_rejects_reactivating_conflicting_jersey(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)

    first_player = _create_player(db_session, "First Player")
    second_player = _create_player(db_session, "Second Player")

    create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=first_player.id,
            jersey_number=12,
            status=RosterStatus.ACTIVE,
        ),
    )

    inactive_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=second_player.id,
            jersey_number=12,
            status=RosterStatus.INACTIVE,
        ),
    )

    with pytest.raises(SeasonRosterJerseyConflictError):
        update_season_roster(
            db_session,
            inactive_roster.id,
            SeasonRosterUpdate(
                status=RosterStatus.ACTIVE,
            ),
        )


def test_update_rejects_missing_final_season(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)
    player = _create_player(db_session)

    roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=player.id,
        ),
    )

    with pytest.raises(SeasonNotFoundError):
        update_season_roster(
            db_session,
            roster.id,
            SeasonRosterUpdate(
                season_id=999999,
            ),
        )


def test_update_rejects_missing_final_player(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)
    player = _create_player(db_session)

    roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=player.id,
        ),
    )

    with pytest.raises(PlayerNotFoundError):
        update_season_roster(
            db_session,
            roster.id,
            SeasonRosterUpdate(
                player_id=999999,
            ),
        )


def test_update_rejects_none_status(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)
    player = _create_player(db_session)

    roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=player.id,
        ),
    )

    with pytest.raises(ValueError):
        update_season_roster(
            db_session,
            roster.id,
            SeasonRosterUpdate(status=None),
        )


def test_inactive_historical_membership_is_preserved(db_session):
    team = _create_team(db_session)
    season = _create_season(db_session, team)

    first_player = _create_player(db_session, "First Player")
    second_player = _create_player(db_session, "Second Player")

    first_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=first_player.id,
            jersey_number=12,
        ),
    )

    original_id = first_roster.id

    first_roster = update_season_roster(
        db_session,
        first_roster.id,
        SeasonRosterUpdate(
            status=RosterStatus.INACTIVE,
        ),
    )

    second_roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=second_player.id,
            jersey_number=12,
        ),
    )

    assert first_roster.id == original_id
    assert first_roster.status == RosterStatus.INACTIVE
    assert first_roster.jersey_number == 12
    assert second_roster.status == RosterStatus.ACTIVE
    assert second_roster.jersey_number == 12