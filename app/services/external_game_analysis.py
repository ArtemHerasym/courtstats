from sqlalchemy import select
from sqlalchemy.orm import Session

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
from app.models.external_game import ExternalGame
from app.models.external_game_player_stats import (
    ExternalGamePlayerStats,
)
from app.models.game import GameStatus
from app.models.player_game_stats import (
    ParticipationStatus,
)
from app.services.external_game import (
    ExternalGameNotFoundError,
)


class ExternalGameNotCompletedError(Exception):
    pass


class ExternalGameAnalysisSelectionError(Exception):
    pass


RAW_STAT_FIELDS = (
    "three_point_attempts",
    "three_point_makes",
    "two_point_attempts",
    "two_point_makes",
    "free_throw_attempts",
    "free_throw_makes",
    "turnovers",
    "assists",
    "offensive_rebounds",
    "defensive_rebounds",
    "steals",
    "deflections",
    "personal_fouls",
)


def _empty_raw_totals() -> dict[str, int]:
    return {
        field: 0
        for field in RAW_STAT_FIELDS
    }


def _get_completed_external_game(
    db: Session,
    external_game_id: int,
) -> ExternalGame:
    game = db.get(
        ExternalGame,
        external_game_id,
    )

    if game is None:
        raise ExternalGameNotFoundError(
            (
                "External game with ID "
                f"{external_game_id} was not found."
            )
        )

    if game.status != GameStatus.COMPLETED:
        raise ExternalGameNotCompletedError(
            (
                "External game must be completed "
                "before it can be analyzed."
            )
        )

    if game.opponent_score is None:
        raise ValueError(
            (
                "Completed external game requires "
                "an opponent score."
            )
        )

    return game


def _get_selected_completed_games(
    db: Session,
    external_game_ids: list[int],
) -> list[ExternalGame]:
    if not external_game_ids:
        raise ExternalGameAnalysisSelectionError(
            (
                "Select at least one completed "
                "external game."
            )
        )

    if len(external_game_ids) != len(
        set(external_game_ids)
    ):
        raise ExternalGameAnalysisSelectionError(
            (
                "Duplicate external game "
                "selections are not allowed."
            )
        )

    games = [
        _get_completed_external_game(
            db,
            external_game_id,
        )
        for external_game_id
        in external_game_ids
    ]

    return games


def _get_stats_rows(
    db: Session,
    external_game_ids: list[int],
) -> list[ExternalGamePlayerStats]:
    statement = (
        select(ExternalGamePlayerStats)
        .where(
            ExternalGamePlayerStats.external_game_id.in_(
                external_game_ids
            )
        )
        .order_by(
            ExternalGamePlayerStats.external_game_id,
            ExternalGamePlayerStats.id,
        )
    )

    return list(
        db.scalars(statement).all()
    )


def _aggregate_raw_stats(
    stats_rows: list[ExternalGamePlayerStats],
) -> dict[str, int]:
    totals = _empty_raw_totals()

    for stats in stats_rows:
        for field in RAW_STAT_FIELDS:
            totals[field] += getattr(
                stats,
                field,
            )

    return totals


def _calculate_stat_summary(
    totals: dict[str, int],
) -> dict[str, int | float | None]:
    points = calculate_points(
        totals["two_point_makes"],
        totals["three_point_makes"],
        totals["free_throw_makes"],
    )

    rebounds = calculate_rebounds(
        totals["offensive_rebounds"],
        totals["defensive_rebounds"],
    )

    field_goal_makes = calculate_fgm(
        totals["two_point_makes"],
        totals["three_point_makes"],
    )

    field_goal_attempts = calculate_fga(
        totals["two_point_attempts"],
        totals["three_point_attempts"],
    )

    field_goal_percentage = (
        calculate_fg_percentage(
            totals["two_point_makes"],
            totals["three_point_makes"],
            totals["two_point_attempts"],
            totals["three_point_attempts"],
        )
    )

    two_point_percentage = (
        calculate_two_point_percentage(
            totals["two_point_makes"],
            totals["two_point_attempts"],
        )
    )

    three_point_percentage = (
        calculate_three_point_percentage(
            totals["three_point_makes"],
            totals["three_point_attempts"],
        )
    )

    free_throw_percentage = (
        calculate_free_throw_percentage(
            totals["free_throw_makes"],
            totals["free_throw_attempts"],
        )
    )

    true_shooting_percentage = (
        calculate_true_shooting_percentage(
            totals["two_point_makes"],
            totals["three_point_makes"],
            totals["free_throw_makes"],
            totals["two_point_attempts"],
            totals["three_point_attempts"],
            totals["free_throw_attempts"],
        )
    )

    assist_turnover_ratio = (
        calculate_assist_turnover_ratio(
            totals["assists"],
            totals["turnovers"],
        )
    )

    return {
        **totals,
        "points": points,
        "rebounds": rebounds,
        "field_goal_makes": (
            field_goal_makes
        ),
        "field_goal_attempts": (
            field_goal_attempts
        ),
        "field_goal_percentage": (
            field_goal_percentage
        ),
        "two_point_percentage": (
            two_point_percentage
        ),
        "three_point_percentage": (
            three_point_percentage
        ),
        "free_throw_percentage": (
            free_throw_percentage
        ),
        "true_shooting_percentage": (
            true_shooting_percentage
        ),
        "assist_turnover_ratio": (
            assist_turnover_ratio
        ),
    }


def _calculate_game_summary(
    stats_rows: list[ExternalGamePlayerStats],
    opponent_score: int,
) -> dict:
    totals = _aggregate_raw_stats(
        stats_rows
    )

    summary = _calculate_stat_summary(
        totals
    )

    team_score = summary["points"]

    score_margin = calculate_score_margin(
        team_score,
        opponent_score,
    )

    result = determine_game_result(
        team_score,
        opponent_score,
    )

    return {
        **summary,
        "team_score": team_score,
        "opponent_score": opponent_score,
        "score_margin": score_margin,
        "result": result,
    }


def _calculate_player_game_summary(
    stats: ExternalGamePlayerStats,
) -> dict:
    totals = {
        field: getattr(
            stats,
            field,
        )
        for field in RAW_STAT_FIELDS
    }

    return _calculate_stat_summary(
        totals
    )


def get_external_game_report(
    db: Session,
    external_game_id: int,
) -> dict:
    game = _get_completed_external_game(
        db,
        external_game_id,
    )

    stats_rows = _get_stats_rows(
        db,
        [game.id],
    )

    summary = _calculate_game_summary(
        stats_rows,
        game.opponent_score,
    )

    player_rows: list[dict] = []

    for stats in stats_rows:
        player_rows.append(
            {
                "player_id": stats.player_id,
                "player_name": (
                    stats.player.display_name
                    or stats.player.full_name
                ),
                "participation_status": (
                    stats.participation_status
                ),
                **_calculate_player_game_summary(
                    stats
                ),
            }
        )

    player_rows.sort(
        key=lambda row: (
            row["player_name"].lower(),
            row["player_id"],
        )
    )

    return {
        "game": game,
        "summary": summary,
        "player_rows": player_rows,
    }


def _build_game_breakdown(
    games: list[ExternalGame],
    stats_rows: list[
        ExternalGamePlayerStats
    ],
) -> list[dict]:
    rows_by_game_id: dict[
        int,
        list[ExternalGamePlayerStats],
    ] = {
        game.id: []
        for game in games
    }

    for stats in stats_rows:
        rows_by_game_id[
            stats.external_game_id
        ].append(stats)

    breakdown: list[dict] = []

    for game in games:
        summary = _calculate_game_summary(
            rows_by_game_id[game.id],
            game.opponent_score,
        )

        breakdown.append(
            {
                "external_game_id": game.id,
                "game_name": game.name,
                "game_date": game.game_date,
                "opponent_name": (
                    game.opponent_team.name
                ),
                "venue_type": (
                    game.venue_type
                ),
                "team_score": (
                    summary["team_score"]
                ),
                "opponent_score": (
                    game.opponent_score
                ),
                "result": (
                    summary["result"]
                ),
                "score_margin": (
                    summary["score_margin"]
                ),
            }
        )

    breakdown.sort(
        key=lambda row: (
            row["game_date"],
            row["external_game_id"],
        )
    )

    return breakdown


def _build_team_aggregate(
    games: list[ExternalGame],
    stats_rows: list[
        ExternalGamePlayerStats
    ],
    game_breakdown: list[dict],
) -> dict:
    totals = _aggregate_raw_stats(
        stats_rows
    )

    stat_summary = _calculate_stat_summary(
        totals
    )

    games_played = len(games)

    wins = sum(
        row["result"] == "WIN"
        for row in game_breakdown
    )

    losses = sum(
        row["result"] == "LOSS"
        for row in game_breakdown
    )

    ties = sum(
        row["result"] == "TIE"
        for row in game_breakdown
    )

    opponent_points = sum(
        game.opponent_score
        for game in games
    )

    points = stat_summary["points"]
    rebounds = stat_summary["rebounds"]

    return {
        **stat_summary,
        "games_played": games_played,
        "wins": wins,
        "losses": losses,
        "ties": ties,
        "points_per_game": (
            points / games_played
        ),
        "opponent_points": (
            opponent_points
        ),
        "opponent_points_per_game": (
            opponent_points
            / games_played
        ),
        "point_differential": (
            points - opponent_points
        ),
        "point_differential_per_game": (
            (points - opponent_points)
            / games_played
        ),
        "rebounds_per_game": (
            rebounds / games_played
        ),
        "assists_per_game": (
            totals["assists"]
            / games_played
        ),
        "turnovers_per_game": (
            totals["turnovers"]
            / games_played
        ),
        "steals_per_game": (
            totals["steals"]
            / games_played
        ),
        "deflections_per_game": (
            totals["deflections"]
            / games_played
        ),
        "personal_fouls_per_game": (
            totals["personal_fouls"]
            / games_played
        ),
    }


def _build_player_aggregates(
    stats_rows: list[
        ExternalGamePlayerStats
    ],
) -> list[dict]:
    player_data: dict[int, dict] = {}

    for stats in stats_rows:
        player_id = stats.player_id

        if player_id not in player_data:
            player_data[player_id] = {
                "player_id": player_id,
                "player_name": (
                    stats.player.display_name
                    or stats.player.full_name
                ),
                "games_played": 0,
                "totals": (
                    _empty_raw_totals()
                ),
            }

        row = player_data[player_id]

        if (
            stats.participation_status
            == ParticipationStatus.PLAYED
        ):
            row["games_played"] += 1

        for field in RAW_STAT_FIELDS:
            row["totals"][field] += getattr(
                stats,
                field,
            )

    result: list[dict] = []

    for player in player_data.values():
        summary = _calculate_stat_summary(
            player["totals"]
        )

        games_played = (
            player["games_played"]
        )

        if games_played == 0:
            points_per_game = None
            rebounds_per_game = None
            assists_per_game = None
        else:
            points_per_game = (
                summary["points"]
                / games_played
            )

            rebounds_per_game = (
                summary["rebounds"]
                / games_played
            )

            assists_per_game = (
                summary["assists"]
                / games_played
            )

        result.append(
            {
                "player_id": (
                    player["player_id"]
                ),
                "player_name": (
                    player["player_name"]
                ),
                "games_played": (
                    games_played
                ),
                **summary,
                "points_per_game": (
                    points_per_game
                ),
                "rebounds_per_game": (
                    rebounds_per_game
                ),
                "assists_per_game": (
                    assists_per_game
                ),
            }
        )

    result.sort(
        key=lambda row: (
            row["points_per_game"] is None,
            -(
                row["points_per_game"]
                if row["points_per_game"]
                is not None
                else 0
            ),
            row["player_name"].lower(),
            row["player_id"],
        )
    )

    return result


def analyze_external_games(
    db: Session,
    external_game_ids: list[int],
) -> dict:
    games = _get_selected_completed_games(
        db,
        external_game_ids,
    )

    stats_rows = _get_stats_rows(
        db,
        [
            game.id
            for game in games
        ],
    )

    game_breakdown = (
        _build_game_breakdown(
            games,
            stats_rows,
        )
    )

    team_summary = (
        _build_team_aggregate(
            games,
            stats_rows,
            game_breakdown,
        )
    )

    player_rows = (
        _build_player_aggregates(
            stats_rows
        )
    )

    return {
        "selected_game_ids": [
            game.id
            for game in games
        ],
        "team_summary": team_summary,
        "player_rows": player_rows,
        "game_breakdown": game_breakdown,
    }