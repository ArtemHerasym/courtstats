from typing import Literal

from pydantic import BaseModel


class RawStatistics(BaseModel):
    three_point_attempts: int
    three_point_makes: int
    two_point_attempts: int
    two_point_makes: int
    free_throw_attempts: int
    free_throw_makes: int
    turnovers: int
    assists: int
    offensive_rebounds: int
    defensive_rebounds: int
    steals: int
    deflections: int
    personal_fouls: int


class GameStatisticsRead(RawStatistics):
    team_score: int
    rebounds: int

    field_goal_makes: int
    field_goal_attempts: int

    field_goal_percentage: float | None
    two_point_percentage: float | None
    three_point_percentage: float | None
    free_throw_percentage: float | None
    true_shooting_percentage: float | None
    assist_turnover_ratio: float | None

    opponent_score: int
    score_margin: int
    result: Literal["WIN", "LOSS", "TIE"]


class PlayerSeasonStatisticsRead(RawStatistics):
    points: int
    rebounds: int

    field_goal_makes: int
    field_goal_attempts: int

    field_goal_percentage: float | None
    two_point_percentage: float | None
    three_point_percentage: float | None
    free_throw_percentage: float | None
    true_shooting_percentage: float | None
    assist_turnover_ratio: float | None

    games_played: int

    points_per_game: float | None
    assists_per_game: float | None
    rebounds_per_game: float | None


class TeamSeasonStatisticsRead(RawStatistics):
    games_played: int

    wins: int
    losses: int
    ties: int

    points: int
    opponent_points: int
    point_differential: int
    rebounds: int

    field_goal_makes: int
    field_goal_attempts: int

    field_goal_percentage: float | None
    two_point_percentage: float | None
    three_point_percentage: float | None
    free_throw_percentage: float | None
    true_shooting_percentage: float | None
    assist_turnover_ratio: float | None