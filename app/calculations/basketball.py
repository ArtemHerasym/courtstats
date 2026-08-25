def _calculate_percentage(
    makes: int,
    attempts: int,
) -> float | None:
    if attempts == 0:
        return None

    return makes / attempts


def calculate_points(
    two_point_makes: int,
    three_point_makes: int,
    free_throw_makes: int,
) -> int:
    return (
        (2 * two_point_makes)
        + (3 * three_point_makes)
        + free_throw_makes
    )


def calculate_rebounds(
    offensive_rebounds: int,
    defensive_rebounds: int,
) -> int:
    return offensive_rebounds + defensive_rebounds


def calculate_fgm(
    two_point_makes: int,
    three_point_makes: int,
) -> int:
    return two_point_makes + three_point_makes


def calculate_fga(
    two_point_attempts: int,
    three_point_attempts: int,
) -> int:
    return two_point_attempts + three_point_attempts


def calculate_fg_percentage(
    two_point_makes: int,
    three_point_makes: int,
    two_point_attempts: int,
    three_point_attempts: int,
) -> float | None:
    fgm = calculate_fgm(
        two_point_makes,
        three_point_makes,
    )

    fga = calculate_fga(
        two_point_attempts,
        three_point_attempts,
    )

    return _calculate_percentage(
        fgm,
        fga,
    )


def calculate_two_point_percentage(
    two_point_makes: int,
    two_point_attempts: int,
) -> float | None:
    return _calculate_percentage(
        two_point_makes,
        two_point_attempts,
    )


def calculate_three_point_percentage(
    three_point_makes: int,
    three_point_attempts: int,
) -> float | None:
    return _calculate_percentage(
        three_point_makes,
        three_point_attempts,
    )


def calculate_free_throw_percentage(
    free_throw_makes: int,
    free_throw_attempts: int,
) -> float | None:
    return _calculate_percentage(
        free_throw_makes,
        free_throw_attempts,
    )

def calculate_true_shooting_percentage(
    two_point_makes: int,
    three_point_makes: int,
    free_throw_makes: int,
    two_point_attempts: int,
    three_point_attempts: int,
    free_throw_attempts: int,
) -> float | None:
    points = calculate_points(
        two_point_makes,
        three_point_makes,
        free_throw_makes,
    )

    fga = calculate_fga(
        two_point_attempts,
        three_point_attempts,
    )

    denominator = 2 * (
        fga + (0.44 * free_throw_attempts)
    )

    if denominator == 0:
        return None

    return points / denominator


def calculate_assist_turnover_ratio(
    assists: int,
    turnovers: int,
) -> float | None:
    if assists == 0 and turnovers == 0:
        return None

    if turnovers == 0:
        return float(assists)

    return assists / turnovers

def calculate_score_margin(
    team_score: int,
    opponent_score: int,
) -> int:

    return team_score - opponent_score

def calculate_score_margin(
    team_score: int,
    opponent_score: int,
) -> int:
    return team_score - opponent_score


def determine_game_result(
    team_score: int,
    opponent_score: int,
) -> str:
    if team_score > opponent_score:
        return "WIN"

    if team_score < opponent_score:
        return "LOSS"

    return "TIE"