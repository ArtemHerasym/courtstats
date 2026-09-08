from datetime import date

from app.models.game import (
    Game,
    GameStatus,
    VenueType,
)
from app.models.player import Player
from app.models.player_game_stats import (
    ParticipationStatus,
    PlayerGameStats,
)
from app.models.season import Season
from app.models.season_roster import (
    RosterStatus,
    SeasonRoster,
)
from app.models.team import Team


def _create_roster(
    db_session,
):
    team = Team(
        name="Roster Removal Team",
    )

    player = Player(
        full_name="Removal Player",
    )

    db_session.add_all(
        [
            team,
            player,
        ]
    )

    db_session.flush()

    season = Season(
        team_id=team.id,
        name="2033-2034",
    )

    db_session.add(season)
    db_session.flush()

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        jersey_number=8,
        status=RosterStatus.ACTIVE,
    )

    db_session.add(roster)
    db_session.commit()

    db_session.refresh(season)
    db_session.refresh(player)
    db_session.refresh(roster)

    return season, player, roster


def test_roster_page_shows_remove_from_season(
    logged_in_client,
    db_session,
):
    season, _, _ = _create_roster(
        db_session,
    )

    response = logged_in_client.get(
        (
            "/app/roster?"
            f"season_id={season.id}"
        )
    )

    assert response.status_code == 200

    assert (
        "Remove from Season"
        in response.text
    )


def test_remove_from_season_deletes_membership_only(
    authenticated_client,
    db_session,
):
    season, player, roster = (
        _create_roster(
            db_session,
        )
    )

    roster_id = roster.id
    player_id = player.id

    response = authenticated_client.post(
        (
            f"/app/roster/"
            f"{roster_id}/remove"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert (
        response.headers["location"]
        == (
            "/app/roster?"
            f"season_id={season.id}"
            "&removed=1"
        )
    )

    assert (
        db_session.get(
            SeasonRoster,
            roster_id,
        )
        is None
    )

    assert (
        db_session.get(
            Player,
            player_id,
        )
        is not None
    )


def test_remove_from_season_blocks_completed_game_history(
    authenticated_client,
    db_session,
):
    season, player, roster = (
        _create_roster(
            db_session,
        )
    )

    opponent = Team(
        name="Removal Opponent",
    )

    db_session.add(opponent)
    db_session.flush()

    game = Game(
        season_id=season.id,
        opponent_team_id=opponent.id,
        game_date=date(
            2033,
            12,
            1,
        ),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=50,
    )

    db_session.add(game)
    db_session.flush()

    stats = PlayerGameStats(
        game_id=game.id,
        season_roster_id=roster.id,
        participation_status=(
            ParticipationStatus.DID_NOT_PLAY
        ),
    )

    db_session.add(stats)
    db_session.commit()

    response = authenticated_client.post(
        (
            f"/app/roster/"
            f"{roster.id}/remove"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert (
        response.headers["location"]
        == (
            "/app/roster?"
            f"season_id={season.id}"
            "&remove_error=history"
        )
    )

    assert (
        db_session.get(
            SeasonRoster,
            roster.id,
        )
        is not None
    )

    assert (
        db_session.get(
            Player,
            player.id,
        )
        is not None
    )


def test_remove_from_season_requires_csrf(
    logged_in_client,
    db_session,
):
    _, _, roster = _create_roster(
        db_session,
    )

    response = logged_in_client.post(
        (
            f"/app/roster/"
            f"{roster.id}/remove"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 403

    assert (
        db_session.get(
            SeasonRoster,
            roster.id,
        )
        is not None
    )


def test_remove_from_season_requires_authentication(
    client,
):
    response = client.post(
        "/app/roster/999/remove",
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert (
        response.headers["location"]
        == "/login"
    )