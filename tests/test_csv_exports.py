import csv
from datetime import date
from io import StringIO

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
from app.services.csv_exports import (
    build_game_csv,
    build_player_season_csv,
    build_season_csv,
)

def _create_completed_game(
    db_session,
    *,
    player_name: str = "Test Player",
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
        full_name=player_name,
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
        jersey_number=12,
        status=RosterStatus.ACTIVE,
    )

    game = Game(
        season_id=season.id,
        opponent_team_id=opponent.id,
        game_date=date(2026, 8, 28),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=12,
        notes="CSV export test",
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
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        three_point_attempts=4,
        three_point_makes=2,
        two_point_attempts=6,
        two_point_makes=3,
        free_throw_attempts=4,
        free_throw_makes=3,
        turnovers=2,
        assists=4,
        offensive_rebounds=2,
        defensive_rebounds=3,
        steals=1,
        deflections=2,
        personal_fouls=2,
    )

    db_session.add(stats)
    db_session.commit()

    db_session.refresh(game)

    return game


def test_build_game_csv_contains_report_data(
    db_session,
):
    game = _create_completed_game(
        db_session
    )

    csv_text = build_game_csv(
        db_session,
        game.id,
    )

    rows = list(
        csv.reader(
            StringIO(csv_text)
        )
    )

    assert ["Game"] in rows

    assert [
        "Team",
        "Jordan Christian Preparatory",
    ] in rows

    assert [
        "Opponent",
        "Test Opponent",
    ] in rows

    assert [
        "Season",
        "2026-27",
    ] in rows

    assert [
        "Date",
        "08/28/2026",
    ] in rows

    assert [
        "Team Score",
        "15",
    ] in rows

    assert [
        "Opponent Score",
        "12",
    ] in rows

    assert [
        "Result",
        "WIN",
    ] in rows

    assert [
        "Score Margin",
        "3",
    ] in rows

    assert [
        "FG",
        "5",
        "10",
        "50.0%",
    ] in rows

    assert [
        "FT",
        "3",
        "4",
        "75.0%",
    ] in rows

    assert [
        "True Shooting %",
        "63.8%",
    ] in rows

    assert [
        "Assist/Turnover Ratio",
        "2.00",
    ] in rows

    player_row = next(
        row
        for row in rows
        if row
        and row[0] == "Test Player"
    )

    assert player_row[1] == "12"
    assert player_row[2] == "PLAYED"
    assert player_row[3] == "15"

    assert "63.8%" in player_row
    assert "2.00" in player_row


def test_build_game_csv_escapes_special_characters(
    db_session,
):
    player_name = 'Smith, "AJ"'

    game = _create_completed_game(
        db_session,
        player_name=player_name,
    )

    csv_text = build_game_csv(
        db_session,
        game.id,
    )

    rows = list(
        csv.reader(
            StringIO(csv_text)
        )
    )

    player_row = next(
        row
        for row in rows
        if row
        and row[0] == player_name
    )

    assert player_row[0] == player_name


def test_game_csv_export_requires_authentication(
    client,
):
    response = client.get(
        "/exports/games/1.csv",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"]
        == "/login"
    )


def test_game_csv_export_returns_404_for_missing_game(
    authenticated_client,
):
    response = authenticated_client.get(
        "/exports/games/999999.csv"
    )

    assert response.status_code == 404
    assert (
        response.text
        == "Game not found."
    )


def test_game_csv_export_download_headers_and_data(
    authenticated_client,
    db_session,
):
    game = _create_completed_game(
        db_session
    )

    response = authenticated_client.get(
        f"/exports/games/{game.id}.csv"
    )

    assert response.status_code == 200

    assert response.headers[
        "content-type"
    ].startswith("text/csv")

    assert response.headers[
        "content-disposition"
    ] == (
        f'attachment; '
        f'filename="game-{game.id}-report.csv"'
    )

    rows = list(
        csv.reader(
            StringIO(response.text)
        )
    )

    assert [
        "Team",
        "Jordan Christian Preparatory",
    ] in rows

    assert [
        "Opponent",
        "Test Opponent",
    ] in rows

    assert [
        "Result",
        "WIN",
    ] in rows

    assert [
        "Team Score",
        "15",
    ] in rows

    player_row = next(
        row
        for row in rows
        if row
        and row[0] == "Test Player"
    )

    assert player_row[3] == "15"


def test_build_player_season_csv_contains_summary_and_game_log(
    db_session,
):
    game = _create_completed_game(
        db_session
    )

    roster = (
        game.player_game_stats[0]
        .season_roster
    )

    csv_text = build_player_season_csv(
        db_session,
        roster.id,
    )

    rows = list(
        csv.reader(
            StringIO(csv_text)
        )
    )

    assert [
        "Player",
        "Test Player",
    ] in rows

    assert [
        "Season",
        "2026-27",
    ] in rows

    assert [
        "Games Played",
        "1",
    ] in rows

    assert [
        "Points",
        "15",
    ] in rows

    assert [
        "Points Per Game",
        "15.0",
    ] in rows

    assert [
        "Rebounds",
        "5",
    ] in rows

    assert [
        "Assists",
        "4",
    ] in rows

    assert [
        "FG",
        "5",
        "10",
        "50.0%",
    ] in rows

    assert [
        "True Shooting %",
        "63.8%",
    ] in rows

    assert [
        "Assist/Turnover Ratio",
        "2.00",
    ] in rows

    game_row = next(
        row
        for row in rows
        if row
        and row[0] == "08/28/2026"
    )

    assert game_row[1] == "Test Opponent"
    assert game_row[2] == "HOME"
    assert game_row[3] == "WIN"
    assert game_row[4] == "15"
    assert game_row[5] == "12"
    assert game_row[6] == "PLAYED"
    assert game_row[7] == "15"


def test_player_season_csv_escapes_player_name(
    db_session,
):
    player_name = 'Smith, "AJ"'

    game = _create_completed_game(
        db_session,
        player_name=player_name,
    )

    roster = (
        game.player_game_stats[0]
        .season_roster
    )

    csv_text = build_player_season_csv(
        db_session,
        roster.id,
    )

    rows = list(
        csv.reader(
            StringIO(csv_text)
        )
    )

    assert [
        "Player",
        player_name,
    ] in rows


def test_player_season_csv_export_requires_authentication(
    client,
):
    response = client.get(
        "/exports/season-rosters/1.csv",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"]
        == "/login"
    )


def test_player_season_csv_export_returns_404_for_missing_roster(
    authenticated_client,
):
    response = authenticated_client.get(
        "/exports/season-rosters/"
        "999999.csv"
    )

    assert response.status_code == 404

    assert response.text == (
        "Season roster entry not found."
    )


def test_player_season_csv_export_headers_and_data(
    authenticated_client,
    db_session,
):
    game = _create_completed_game(
        db_session
    )

    roster = (
        game.player_game_stats[0]
        .season_roster
    )

    response = authenticated_client.get(
        f"/exports/season-rosters/"
        f"{roster.id}.csv"
    )

    assert response.status_code == 200

    assert response.headers[
        "content-type"
    ].startswith("text/csv")

    assert response.headers[
        "content-disposition"
    ] == (
        "attachment; "
        f'filename="player-season-'
        f'{roster.id}.csv"'
    )

    rows = list(
        csv.reader(
            StringIO(response.text)
        )
    )

    assert [
        "Player",
        "Test Player",
    ] in rows

    assert [
        "Games Played",
        "1",
    ] in rows

    assert [
        "Points",
        "15",
    ] in rows

    assert [
        "True Shooting %",
        "63.8%",
    ] in rows

    game_row = next(
        row
        for row in rows
        if row
        and row[0] == "08/28/2026"
    )

    assert game_row[1] == "Test Opponent"
    assert game_row[3] == "WIN"
    assert game_row[7] == "15"

def test_player_season_csv_export_excludes_draft_games(
    authenticated_client,
    db_session,
):
    completed_game = _create_completed_game(
        db_session
    )

    roster = (
        completed_game.player_game_stats[0]
        .season_roster
    )

    draft_opponent = Team(
        name="Draft CSV Opponent",
        abbreviation="DRAFTCSV",
    )

    db_session.add(draft_opponent)
    db_session.commit()
    db_session.refresh(draft_opponent)

    draft_game = Game(
        season_id=completed_game.season_id,
        opponent_team_id=draft_opponent.id,
        game_date=date(2026, 8, 29),
        venue_type=VenueType.AWAY,
        status=GameStatus.DRAFT,
        opponent_score=None,
        notes="Must not be exported",
    )

    db_session.add(draft_game)
    db_session.commit()
    db_session.refresh(draft_game)

    draft_stats = PlayerGameStats(
        game_id=draft_game.id,
        season_roster_id=roster.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        three_point_attempts=10,
        three_point_makes=10,
        two_point_attempts=10,
        two_point_makes=10,
        free_throw_attempts=10,
        free_throw_makes=10,
        turnovers=9,
        assists=9,
        offensive_rebounds=9,
        defensive_rebounds=9,
        steals=9,
        deflections=9,
        personal_fouls=5,
    )

    db_session.add(draft_stats)
    db_session.commit()

    response = authenticated_client.get(
        f"/exports/season-rosters/"
        f"{roster.id}.csv"
    )

    assert response.status_code == 200

    rows = list(
        csv.reader(
            StringIO(response.text)
        )
    )

    # Only the completed game counts.
    assert [
        "Games Played",
        "1",
    ] in rows

    assert [
        "Points",
        "15",
    ] in rows

    # The DRAFT game must not appear
    # anywhere in the completed-game log.
    assert "Draft CSV Opponent" not in (
        response.text
    )

    completed_game_rows = [
        row
        for row in rows
        if row
        and row[0] == "08/28/2026"
    ]

    assert len(completed_game_rows) == 1

    draft_game_rows = [
        row
        for row in rows
        if row
        and row[0] == "08/29/2026"
    ]

    assert draft_game_rows == []


def test_build_season_csv_contains_summary_and_completed_games(
    db_session,
):
    game = _create_completed_game(
        db_session
    )

    csv_text = build_season_csv(
        db_session,
        game.season_id,
    )

    rows = list(
        csv.reader(
            StringIO(csv_text)
        )
    )

    assert [
        "Team",
        "Jordan Christian Preparatory",
    ] in rows

    assert [
        "Season",
        "2026-27",
    ] in rows

    assert [
        "Games Played",
        "1",
    ] in rows

    assert [
        "Wins",
        "1",
    ] in rows

    assert [
        "Losses",
        "0",
    ] in rows

    assert [
        "Points",
        "15",
    ] in rows

    assert [
        "Opponent Points",
        "12",
    ] in rows

    assert [
        "Points Per Game",
        "15.0",
    ] in rows

    assert [
        "FG",
        "5",
        "10",
        "50.0%",
    ] in rows

    assert [
        "True Shooting %",
        "63.8%",
    ] in rows

    game_row = next(
        row
        for row in rows
        if row
        and row[0] == "08/28/2026"
    )

    assert game_row[1] == "Test Opponent"
    assert game_row[2] == "HOME"
    assert game_row[3] == "WIN"
    assert game_row[4] == "15"
    assert game_row[5] == "12"
    assert game_row[6] == "3"


def test_season_csv_export_requires_authentication(
    client,
):
    response = client.get(
        "/exports/seasons/1.csv",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"]
        == "/login"
    )


def test_season_csv_export_returns_404_for_missing_season(
    authenticated_client,
):
    response = authenticated_client.get(
        "/exports/seasons/999999.csv"
    )

    assert response.status_code == 404
    assert response.text == (
        "Season not found."
    )


def test_season_csv_export_headers_and_data(
    authenticated_client,
    db_session,
):
    game = _create_completed_game(
        db_session
    )

    response = authenticated_client.get(
        f"/exports/seasons/"
        f"{game.season_id}.csv"
    )

    assert response.status_code == 200

    assert response.headers[
        "content-type"
    ].startswith("text/csv")

    assert response.headers[
        "content-disposition"
    ] == (
        "attachment; "
        f'filename="season-'
        f'{game.season_id}-summary.csv"'
    )

    rows = list(
        csv.reader(
            StringIO(response.text)
        )
    )

    assert [
        "Team",
        "Jordan Christian Preparatory",
    ] in rows

    assert [
        "Season",
        "2026-27",
    ] in rows

    assert [
        "Games Played",
        "1",
    ] in rows

    assert [
        "Wins",
        "1",
    ] in rows

    assert [
        "Points",
        "15",
    ] in rows

    assert [
        "Opponent Points",
        "12",
    ] in rows

    game_row = next(
        row
        for row in rows
        if row
        and row[0] == "08/28/2026"
    )

    assert game_row[1] == "Test Opponent"
    assert game_row[2] == "HOME"
    assert game_row[3] == "WIN"
    assert game_row[4] == "15"
    assert game_row[5] == "12"


def test_season_csv_export_excludes_draft_games(
    authenticated_client,
    db_session,
):
    completed_game = _create_completed_game(
        db_session
    )

    roster = (
        completed_game.player_game_stats[0]
        .season_roster
    )

    draft_opponent = Team(
        name="Season Draft Opponent",
        abbreviation="SDRAFT",
    )

    db_session.add(draft_opponent)
    db_session.commit()
    db_session.refresh(draft_opponent)

    draft_game = Game(
        season_id=completed_game.season_id,
        opponent_team_id=draft_opponent.id,
        game_date=date(2026, 8, 29),
        venue_type=VenueType.AWAY,
        status=GameStatus.DRAFT,
        opponent_score=50,
        notes="Must not affect season export",
    )

    db_session.add(draft_game)
    db_session.commit()
    db_session.refresh(draft_game)

    draft_stats = PlayerGameStats(
        game_id=draft_game.id,
        season_roster_id=roster.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        three_point_attempts=10,
        three_point_makes=10,
        two_point_attempts=10,
        two_point_makes=10,
        free_throw_attempts=10,
        free_throw_makes=10,
        turnovers=9,
        assists=9,
        offensive_rebounds=9,
        defensive_rebounds=9,
        steals=9,
        deflections=9,
        personal_fouls=5,
    )

    db_session.add(draft_stats)
    db_session.commit()

    response = authenticated_client.get(
        f"/exports/seasons/"
        f"{completed_game.season_id}.csv"
    )

    assert response.status_code == 200

    rows = list(
        csv.reader(
            StringIO(response.text)
        )
    )

    # Only the completed game contributes.
    assert [
        "Games Played",
        "1",
    ] in rows

    assert [
        "Wins",
        "1",
    ] in rows

    assert [
        "Points",
        "15",
    ] in rows

    assert [
        "Opponent Points",
        "12",
    ] in rows

    # DRAFT game must not appear.
    assert (
        "Season Draft Opponent"
        not in response.text
    )

    draft_rows = [
        row
        for row in rows
        if row
        and row[0] == "08/29/2026"
    ]

    assert draft_rows == []


def test_game_report_links_to_csv_export(
    authenticated_client,
    db_session,
):
    game = _create_completed_game(
        db_session
    )

    response = authenticated_client.get(
        f"/app/games/{game.id}/report"
    )

    assert response.status_code == 200

    assert (
        f"/exports/games/{game.id}.csv"
        in response.text
    )


def test_player_profile_links_to_csv_export(
    authenticated_client,
    db_session,
):
    game = _create_completed_game(
        db_session
    )

    roster = (
        game.player_game_stats[0]
        .season_roster
    )

    response = authenticated_client.get(
        f"/app/season-rosters/"
        f"{roster.id}/profile"
    )

    assert response.status_code == 200

    assert (
        f"/exports/season-rosters/"
        f"{roster.id}.csv"
        in response.text
    )


def test_season_dashboard_links_to_csv_export(
    authenticated_client,
    db_session,
):
    game = _create_completed_game(
        db_session
    )

    response = authenticated_client.get(
        f"/app/seasons/"
        f"{game.season_id}/dashboard"
    )

    assert response.status_code == 200

    assert (
        f"/exports/seasons/"
        f"{game.season_id}.csv"
        in response.text
    )