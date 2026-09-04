from app.models.external_game_player_stats import (
    ExternalGamePlayerStats,
)
from app.models.player_game_stats import (
    ParticipationStatus,
    PlayerGameStats,
)
from app.services.statistics import (
    calculate_game_summary,
    calculate_player_game_summary,
)


def _raw_stats() -> dict[str, int]:
    return {
        "three_point_attempts": 7,
        "three_point_makes": 3,
        "two_point_attempts": 9,
        "two_point_makes": 5,
        "free_throw_attempts": 6,
        "free_throw_makes": 4,
        "turnovers": 3,
        "assists": 6,
        "offensive_rebounds": 2,
        "defensive_rebounds": 5,
        "steals": 2,
        "deflections": 4,
        "personal_fouls": 2,
    }


def test_external_player_calculations_match_regular_player():
    raw_stats = _raw_stats()

    regular = PlayerGameStats(
        game_id=1,
        season_roster_id=1,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        **raw_stats,
    )

    external = ExternalGamePlayerStats(
        external_game_id=1,
        player_id=1,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        **raw_stats,
    )

    regular_summary = (
        calculate_player_game_summary(
            regular
        )
    )

    external_summary = (
        calculate_player_game_summary(
            external
        )
    )

    assert external_summary == regular_summary

    assert external_summary["points"] == 23
    assert external_summary["rebounds"] == 7
    assert external_summary["field_goal_makes"] == 8
    assert external_summary["field_goal_attempts"] == 16
    assert external_summary[
        "assist_turnover_ratio"
    ] == 2.0


def test_external_game_calculations_match_regular_game():
    raw_stats = _raw_stats()

    regular = PlayerGameStats(
        game_id=1,
        season_roster_id=1,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        **raw_stats,
    )

    external = ExternalGamePlayerStats(
        external_game_id=1,
        player_id=1,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        **raw_stats,
    )

    regular_summary = calculate_game_summary(
        [regular],
        opponent_score=20,
    )

    external_summary = calculate_game_summary(
        [external],
        opponent_score=20,
    )

    assert external_summary == regular_summary

    assert external_summary["team_score"] == 23
    assert external_summary["score_margin"] == 3
    assert external_summary["result"] == "WIN"