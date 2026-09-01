from datetime import date

import pytest

from app.models.game import Game, GameStatus, VenueType
from app.models.player import Player
from app.models.player_game_stats import (
    ParticipationStatus,
    PlayerGameStats,
)
from app.models.season import Season
from app.models.season_roster import RosterStatus, SeasonRoster
from app.models.team import Team


def _create_statistics_dependencies(db_session):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    player = Player(
        full_name="Stats Player",
    )

    db_session.add_all(
        [
            season_team,
            opponent_team,
            player,
        ]
    )
    db_session.commit()

    db_session.refresh(season_team)
    db_session.refresh(opponent_team)
    db_session.refresh(player)

    season = Season(
        team_id=season_team.id,
        name="2026-27",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        status=RosterStatus.ACTIVE,
    )

    db_session.add(roster)
    db_session.commit()
    db_session.refresh(roster)

    return season_team, opponent_team, season, roster


def test_game_statistics_route_returns_expected_summary(
    authenticated_client,
    db_session,
):
    (
        season_team,
        opponent_team,
        season,
        roster,
    ) = _create_statistics_dependencies(db_session)

    game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=24,
    )

    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)

    stats = PlayerGameStats(
        game_id=game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        three_point_attempts=5,
        three_point_makes=2,
        two_point_attempts=8,
        two_point_makes=4,
        free_throw_attempts=4,
        free_throw_makes=3,
        turnovers=2,
        assists=5,
        offensive_rebounds=2,
        defensive_rebounds=4,
        steals=1,
        deflections=2,
        personal_fouls=3,
    )

    db_session.add(stats)
    db_session.commit()

    response = authenticated_client.get(
        f"/statistics/games/{game.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["three_point_attempts"] == 5
    assert data["three_point_makes"] == 2
    assert data["two_point_attempts"] == 8
    assert data["two_point_makes"] == 4

    assert data["team_score"] == 17
    assert data["rebounds"] == 6

    assert data["field_goal_makes"] == 6
    assert data["field_goal_attempts"] == 13
    assert data["field_goal_percentage"] == pytest.approx(6 / 13)

    assert data["opponent_score"] == 24
    assert data["score_margin"] == -7
    assert data["result"] == "LOSS"


def test_game_statistics_route_returns_404_for_missing_game(
    authenticated_client,
):
    response = authenticated_client.get(
        "/statistics/games/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Game with ID 999999 was not found."
    )

def test_player_season_statistics_route_returns_expected_summary(
    authenticated_client,
    db_session,
):
    (
        season_team,
        opponent_team,
        season,
        roster,
    ) = _create_statistics_dependencies(db_session)

    completed_game_one = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=60,
    )

    completed_game_two = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.AWAY,
        status=GameStatus.COMPLETED,
        opponent_score=65,
    )

    dnp_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=55,
    )

    draft_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.NEUTRAL,
        status=GameStatus.DRAFT,
    )

    db_session.add_all(
        [
            completed_game_one,
            completed_game_two,
            dnp_game,
            draft_game,
        ]
    )
    db_session.commit()

    for game in [
        completed_game_one,
        completed_game_two,
        dnp_game,
        draft_game,
    ]:
        db_session.refresh(game)

    first_stats = PlayerGameStats(
        game_id=completed_game_one.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_attempts=1,
        two_point_makes=1,
        assists=4,
        offensive_rebounds=1,
        defensive_rebounds=3,
    )

    second_stats = PlayerGameStats(
        game_id=completed_game_two.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_attempts=9,
        two_point_makes=1,
        assists=2,
        offensive_rebounds=2,
        defensive_rebounds=2,
    )

    dnp_stats = PlayerGameStats(
        game_id=dnp_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.DID_NOT_PLAY,
    )

    draft_stats = PlayerGameStats(
        game_id=draft_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_attempts=10,
        two_point_makes=10,
        assists=20,
    )

    db_session.add_all(
        [
            first_stats,
            second_stats,
            dnp_stats,
            draft_stats,
        ]
    )
    db_session.commit()

    response = authenticated_client.get(
        f"/statistics/seasons-rosters/{roster.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["games_played"] == 2

    assert data["two_point_makes"] == 2
    assert data["two_point_attempts"] == 10

    assert data["field_goal_makes"] == 2
    assert data["field_goal_attempts"] == 10

    assert data["field_goal_percentage"] == pytest.approx(0.2)
    assert data["two_point_percentage"] == pytest.approx(0.2)

    assert data["points"] == 4
    assert data["points_per_game"] == pytest.approx(2.0)

    assert data["assists"] == 6
    assert data["assists_per_game"] == pytest.approx(3.0)

    assert data["rebounds"] == 8
    assert data["rebounds_per_game"] == pytest.approx(4.0)


def test_player_season_statistics_route_returns_404_for_missing_roster(
    authenticated_client,
):
    response = authenticated_client.get(
        "/statistics/seasons-rosters/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season roster entry with ID 999999 was not found."
    )


def test_team_season_statistics_route_returns_expected_summary(
    authenticated_client,
    db_session,
):
    (
        season_team,
        opponent_team,
        season,
        roster,
    ) = _create_statistics_dependencies(db_session)

    win_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=6,
    )

    loss_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.AWAY,
        status=GameStatus.COMPLETED,
        opponent_score=10,
    )

    tie_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.NEUTRAL,
        status=GameStatus.COMPLETED,
        opponent_score=6,
    )

    draft_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.DRAFT,
    )

    db_session.add_all(
        [
            win_game,
            loss_game,
            tie_game,
            draft_game,
        ]
    )
    db_session.commit()

    for game in [
        win_game,
        loss_game,
        tie_game,
        draft_game,
    ]:
        db_session.refresh(game)

    win_stats = PlayerGameStats(
        game_id=win_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_attempts=8,
        two_point_makes=4,
        assists=3,
        offensive_rebounds=1,
        defensive_rebounds=3,
    )

    loss_stats = PlayerGameStats(
        game_id=loss_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_attempts=10,
        two_point_makes=2,
        assists=2,
        offensive_rebounds=2,
        defensive_rebounds=2,
    )

    tie_stats = PlayerGameStats(
        game_id=tie_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_attempts=6,
        two_point_makes=3,
        assists=1,
        offensive_rebounds=1,
        defensive_rebounds=2,
    )

    draft_stats = PlayerGameStats(
        game_id=draft_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_attempts=10,
        two_point_makes=10,
        assists=20,
        offensive_rebounds=10,
        defensive_rebounds=10,
    )

    db_session.add_all(
        [
            win_stats,
            loss_stats,
            tie_stats,
            draft_stats,
        ]
    )
    db_session.commit()

    response = authenticated_client.get(
        f"/statistics/seasons/{season.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["games_played"] == 3
    assert data["wins"] == 1
    assert data["losses"] == 1
    assert data["ties"] == 1

    assert data["points"] == 18
    assert data["opponent_points"] == 22
    assert data["point_differential"] == -4

    assert data["two_point_makes"] == 9
    assert data["two_point_attempts"] == 24

    assert data["field_goal_makes"] == 9
    assert data["field_goal_attempts"] == 24

    assert data["field_goal_percentage"] == pytest.approx(9 / 24)
    assert data["two_point_percentage"] == pytest.approx(9 / 24)

    assert data["assists"] == 6
    assert data["rebounds"] == 11


def test_team_season_statistics_route_returns_empty_summary(
    authenticated_client,
    db_session,
):
    (
        season_team,
        opponent_team,
        season,
        roster,
    ) = _create_statistics_dependencies(db_session)

    draft_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.DRAFT,
    )

    db_session.add(draft_game)
    db_session.commit()
    db_session.refresh(draft_game)

    draft_stats = PlayerGameStats(
        game_id=draft_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_attempts=10,
        two_point_makes=10,
        assists=20,
    )

    db_session.add(draft_stats)
    db_session.commit()

    response = authenticated_client.get(
        f"/statistics/seasons/{season.id}"
    )

    assert response.status_code == 200

    data = response.json()

    assert data["games_played"] == 0

    assert data["wins"] == 0
    assert data["losses"] == 0
    assert data["ties"] == 0

    assert data["points"] == 0
    assert data["opponent_points"] == 0
    assert data["point_differential"] == 0

    assert data["field_goal_makes"] == 0
    assert data["field_goal_attempts"] == 0

    assert data["field_goal_percentage"] is None
    assert data["two_point_percentage"] is None
    assert data["three_point_percentage"] is None
    assert data["free_throw_percentage"] is None
    assert data["true_shooting_percentage"] is None
    assert data["assist_turnover_ratio"] is None


def test_team_season_statistics_route_returns_404_for_missing_season(
    authenticated_client,
):
    response = authenticated_client.get(
        "/statistics/seasons/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season with ID 999999 was not found."
    )