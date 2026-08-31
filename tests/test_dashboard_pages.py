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


def test_season_dashboard_renders_statistics_leaders_and_charts(
    client,
    db_session,
):
    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent = Team(
        name="Test Opponent",
        abbreviation="TEST",
    )

    player = Player(
        full_name="Dashboard Player",
    )

    db_session.add_all(
        [team, opponent, player]
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
        opponent_score=12,
    )

    db_session.add_all(
        [roster, game]
    )
    db_session.commit()

    stats = PlayerGameStats(
        game_id=game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_attempts=6,
        two_point_makes=3,
        three_point_attempts=4,
        three_point_makes=2,
        free_throw_attempts=4,
        free_throw_makes=3,
        offensive_rebounds=2,
        defensive_rebounds=3,
        assists=4,
        turnovers=2,
        steals=1,
        deflections=2,
        personal_fouls=2,
    )

    db_session.add(stats)
    db_session.commit()

    response = client.get(
        f"/app/seasons/{season.id}/dashboard"
    )

    assert response.status_code == 200

    html = response.text

    assert "Jordan Christian Preparatory" in html
    assert "2026-27" in html

    assert "1-0" in html
    assert "15.0" in html
    assert "12.0" in html
    assert "+3.0" in html

    assert "50.0%" in html
    assert "75.0%" in html

    assert "Dashboard Player" in html

    assert (
        f"/app/season-rosters/"
        f"{roster.id}/profile"
        in html
    )

    assert 'id="scoring-trend-chart"' in html
    assert 'id="score-comparison-chart"' in html
    assert 'id="shooting-trend-chart"' in html
    assert 'id="result-comparison-chart"' in html
    assert 'id="venue-comparison-chart"' in html
    assert 'id="player-scoring-chart"' in html

    assert 'id="season-chart-data"' in html
    assert 'id="season-comparison-data"' in html
    assert 'id="season-player-scoring-data"' in html

    assert "01/10 vs Test Opponent" in html


def test_season_dashboard_empty_state(
    client,
    db_session,
):
    team = Team(
        name="Empty Dashboard Team",
    )

    db_session.add(team)
    db_session.commit()

    season = Season(
        team_id=team.id,
        name="Empty Season",
    )

    db_session.add(season)
    db_session.commit()

    response = client.get(
        f"/app/seasons/{season.id}/dashboard"
    )

    assert response.status_code == 200

    assert (
        "No completed games yet"
        in response.text
    )

    assert (
        "Season statistics will appear "
        "after the first game is completed."
        in response.text
    )

    assert (
        'id="scoring-trend-chart"'
        not in response.text
    )

    assert (
        'id="season-chart-data"'
        not in response.text
    )


def test_season_dashboard_returns_404_for_missing_season(
    client,
):
    response = client.get(
        "/app/seasons/999999/dashboard"
    )

    assert response.status_code == 404

    assert (
        "Season not found."
        in response.text
    )