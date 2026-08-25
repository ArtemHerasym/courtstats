from app.models.player_game_stats import PlayerGameStats
from app.calculations.basketball import (
    calculate_assist_turnover_ratio,
    calculate_fga,
    calculate_fg_percentage,
    calculate_fgm,
    calculate_free_throw_percentage,
    calculate_points,
    calculate_rebounds,
    calculate_score_margin,
    calculate_three_point_percentage,
    calculate_true_shooting_percentage,
    calculate_two_point_percentage,
    determine_game_result,
)

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.game import Game, GameStatus
from app.models.player_game_stats import (
    ParticipationStatus,
    PlayerGameStats,
)
from app.services.season_roster import get_season_roster


def aggregate_game_raw_stats(
    stats_rows: list[PlayerGameStats],
) -> dict[str, int]:
    totals = {
        "three_point_attempts": 0,
        "three_point_makes": 0,
        "two_point_attempts": 0,
        "two_point_makes": 0,
        "free_throw_attempts": 0,
        "free_throw_makes": 0,
        "turnovers": 0,
        "assists": 0,
        "offensive_rebounds": 0,
        "defensive_rebounds": 0,
        "steals": 0,
        "deflections": 0,
        "personal_fouls": 0,
    }

    for stats in stats_rows:
        totals["three_point_attempts"] += stats.three_point_attempts
        totals["three_point_makes"] += stats.three_point_makes
        totals["two_point_attempts"] += stats.two_point_attempts
        totals["two_point_makes"] += stats.two_point_makes
        totals["free_throw_attempts"] += stats.free_throw_attempts
        totals["free_throw_makes"] += stats.free_throw_makes
        totals["turnovers"] += stats.turnovers
        totals["assists"] += stats.assists
        totals["offensive_rebounds"] += stats.offensive_rebounds
        totals["defensive_rebounds"] += stats.defensive_rebounds
        totals["steals"] += stats.steals
        totals["deflections"] += stats.deflections
        totals["personal_fouls"] += stats.personal_fouls

    return totals

def calculate_game_summary(
    stats_rows: list[PlayerGameStats],
    opponent_score: int,
) -> dict[str, int | float | str | None]:
    totals = aggregate_game_raw_stats(stats_rows)

    team_score = calculate_points(
        totals["two_point_makes"],
        totals["three_point_makes"],
        totals["free_throw_makes"],
    )

    rebounds = calculate_rebounds(
        totals["offensive_rebounds"],
        totals["defensive_rebounds"],
    )

    fgm = calculate_fgm(
        totals["two_point_makes"],
        totals["three_point_makes"],
    )

    fga = calculate_fga(
        totals["two_point_attempts"],
        totals["three_point_attempts"],
    )

    fg_percentage = calculate_fg_percentage(
        totals["two_point_makes"],
        totals["three_point_makes"],
        totals["two_point_attempts"],
        totals["three_point_attempts"],
    )

    two_point_percentage = calculate_two_point_percentage(
        totals["two_point_makes"],
        totals["two_point_attempts"],
    )

    three_point_percentage = calculate_three_point_percentage(
        totals["three_point_makes"],
        totals["three_point_attempts"],
    )

    free_throw_percentage = calculate_free_throw_percentage(
        totals["free_throw_makes"],
        totals["free_throw_attempts"],
    )

    true_shooting_percentage = calculate_true_shooting_percentage(
        totals["two_point_makes"],
        totals["three_point_makes"],
        totals["free_throw_makes"],
        totals["two_point_attempts"],
        totals["three_point_attempts"],
        totals["free_throw_attempts"],
    )

    assist_turnover_ratio = calculate_assist_turnover_ratio(
        totals["assists"],
        totals["turnovers"],
    )

    score_margin = calculate_score_margin(
        team_score,
        opponent_score,
    )

    game_result = determine_game_result(
        team_score,
        opponent_score,
    )

    return {
        **totals,
        "team_score": team_score,
        "rebounds": rebounds,
        "field_goal_makes": fgm,
        "field_goal_attempts": fga,
        "field_goal_percentage": fg_percentage,
        "two_point_percentage": two_point_percentage,
        "three_point_percentage": three_point_percentage,
        "free_throw_percentage": free_throw_percentage,
        "true_shooting_percentage": true_shooting_percentage,
        "assist_turnover_ratio": assist_turnover_ratio,
        "opponent_score": opponent_score,
        "score_margin": score_margin,
        "result": game_result,
    }

def _get_completed_player_stats(
    db: Session,
    season_roster_id: int,
) -> list[PlayerGameStats]:

    get_season_roster(
        db,
        season_roster_id,
    )

    statement = (
        select(PlayerGameStats)
        .join(
            Game,
            PlayerGameStats.game_id == Game.id,
        )
        .where(
            PlayerGameStats.season_roster_id == season_roster_id,
            Game.status == GameStatus.COMPLETED,
        )
        .order_by(
            Game.game_date,
            Game.id,
        )
    )

    return list(
        db.scalars(statement).all()
    )

def calculate_player_season_summary(
    db: Session,
    season_roster_id: int,
) -> dict[str, int | float | None]:
    stats_rows = _get_completed_player_stats(
        db,
        season_roster_id,
    )

    games_played = sum(
        1
        for stats in stats_rows
        if stats.participation_status == ParticipationStatus.PLAYED
    )

    totals = aggregate_game_raw_stats(stats_rows)

    points = calculate_points(
        totals["two_point_makes"],
        totals["three_point_makes"],
        totals["free_throw_makes"],
    )

    rebounds = calculate_rebounds(
        totals["offensive_rebounds"],
        totals["defensive_rebounds"],
    )

    if games_played == 0:
        points_per_game = None
        assists_per_game = None
        rebounds_per_game = None
    else:
        points_per_game = points / games_played
        assists_per_game = totals["assists"] / games_played
        rebounds_per_game = rebounds / games_played

    fgm = calculate_fgm(
        totals["two_point_makes"],
        totals["three_point_makes"],
    )

    fga = calculate_fga(
        totals["two_point_attempts"],
        totals["three_point_attempts"],
    )

    fg_percentage = calculate_fg_percentage(
        totals["two_point_makes"],
        totals["three_point_makes"],
        totals["two_point_attempts"],
        totals["three_point_attempts"],
    )

    two_point_percentage = calculate_two_point_percentage(
        totals["two_point_makes"],
        totals["two_point_attempts"],
    )

    three_point_percentage = calculate_three_point_percentage(
        totals["three_point_makes"],
        totals["three_point_attempts"],
    )

    free_throw_percentage = calculate_free_throw_percentage(
        totals["free_throw_makes"],
        totals["free_throw_attempts"],
    )

    true_shooting_percentage = calculate_true_shooting_percentage(
        totals["two_point_makes"],
        totals["three_point_makes"],
        totals["free_throw_makes"],
        totals["two_point_attempts"],
        totals["three_point_attempts"],
        totals["free_throw_attempts"],
    )

    assist_turnover_ratio = calculate_assist_turnover_ratio(
        totals["assists"],
        totals["turnovers"],
    )

    return {
        **totals,
        "points": points,
        "rebounds": rebounds,
        "field_goal_makes": fgm,
        "field_goal_attempts": fga,
        "field_goal_percentage": fg_percentage,
        "two_point_percentage": two_point_percentage,
        "three_point_percentage": three_point_percentage,
        "free_throw_percentage": free_throw_percentage,
        "true_shooting_percentage": true_shooting_percentage,
        "assist_turnover_ratio": assist_turnover_ratio,
        "games_played": games_played,
        "points_per_game": points_per_game,
        "assists_per_game": assists_per_game,
        "rebounds_per_game": rebounds_per_game,
    }


def _get_completed_season_games(
    db: Session,
    season_id: int,
) -> list[Game]:
    statement = (
        select(Game)
        .where(
            Game.season_id == season_id,
            Game.status == GameStatus.COMPLETED,
        )
        .order_by(
            Game.game_date,
            Game.id,
        )
    )

    return list(
        db.scalars(statement).all()
    )

def calculate_team_season_summary(
    db: Session,
    season_id: int,
) -> dict[str, int | float | None]:
    games = _get_completed_season_games(
        db,
        season_id,
    )

    all_stats_rows: list[PlayerGameStats] = []

    for game in games:
        all_stats_rows.extend(
            game.player_game_stats
        )

    totals = aggregate_game_raw_stats(
        all_stats_rows
    )

    points = calculate_points(
        totals["two_point_makes"],
        totals["three_point_makes"],
        totals["free_throw_makes"],
    )

    rebounds = calculate_rebounds(
        totals["offensive_rebounds"],
        totals["defensive_rebounds"],
    )

    fgm = calculate_fgm(
        totals["two_point_makes"],
        totals["three_point_makes"],
    )

    fga = calculate_fga(
        totals["two_point_attempts"],
        totals["three_point_attempts"],
    )

    fg_percentage = calculate_fg_percentage(
        totals["two_point_makes"],
        totals["three_point_makes"],
        totals["two_point_attempts"],
        totals["three_point_attempts"],
    )

    two_point_percentage = calculate_two_point_percentage(
        totals["two_point_makes"],
        totals["two_point_attempts"],
    )

    three_point_percentage = calculate_three_point_percentage(
        totals["three_point_makes"],
        totals["three_point_attempts"],
    )

    free_throw_percentage = calculate_free_throw_percentage(
        totals["free_throw_makes"],
        totals["free_throw_attempts"],
    )

    true_shooting_percentage = calculate_true_shooting_percentage(
        totals["two_point_makes"],
        totals["three_point_makes"],
        totals["free_throw_makes"],
        totals["two_point_attempts"],
        totals["three_point_attempts"],
        totals["free_throw_attempts"],
    )

    assist_turnover_ratio = calculate_assist_turnover_ratio(
        totals["assists"],
        totals["turnovers"],
    )

    wins = 0
    losses = 0
    ties = 0
    opponent_points = 0

    for game in games:
        assert game.opponent_score is not None

        game_summary = calculate_game_summary(
            game.player_game_stats,
            game.opponent_score,
        )

        opponent_points += game.opponent_score

        if game_summary["result"] == "WIN":
            wins += 1
        elif game_summary["result"] == "LOSS":
            losses += 1
        else:
            ties += 1

    point_differential = points - opponent_points

    return {
        **totals,
        "games_played": len(games),
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "points": points,
        "opponent_points": opponent_points,
        "point_differential": point_differential,
        "rebounds": rebounds,
        "field_goal_makes": fgm,
        "field_goal_attempts": fga,
        "field_goal_percentage": fg_percentage,
        "two_point_percentage": two_point_percentage,
        "three_point_percentage": three_point_percentage,
        "free_throw_percentage": free_throw_percentage,
        "true_shooting_percentage": true_shooting_percentage,
        "assist_turnover_ratio": assist_turnover_ratio,
    }