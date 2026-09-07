import pytest

from app.models.player import Player
from app.models.season import Season
from app.models.season_roster import (
    RosterStatus,
    SeasonRoster,
)
from app.models.team import Team
from app.services.season import (
    SeasonNotFoundError,
)
from app.services.season_roster import (
    season_has_usable_game_roster,
)


def _create_season(
    db_session,
) -> Season:
    team = Team(
        name="Roster Availability Team",
    )

    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    season = Season(
        team_id=team.id,
        name="2027-2028",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    return season


def _add_roster_player(
    db_session,
    season: Season,
    *,
    name: str,
    status: RosterStatus,
) -> SeasonRoster:
    player = Player(
        full_name=name,
    )

    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        status=status,
    )

    db_session.add(roster)
    db_session.commit()
    db_session.refresh(roster)

    return roster


def test_season_without_roster_is_not_usable(
    db_session,
):
    season = _create_season(
        db_session
    )

    assert (
        season_has_usable_game_roster(
            db_session,
            season.id,
        )
        is False
    )


def test_active_roster_player_makes_season_usable(
    db_session,
):
    season = _create_season(
        db_session
    )

    _add_roster_player(
        db_session,
        season,
        name="Active Player",
        status=RosterStatus.ACTIVE,
    )

    assert (
        season_has_usable_game_roster(
            db_session,
            season.id,
        )
        is True
    )


def test_inactive_only_roster_is_not_usable(
    db_session,
):
    season = _create_season(
        db_session
    )

    _add_roster_player(
        db_session,
        season,
        name="Inactive Player",
        status=RosterStatus.INACTIVE,
    )

    assert (
        season_has_usable_game_roster(
            db_session,
            season.id,
        )
        is False
    )


def test_left_team_only_roster_is_not_usable(
    db_session,
):
    season = _create_season(
        db_session
    )

    _add_roster_player(
        db_session,
        season,
        name="Former Player",
        status=RosterStatus.LEFT_TEAM,
    )

    assert (
        season_has_usable_game_roster(
            db_session,
            season.id,
        )
        is False
    )


def test_active_player_counts_even_with_inactive_players(
    db_session,
):
    season = _create_season(
        db_session
    )

    _add_roster_player(
        db_session,
        season,
        name="Inactive Player",
        status=RosterStatus.INACTIVE,
    )

    _add_roster_player(
        db_session,
        season,
        name="Active Player",
        status=RosterStatus.ACTIVE,
    )

    assert (
        season_has_usable_game_roster(
            db_session,
            season.id,
        )
        is True
    )


def test_usable_roster_query_rejects_missing_season(
    db_session,
):
    with pytest.raises(
        SeasonNotFoundError
    ):
        season_has_usable_game_roster(
            db_session,
            999999,
        )