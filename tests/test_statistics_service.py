import pytest
from app.services.statistics import (
    _get_completed_player_stats,
    aggregate_game_raw_stats,
    calculate_game_summary,
    calculate_player_season_summary,
    calculate_team_season_summary,
)
from app.models.player_game_stats import (
    ParticipationStatus,
    PlayerGameStats,
)
from app.services.statistics import aggregate_game_raw_stats

from datetime import date

from app.models.game import Game, GameStatus, VenueType
from app.models.player import Player
from app.models.season import Season
from app.models.season_roster import RosterStatus, SeasonRoster
from app.models.team import Team
from app.services.statistics import _get_completed_player_stats



first = PlayerGameStats(
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

second = PlayerGameStats(
    participation_status=ParticipationStatus.PLAYED,
    three_point_attempts=3,
    three_point_makes=1,
    two_point_attempts=6,
    two_point_makes=3,
    free_throw_attempts=2,
    free_throw_makes=2,
    turnovers=1,
    assists=4,
    offensive_rebounds=1,
    defensive_rebounds=5,
    steals=2,
    deflections=1,
    personal_fouls=2,
)

result = aggregate_game_raw_stats([first, second])

def test_aggregate_game_raw_stats_returns_zero_totals_for_empty_list():
    return aggregate_game_raw_stats([])


def test_aggregate_game_raw_stats():
    first = PlayerGameStats(
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

    second = PlayerGameStats(
        participation_status=ParticipationStatus.PLAYED,
        three_point_attempts=3,
        three_point_makes=1,
        two_point_attempts=6,
        two_point_makes=3,
        free_throw_attempts=2,
        free_throw_makes=2,
        turnovers=1,
        assists=4,
        offensive_rebounds=1,
        defensive_rebounds=5,
        steals=2,
        deflections=1,
        personal_fouls=2,
    )

    result = aggregate_game_raw_stats(
        [first, second]
    )

    assert result["three_point_attempts"] == 8
    assert result["three_point_makes"] == 3
    assert result["two_point_attempts"] == 14
    assert result["two_point_makes"] == 7
    assert result["free_throw_attempts"] == 6
    assert result["free_throw_makes"] == 5
    assert result["turnovers"] == 3
    assert result["assists"] == 9
    assert result["offensive_rebounds"] == 3
    assert result["defensive_rebounds"] == 9
    assert result["steals"] == 3
    assert result["deflections"] == 3
    assert result["personal_fouls"] == 5


def test_aggregate_game_raw_stats_returns_zero_totals_for_empty_list():
    result = aggregate_game_raw_stats([])

    assert all(
        value == 0
        for value in result.values()
    )

def test_calculate_game_summary():
    first = PlayerGameStats(
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

    second = PlayerGameStats(
        participation_status=ParticipationStatus.PLAYED,
        three_point_attempts=3,
        three_point_makes=1,
        two_point_attempts=6,
        two_point_makes=3,
        free_throw_attempts=2,
        free_throw_makes=2,
        turnovers=1,
        assists=4,
        offensive_rebounds=1,
        defensive_rebounds=5,
        steals=2,
        deflections=1,
        personal_fouls=2,
    )

    result = calculate_game_summary(
        stats_rows=[first, second],
        opponent_score=24,
    )

    assert result["team_score"] == 28
    assert result["rebounds"] == 12

    assert result["field_goal_makes"] == 10
    assert result["field_goal_attempts"] == 22

    assert result["field_goal_percentage"] == pytest.approx(10 / 22)
    assert result["two_point_percentage"] == pytest.approx(7 / 14)
    assert result["three_point_percentage"] == pytest.approx(3 / 8)
    assert result["free_throw_percentage"] == pytest.approx(5 / 6)

    assert result["true_shooting_percentage"] == pytest.approx(
        28 / (2 * (22 + (0.44 * 6)))
    )

    assert result["assist_turnover_ratio"] == pytest.approx(3.0)

    assert result["score_margin"] == 4
    assert result["result"] == "WIN"

def test_calculate_game_summary_handles_zero_stats():
    result = calculate_game_summary(
        stats_rows=[],
        opponent_score=0,
    )

    assert result["team_score"] == 0
    assert result["rebounds"] == 0

    assert result["field_goal_makes"] == 0
    assert result["field_goal_attempts"] == 0

    assert result["field_goal_percentage"] is None
    assert result["two_point_percentage"] is None
    assert result["three_point_percentage"] is None
    assert result["free_throw_percentage"] is None
    assert result["true_shooting_percentage"] is None
    assert result["assist_turnover_ratio"] is None

    assert result["score_margin"] == 0
    assert result["result"] == "TIE"


def test_get_completed_player_stats_excludes_draft_games(
    db_session,
):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    player = Player(
        full_name="John Smith",
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

    completed_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=60,
    )

    draft_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.AWAY,
        status=GameStatus.DRAFT,
    )

    db_session.add_all(
        [
            roster,
            completed_game,
            draft_game,
        ]
    )
    db_session.commit()

    db_session.refresh(roster)
    db_session.refresh(completed_game)
    db_session.refresh(draft_game)

    completed_stats = PlayerGameStats(
        game_id=completed_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        assists=5,
    )

    draft_stats = PlayerGameStats(
        game_id=draft_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        assists=20,
    )

    db_session.add_all(
        [
            completed_stats,
            draft_stats,
        ]
    )
    db_session.commit()

    result = _get_completed_player_stats(
        db_session,
        roster.id,
    )

    assert len(result) == 1
    assert result[0].game_id == completed_game.id
    assert result[0].assists == 5

def test_calculate_player_season_summary_uses_combined_completed_game_percentages(
    db_session,
):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    player = Player(
        full_name="John Smith",
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

    first_completed_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=60,
    )

    second_completed_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.AWAY,
        status=GameStatus.COMPLETED,
        opponent_score=65,
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
            roster,
            first_completed_game,
            second_completed_game,
            draft_game,
        ]
    )
    db_session.commit()

    db_session.refresh(roster)
    db_session.refresh(first_completed_game)
    db_session.refresh(second_completed_game)
    db_session.refresh(draft_game)

    first_stats = PlayerGameStats(
        game_id=first_completed_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_makes=1,
        two_point_attempts=1,
    )

    second_stats = PlayerGameStats(
        game_id=second_completed_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_makes=1,
        two_point_attempts=9,
    )

    draft_stats = PlayerGameStats(
        game_id=draft_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_makes=9,
        two_point_attempts=9,
    )

    db_session.add_all(
        [
            first_stats,
            second_stats,
            draft_stats,
        ]
    )
    db_session.commit()

    result = calculate_player_season_summary(
        db_session,
        roster.id,
    )

    assert result["two_point_makes"] == 2
    assert result["two_point_attempts"] == 10

    assert result["field_goal_makes"] == 2
    assert result["field_goal_attempts"] == 10

    assert result["field_goal_percentage"] == pytest.approx(0.2)

    average_of_game_percentages = (
        (1 / 1) + (1 / 9)
    ) / 2

    assert result["field_goal_percentage"] != pytest.approx(
        average_of_game_percentages
    )

def test_calculate_team_season_summary_uses_completed_games_only(
    db_session,
):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    player = Player(
        full_name="John Smith",
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

    win_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=60,
    )

    loss_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.AWAY,
        status=GameStatus.COMPLETED,
        opponent_score=65,
    )

    tie_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.NEUTRAL,
        status=GameStatus.COMPLETED,
        opponent_score=50,
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
            roster,
            win_game,
            loss_game,
            tie_game,
            draft_game,
        ]
    )
    db_session.commit()

    db_session.refresh(roster)
    db_session.refresh(win_game)
    db_session.refresh(loss_game)
    db_session.refresh(tie_game)
    db_session.refresh(draft_game)

    win_stats = PlayerGameStats(
        game_id=win_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        free_throw_makes=70,
        free_throw_attempts=70,
    )

    loss_stats = PlayerGameStats(
        game_id=loss_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        free_throw_makes=55,
        free_throw_attempts=55,
    )

    tie_stats = PlayerGameStats(
        game_id=tie_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        free_throw_makes=50,
        free_throw_attempts=50,
    )

    draft_stats = PlayerGameStats(
        game_id=draft_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        free_throw_makes=100,
        free_throw_attempts=100,
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

    result = calculate_team_season_summary(
        db_session,
        season.id,
    )

    assert result["games_played"] == 3

    assert result["wins"] == 1
    assert result["losses"] == 1
    assert result["ties"] == 1

    assert result["points"] == 175
    assert result["opponent_points"] == 175
    assert result["point_differential"] == 0

    assert result["free_throw_makes"] == 175
    assert result["free_throw_attempts"] == 175
    assert result["free_throw_percentage"] == pytest.approx(1.0)

def test_player_season_games_played_excludes_dnp(
    db_session,
):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    player = Player(
        full_name="John Smith",
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

    played_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=60,
    )

    dnp_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.AWAY,
        status=GameStatus.COMPLETED,
        opponent_score=65,
    )

    db_session.add_all(
        [
            roster,
            played_game,
            dnp_game,
        ]
    )
    db_session.commit()

    db_session.refresh(roster)
    db_session.refresh(played_game)
    db_session.refresh(dnp_game)

    played_stats = PlayerGameStats(
        game_id=played_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        free_throw_makes=10,
        free_throw_attempts=10,
        assists=4,
        offensive_rebounds=2,
        defensive_rebounds=4,
    )

    dnp_stats = PlayerGameStats(
        game_id=dnp_game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.DID_NOT_PLAY,
    )

    db_session.add_all(
        [
            played_stats,
            dnp_stats,
        ]
    )
    db_session.commit()

    result = calculate_player_season_summary(
        db_session,
        roster.id,
    )

    assert result["games_played"] == 1

    assert result["points"] == 10
    assert result["assists"] == 4
    assert result["rebounds"] == 6

    assert result["points_per_game"] == pytest.approx(10.0)
    assert result["assists_per_game"] == pytest.approx(4.0)
    assert result["rebounds_per_game"] == pytest.approx(6.0)

def test_player_season_averages_return_none_with_zero_games_played(
    db_session,
):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    player = Player(
        full_name="John Smith",
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

    game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=60,
    )

    db_session.add_all(
        [
            roster,
            game,
        ]
    )
    db_session.commit()

    db_session.refresh(roster)
    db_session.refresh(game)

    stats = PlayerGameStats(
        game_id=game.id,
        season_roster_id=roster.id,
        participation_status=ParticipationStatus.DID_NOT_PLAY,
    )

    db_session.add(stats)
    db_session.commit()

    result = calculate_player_season_summary(
        db_session,
        roster.id,
    )

    assert result["games_played"] == 0

    assert result["points"] == 0
    assert result["assists"] == 0
    assert result["rebounds"] == 0

    assert result["points_per_game"] is None
    assert result["assists_per_game"] is None
    assert result["rebounds_per_game"] is None

def test_team_season_summary_handles_no_completed_games(
    db_session,
):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    db_session.add_all(
        [
            season_team,
            opponent_team,
        ]
    )
    db_session.commit()

    db_session.refresh(season_team)
    db_session.refresh(opponent_team)

    season = Season(
        team_id=season_team.id,
        name="2026-27",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    draft_game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.DRAFT,
    )

    db_session.add(draft_game)
    db_session.commit()

    result = calculate_team_season_summary(
        db_session,
        season.id,
    )

    assert result["games_played"] == 0

    assert result["wins"] == 0
    assert result["losses"] == 0
    assert result["ties"] == 0

    assert result["points"] == 0
    assert result["opponent_points"] == 0
    assert result["point_differential"] == 0

    assert result["field_goal_makes"] == 0
    assert result["field_goal_attempts"] == 0

    assert result["field_goal_percentage"] is None
    assert result["two_point_percentage"] is None
    assert result["three_point_percentage"] is None
    assert result["free_throw_percentage"] is None
    assert result["true_shooting_percentage"] is None
    assert result["assist_turnover_ratio"] is None