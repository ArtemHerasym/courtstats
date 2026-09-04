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


def _setup_navigation_data(
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent = Team(
        name="Navigation Opponent",
        abbreviation="NAV",
    )

    player = Player(
        full_name="Navigation Player",
    )

    db_session.add_all(
        [
            team,
            opponent,
            player,
        ]
    )

    db_session.commit()

    season = Season(
        team_id=team.id,
        name="2026-27",
    )

    db_session.add(season)
    db_session.commit()

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        jersey_number=10,
        status=RosterStatus.ACTIVE,
    )

    game = Game(
        season_id=season.id,
        opponent_team_id=opponent.id,
        game_date=date(2026, 1, 10),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=10,
    )

    db_session.add_all(
        [
            roster,
            game,
        ]
    )

    db_session.commit()

    stats = PlayerGameStats(
        game_id=game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_attempts=3,
        two_point_makes=2,
        three_point_attempts=2,
        three_point_makes=1,
        free_throw_attempts=2,
        free_throw_makes=1,
        offensive_rebounds=1,
        defensive_rebounds=2,
        assists=2,
        turnovers=1,
        steals=1,
        deflections=1,
        personal_fouls=1,
    )

    db_session.add(stats)
    db_session.commit()

    return season, roster, game


def test_primary_navbar_links_are_enabled(
    authenticated_client,
):
    response = authenticated_client.get(
        "/"
    )

    assert response.status_code == 200

    html = response.text

    assert "http://testserver/" in html
    assert "/app/seasons" in html
    assert "/app/players" in html
    assert "/app/roster" in html
    assert "/app/games" in html
    assert "/app/games/new" in html

    assert 'action="/logout"' in html

    assert "nav-link-disabled" not in html
    assert "button-disabled" not in html


def test_primary_navigation_pages_load(
    authenticated_client,
):
    paths = [
        "/",
        "/app/seasons",
        "/app/players",
        "/app/roster",
        "/app/games",
        "/app/games/new",
    ]

    for path in paths:
        response = authenticated_client.get(
            path
        )

        assert response.status_code == 200


def test_season_page_links_to_related_workflows(
    authenticated_client,
    db_session,
):
    season, _, _ = _setup_navigation_data(
        db_session,
    )

    response = authenticated_client.get(
        "/app/seasons"
    )

    assert response.status_code == 200

    html = response.text

    assert (
        f"/app/seasons/"
        f"{season.id}/dashboard"
        in html
    )

    assert (
        f"/app/roster?season_id="
        f"{season.id}"
        in html
    )

    assert (
        f"/app/games?season_id="
        f"{season.id}"
        in html
    )

    assert (
        f"/exports/seasons/"
        f"{season.id}.csv"
        in html
    )


def test_roster_links_to_player_profile(
    authenticated_client,
    db_session,
):
    season, roster, _ = (
        _setup_navigation_data(
            db_session,
        )
    )

    response = authenticated_client.get(
        f"/app/roster?"
        f"season_id={season.id}"
    )

    assert response.status_code == 200

    profile_url = (
        f"/app/season-rosters/"
        f"{roster.id}/profile"
    )

    assert profile_url in response.text

    profile_response = (
        authenticated_client.get(
            profile_url
        )
    )

    assert profile_response.status_code == 200

    assert (
        "Navigation Player"
        in profile_response.text
    )


def test_games_page_links_to_stats_report_and_csv(
    authenticated_client,
    db_session,
):
    _, _, game = _setup_navigation_data(
        db_session,
    )

    response = authenticated_client.get(
        "/app/games"
    )

    assert response.status_code == 200

    html = response.text

    assert (
        f"/app/games/"
        f"{game.id}/stats"
        in html
    )

    report_url = (
        f"/app/games/"
        f"{game.id}/report"
    )

    assert report_url in html

    assert (
        f"/exports/games/"
        f"{game.id}.csv"
        in html
    )

    report_response = (
        authenticated_client.get(
            report_url
        )
    )

    assert report_response.status_code == 200


def test_players_page_links_to_profile(
    authenticated_client,
    db_session,
):
    _, roster, _ = _setup_navigation_data(
        db_session,
    )

    response = authenticated_client.get(
        "/app/players"
    )

    assert response.status_code == 200

    profile_url = (
        f"/app/season-rosters/"
        f"{roster.id}/profile"
    )

    assert profile_url in response.text


def test_season_dashboard_is_reachable_from_seasons(
    authenticated_client,
    db_session,
):
    season, _, _ = _setup_navigation_data(
        db_session,
    )

    seasons_response = (
        authenticated_client.get(
            "/app/seasons"
        )
    )

    assert seasons_response.status_code == 200

    dashboard_url = (
        f"/app/seasons/"
        f"{season.id}/dashboard"
    )

    assert (
        dashboard_url
        in seasons_response.text
    )

    dashboard_response = (
        authenticated_client.get(
            dashboard_url
        )
    )

    assert dashboard_response.status_code == 200


def test_anonymous_navigation_redirects_to_login(
    client,
):
    protected_paths = [
        "/",
        "/app/seasons",
        "/app/players",
        "/app/roster",
        "/app/games",
        "/app/games/new",
    ]

    for path in protected_paths:
        response = client.get(
            path,
            follow_redirects=False,
        )

        assert response.status_code == 303

        assert (
            response.headers["location"]
            == "/login"
        )