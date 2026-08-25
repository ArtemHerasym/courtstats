import pytest

from app.calculations.basketball import (
    calculate_fga,
    calculate_fg_percentage,
    calculate_fgm,
    calculate_free_throw_percentage,
    calculate_points,
    calculate_rebounds,
    calculate_three_point_percentage,
    calculate_two_point_percentage,
    calculate_assist_turnover_ratio,
    calculate_true_shooting_percentage,
    calculate_score_margin,
    determine_game_result,
)

def test_calculate_points():
    result = calculate_points(
        two_point_makes=4,
        three_point_makes=3,
        free_throw_makes=5,
    )

    assert result == 22


def test_calculate_rebounds():
    result = calculate_rebounds(
        offensive_rebounds=3,
        defensive_rebounds=7,
    )

    assert result == 10


def test_calculate_fgm():
    result = calculate_fgm(
        two_point_makes=5,
        three_point_makes=2,
    )

    assert result == 7


def test_calculate_fga():
    result = calculate_fga(
        two_point_attempts=11,
        three_point_attempts=6,
    )

    assert result == 17


def test_basic_calculations_return_zero_for_zero_inputs():
    assert calculate_points(0, 0, 0) == 0
    assert calculate_rebounds(0, 0) == 0
    assert calculate_fgm(0, 0) == 0
    assert calculate_fga(0, 0) == 0


def test_calculate_fg_percentage():
    result = calculate_fg_percentage(
        two_point_makes=4,
        three_point_makes=2,
        two_point_attempts=8,
        three_point_attempts=4,
    )

    assert result == pytest.approx(0.5)


def test_calculate_two_point_percentage():
    result = calculate_two_point_percentage(
        two_point_makes=5,
        two_point_attempts=10,
    )

    assert result == pytest.approx(0.5)


def test_calculate_three_point_percentage():
    result = calculate_three_point_percentage(
        three_point_makes=3,
        three_point_attempts=8,
    )

    assert result == pytest.approx(0.375)


def test_calculate_free_throw_percentage():
    result = calculate_free_throw_percentage(
        free_throw_makes=7,
        free_throw_attempts=10,
    )

    assert result == pytest.approx(0.7)


def test_shooting_percentages_return_none_for_zero_attempts():
    assert calculate_fg_percentage(
        two_point_makes=0,
        three_point_makes=0,
        two_point_attempts=0,
        three_point_attempts=0,
    ) is None

    assert calculate_two_point_percentage(
        two_point_makes=0,
        two_point_attempts=0,
    ) is None

    assert calculate_three_point_percentage(
        three_point_makes=0,
        three_point_attempts=0,
    ) is None

    assert calculate_free_throw_percentage(
        free_throw_makes=0,
        free_throw_attempts=0,
    ) is None

def test_calculate_true_shooting_percentage():
    result = calculate_true_shooting_percentage(
        two_point_makes=4,
        three_point_makes=2,
        free_throw_makes=5,
        two_point_attempts=8,
        three_point_attempts=4,
        free_throw_attempts=6,
    )

    expected = 19 / (2 * (12 + (0.44 * 6)))

    assert result == pytest.approx(expected)


def test_true_shooting_percentage_returns_none_for_zero_denominator():
    result = calculate_true_shooting_percentage(
        two_point_makes=0,
        three_point_makes=0,
        free_throw_makes=0,
        two_point_attempts=0,
        three_point_attempts=0,
        free_throw_attempts=0,
    )

    assert result is None


def test_calculate_assist_turnover_ratio():
    result = calculate_assist_turnover_ratio(
        assists=6,
        turnovers=3,
    )

    assert result == pytest.approx(2.0)


def test_assist_turnover_ratio_returns_assists_when_turnovers_are_zero():
    result = calculate_assist_turnover_ratio(
        assists=5,
        turnovers=0,
    )

    assert result == pytest.approx(5.0)


def test_assist_turnover_ratio_returns_none_when_both_are_zero():
    result = calculate_assist_turnover_ratio(
        assists=0,
        turnovers=0,
    )

    assert result is None

def test_calculate_score_margin():
    result = calculate_score_margin(
        team_score=78,
        opponent_score=70,
    )

    assert result == 8


def test_determine_game_result_returns_win():
    result = determine_game_result(
        team_score=78,
        opponent_score=70,
    )

    assert result == "WIN"


def test_determine_game_result_returns_loss():
    result = determine_game_result(
        team_score=65,
        opponent_score=72,
    )

    assert result == "LOSS"


def test_determine_game_result_returns_tie():
    result = determine_game_result(
        team_score=70,
        opponent_score=70,
    )

    assert result == "TIE"