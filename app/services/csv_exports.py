import csv
from io import StringIO

from sqlalchemy.orm import Session

from app.core.templates import format_percentage
from app.services.game import get_game
from app.services.statistics import (
    calculate_player_season_summary,
    calculate_team_season_summary,
    get_game_player_summaries,
    get_game_statistics,
    get_player_completed_game_log,
    get_season_game_series,
)
from app.services.season_roster import (
    get_season_roster,
)
from app.services.season import get_season


def _format_ratio(
    value: float | None,
) -> str:
    if value is None:
        return ""

    return f"{value:.2f}"

def _format_average(
    value: float | None,
) -> str:
    if value is None:
        return ""

    return f"{value:.1f}"

def build_game_csv(
    db: Session,
    game_id: int,
) -> str:
    game = get_game(
        db,
        game_id,
    )

    summary = get_game_statistics(
        db,
        game_id,
    )

    player_rows = get_game_player_summaries(
        db,
        game_id,
    )

    output = StringIO(newline="")
    writer = csv.writer(output)

    # -----------------------------
    # Game metadata
    # -----------------------------
    writer.writerow(["Game"])
    writer.writerow(["Field", "Value"])

    writer.writerow(
        [
            "Team",
            game.season.team.name,
        ]
    )
    writer.writerow(
        [
            "Opponent",
            game.opponent_team.name,
        ]
    )
    writer.writerow(
        [
            "Season",
            game.season.name,
        ]
    )
    writer.writerow(
        [
            "Date",
            game.game_date.strftime(
                "%m/%d/%Y"
            ),
        ]
    )
    writer.writerow(
        [
            "Venue",
            game.venue_type.value,
        ]
    )
    writer.writerow(
        [
            "Status",
            game.status.value,
        ]
    )
    writer.writerow(
        [
            "Team Score",
            summary["team_score"],
        ]
    )
    writer.writerow(
        [
            "Opponent Score",
            summary["opponent_score"],
        ]
    )
    writer.writerow(
        [
            "Result",
            summary["result"],
        ]
    )
    writer.writerow(
        [
            "Score Margin",
            summary["score_margin"],
        ]
    )
    writer.writerow(
        [
            "Notes",
            game.notes or "",
        ]
    )

    writer.writerow([])

    # -----------------------------
    # Team summary
    # -----------------------------
    writer.writerow(["Team Summary"])
    writer.writerow(["Metric", "Value"])

    team_summary_rows = [
        ("Points", summary["team_score"]),
        ("Rebounds", summary["rebounds"]),
        ("Assists", summary["assists"]),
        ("Turnovers", summary["turnovers"]),
        (
            "Assist/Turnover Ratio",
            _format_ratio(
                summary[
                    "assist_turnover_ratio"
                ]
            ),
        ),
        (
            "True Shooting %",
            format_percentage(
                summary[
                    "true_shooting_percentage"
                ]
            ),
        ),
        ("Steals", summary["steals"]),
        (
            "Deflections",
            summary["deflections"],
        ),
        (
            "Offensive Rebounds",
            summary["offensive_rebounds"],
        ),
        (
            "Defensive Rebounds",
            summary["defensive_rebounds"],
        ),
        (
            "Personal Fouls",
            summary["personal_fouls"],
        ),
    ]

    writer.writerows(
        team_summary_rows
    )

    writer.writerow([])

    # -----------------------------
    # Shooting
    # -----------------------------
    writer.writerow(["Shooting"])
    writer.writerow(
        [
            "Type",
            "Makes",
            "Attempts",
            "Percentage",
        ]
    )

    writer.writerow(
        [
            "FG",
            summary["field_goal_makes"],
            summary["field_goal_attempts"],
            format_percentage(
                summary[
                    "field_goal_percentage"
                ]
            ),
        ]
    )
    writer.writerow(
        [
            "2PT",
            summary["two_point_makes"],
            summary["two_point_attempts"],
            format_percentage(
                summary[
                    "two_point_percentage"
                ]
            ),
        ]
    )
    writer.writerow(
        [
            "3PT",
            summary["three_point_makes"],
            summary["three_point_attempts"],
            format_percentage(
                summary[
                    "three_point_percentage"
                ]
            ),
        ]
    )
    writer.writerow(
        [
            "FT",
            summary["free_throw_makes"],
            summary["free_throw_attempts"],
            format_percentage(
                summary[
                    "free_throw_percentage"
                ]
            ),
        ]
    )

    writer.writerow([])

    # -----------------------------
    # Player box score
    # -----------------------------
    writer.writerow(
        ["Player Box Score"]
    )

    writer.writerow(
        [
            "Player",
            "Jersey",
            "Participation",
            "PTS",
            "FGM",
            "FGA",
            "2PM",
            "2PA",
            "3PM",
            "3PA",
            "FTM",
            "FTA",
            "REB",
            "OREB",
            "DREB",
            "AST",
            "TO",
            "STL",
            "DEF",
            "PF",
            "TS%",
            "A:TO",
        ]
    )

    for row in player_rows:
        writer.writerow(
            [
                row["player_name"],
                (
                    row["jersey_number"]
                    if row[
                        "jersey_number"
                    ] is not None
                    else ""
                ),
                row[
                    "participation_status"
                ].value,
                row["points"],
                row["field_goal_makes"],
                row[
                    "field_goal_attempts"
                ],
                row["two_point_makes"],
                row[
                    "two_point_attempts"
                ],
                row[
                    "three_point_makes"
                ],
                row[
                    "three_point_attempts"
                ],
                row["free_throw_makes"],
                row[
                    "free_throw_attempts"
                ],
                row["rebounds"],
                row[
                    "offensive_rebounds"
                ],
                row[
                    "defensive_rebounds"
                ],
                row["assists"],
                row["turnovers"],
                row["steals"],
                row["deflections"],
                row["personal_fouls"],
                format_percentage(
                    row[
                        "true_shooting_percentage"
                    ]
                ),
                _format_ratio(
                    row[
                        "assist_turnover_ratio"
                    ]
                ),
            ]
        )

    return output.getvalue()

def build_player_season_csv(
    db: Session,
    season_roster_id: int,
) -> str:
    roster = get_season_roster(
        db,
        season_roster_id,
    )

    summary = calculate_player_season_summary(
        db,
        season_roster_id,
    )

    game_log = get_player_completed_game_log(
        db,
        season_roster_id,
    )

    player_name = (
        roster.player.display_name
        or roster.player.full_name
    )

    output = StringIO(newline="")
    writer = csv.writer(output)

    # -----------------------------
    # Player identity
    # -----------------------------
    writer.writerow(["Player"])
    writer.writerow(["Field", "Value"])

    writer.writerow(
        [
            "Player",
            player_name,
        ]
    )
    writer.writerow(
        [
            "Season",
            roster.season.name,
        ]
    )
    writer.writerow(
        [
            "Team",
            roster.season.team.name,
        ]
    )
    writer.writerow(
        [
            "Jersey",
            (
                roster.jersey_number
                if roster.jersey_number
                is not None
                else ""
            ),
        ]
    )
    writer.writerow(
        [
            "Position",
            roster.position or "",
        ]
    )
    writer.writerow(
        [
            "Grade",
            roster.grade_level or "",
        ]
    )
    writer.writerow(
        [
            "Roster Status",
            roster.status.value,
        ]
    )

    writer.writerow([])

    # -----------------------------
    # Season summary
    # -----------------------------
    writer.writerow(["Season Summary"])
    writer.writerow(["Metric", "Value"])

    summary_rows = [
        (
            "Games Played",
            summary["games_played"],
        ),
        (
            "Points",
            summary["points"],
        ),
        (
            "Points Per Game",
            _format_average(
                summary["points_per_game"]
            ),
        ),
        (
            "Rebounds",
            summary["rebounds"],
        ),
        (
            "Rebounds Per Game",
            _format_average(
                summary[
                    "rebounds_per_game"
                ]
            ),
        ),
        (
            "Assists",
            summary["assists"],
        ),
        (
            "Assists Per Game",
            _format_average(
                summary[
                    "assists_per_game"
                ]
            ),
        ),
        (
            "Assist/Turnover Ratio",
            _format_ratio(
                summary[
                    "assist_turnover_ratio"
                ]
            ),
        ),
        (
            "True Shooting %",
            format_percentage(
                summary[
                    "true_shooting_percentage"
                ]
            ),
        ),
    ]

    writer.writerows(summary_rows)

    writer.writerow([])

    # -----------------------------
    # Shooting
    # -----------------------------
    writer.writerow(["Shooting"])
    writer.writerow(
        [
            "Type",
            "Makes",
            "Attempts",
            "Percentage",
        ]
    )

    writer.writerow(
        [
            "FG",
            summary["field_goal_makes"],
            summary["field_goal_attempts"],
            format_percentage(
                summary[
                    "field_goal_percentage"
                ]
            ),
        ]
    )

    writer.writerow(
        [
            "2PT",
            summary["two_point_makes"],
            summary["two_point_attempts"],
            format_percentage(
                summary[
                    "two_point_percentage"
                ]
            ),
        ]
    )

    writer.writerow(
        [
            "3PT",
            summary["three_point_makes"],
            summary["three_point_attempts"],
            format_percentage(
                summary[
                    "three_point_percentage"
                ]
            ),
        ]
    )

    writer.writerow(
        [
            "FT",
            summary["free_throw_makes"],
            summary["free_throw_attempts"],
            format_percentage(
                summary[
                    "free_throw_percentage"
                ]
            ),
        ]
    )

    writer.writerow([])

    # -----------------------------
    # Other totals
    # -----------------------------
    writer.writerow(["Other Totals"])
    writer.writerow(["Metric", "Value"])

    writer.writerows(
        [
            (
                "Offensive Rebounds",
                summary[
                    "offensive_rebounds"
                ],
            ),
            (
                "Defensive Rebounds",
                summary[
                    "defensive_rebounds"
                ],
            ),
            (
                "Turnovers",
                summary["turnovers"],
            ),
            (
                "Steals",
                summary["steals"],
            ),
            (
                "Deflections",
                summary["deflections"],
            ),
            (
                "Personal Fouls",
                summary["personal_fouls"],
            ),
        ]
    )

    writer.writerow([])

    # -----------------------------
    # Completed game log
    # -----------------------------
    writer.writerow(
        ["Completed Game Log"]
    )

    writer.writerow(
        [
            "Date",
            "Opponent",
            "Venue",
            "Result",
            "Team Score",
            "Opponent Score",
            "Participation",
            "PTS",
            "REB",
            "AST",
            "TO",
            "FGM",
            "FGA",
            "3PM",
            "3PA",
            "FTM",
            "FTA",
            "TS%",
            "A:TO",
        ]
    )

    for row in game_log:
        writer.writerow(
            [
                row[
                    "game_date"
                ].strftime("%m/%d/%Y"),
                row["opponent_name"],
                row["venue_type"].value,
                row["result"],
                row["team_score"],
                row["opponent_score"],
                row[
                    "participation_status"
                ].value,
                row["points"],
                row["rebounds"],
                row["assists"],
                row["turnovers"],
                row["field_goal_makes"],
                row[
                    "field_goal_attempts"
                ],
                row[
                    "three_point_makes"
                ],
                row[
                    "three_point_attempts"
                ],
                row["free_throw_makes"],
                row[
                    "free_throw_attempts"
                ],
                format_percentage(
                    row[
                        "true_shooting_percentage"
                    ]
                ),
                _format_ratio(
                    row[
                        "assist_turnover_ratio"
                    ]
                ),
            ]
        )

    return output.getvalue()

def build_season_csv(
    db: Session,
    season_id: int,
) -> str:
    season = get_season(
        db,
        season_id,
    )

    summary = calculate_team_season_summary(
        db,
        season_id,
    )

    game_series = get_season_game_series(
        db,
        season_id,
    )

    output = StringIO(newline="")
    writer = csv.writer(output)

    # -----------------------------
    # Season identity
    # -----------------------------
    writer.writerow(["Season"])
    writer.writerow(["Field", "Value"])

    writer.writerow(
        [
            "Team",
            season.team.name,
        ]
    )
    writer.writerow(
        [
            "Season",
            season.name,
        ]
    )
    writer.writerow(
        [
            "Status",
            season.status.value,
        ]
    )
    writer.writerow(
        [
            "Start Date",
            (
                season.start_date.strftime(
                    "%m/%d/%Y"
                )
                if season.start_date
                is not None
                else ""
            ),
        ]
    )
    writer.writerow(
        [
            "End Date",
            (
                season.end_date.strftime(
                    "%m/%d/%Y"
                )
                if season.end_date
                is not None
                else ""
            ),
        ]
    )

    writer.writerow([])

    # -----------------------------
    # Record
    # -----------------------------
    writer.writerow(["Record"])
    writer.writerow(["Metric", "Value"])

    writer.writerows(
        [
            (
                "Games Played",
                summary["games_played"],
            ),
            (
                "Wins",
                summary["wins"],
            ),
            (
                "Losses",
                summary["losses"],
            ),
            (
                "Ties",
                summary["ties"],
            ),
        ]
    )

    writer.writerow([])

    # -----------------------------
    # Team season summary
    # -----------------------------
    writer.writerow(
        ["Team Season Summary"]
    )
    writer.writerow(["Metric", "Value"])

    writer.writerows(
        [
            (
                "Points",
                summary["points"],
            ),
            (
                "Opponent Points",
                summary[
                    "opponent_points"
                ],
            ),
            (
                "Point Differential",
                summary[
                    "point_differential"
                ],
            ),
            (
                "Points Per Game",
                _format_average(
                    summary[
                        "points_per_game"
                    ]
                ),
            ),
            (
                "Opponent Points Per Game",
                _format_average(
                    summary[
                        "opponent_points_per_game"
                    ]
                ),
            ),
            (
                "Point Differential Per Game",
                _format_average(
                    summary[
                        "point_differential_per_game"
                    ]
                ),
            ),
            (
                "Rebounds",
                summary["rebounds"],
            ),
            (
                "Rebounds Per Game",
                _format_average(
                    summary[
                        "rebounds_per_game"
                    ]
                ),
            ),
            (
                "Assists",
                summary["assists"],
            ),
            (
                "Assists Per Game",
                _format_average(
                    summary[
                        "assists_per_game"
                    ]
                ),
            ),
            (
                "Turnovers",
                summary["turnovers"],
            ),
            (
                "Turnovers Per Game",
                _format_average(
                    summary[
                        "turnovers_per_game"
                    ]
                ),
            ),
            (
                "Steals",
                summary["steals"],
            ),
            (
                "Steals Per Game",
                _format_average(
                    summary[
                        "steals_per_game"
                    ]
                ),
            ),
            (
                "Deflections",
                summary["deflections"],
            ),
            (
                "Deflections Per Game",
                _format_average(
                    summary[
                        "deflections_per_game"
                    ]
                ),
            ),
            (
                "Assist/Turnover Ratio",
                _format_ratio(
                    summary[
                        "assist_turnover_ratio"
                    ]
                ),
            ),
            (
                "True Shooting %",
                format_percentage(
                    summary[
                        "true_shooting_percentage"
                    ]
                ),
            ),
        ]
    )

    writer.writerow([])

    # -----------------------------
    # Shooting
    # -----------------------------
    writer.writerow(["Shooting"])
    writer.writerow(
        [
            "Type",
            "Makes",
            "Attempts",
            "Percentage",
        ]
    )

    writer.writerow(
        [
            "FG",
            summary["field_goal_makes"],
            summary["field_goal_attempts"],
            format_percentage(
                summary[
                    "field_goal_percentage"
                ]
            ),
        ]
    )

    writer.writerow(
        [
            "2PT",
            summary["two_point_makes"],
            summary["two_point_attempts"],
            format_percentage(
                summary[
                    "two_point_percentage"
                ]
            ),
        ]
    )

    writer.writerow(
        [
            "3PT",
            summary["three_point_makes"],
            summary["three_point_attempts"],
            format_percentage(
                summary[
                    "three_point_percentage"
                ]
            ),
        ]
    )

    writer.writerow(
        [
            "FT",
            summary["free_throw_makes"],
            summary["free_throw_attempts"],
            format_percentage(
                summary[
                    "free_throw_percentage"
                ]
            ),
        ]
    )

    writer.writerow([])

    # -----------------------------
    # Completed games
    # -----------------------------
    writer.writerow(["Completed Games"])

    writer.writerow(
        [
            "Date",
            "Opponent",
            "Venue",
            "Result",
            "Team Score",
            "Opponent Score",
            "Score Margin",
            "FG%",
            "2PT%",
            "3PT%",
            "FT%",
            "TS%",
        ]
    )

    for row in game_series:
        writer.writerow(
            [
                row[
                    "game_date"
                ].strftime("%m/%d/%Y"),
                row["opponent_name"],
                row["venue_type"].value,
                row["result"],
                row["team_score"],
                row["opponent_score"],
                row["score_margin"],
                format_percentage(
                    row[
                        "field_goal_percentage"
                    ]
                ),
                format_percentage(
                    row[
                        "two_point_percentage"
                    ]
                ),
                format_percentage(
                    row[
                        "three_point_percentage"
                    ]
                ),
                format_percentage(
                    row[
                        "free_throw_percentage"
                    ]
                ),
                format_percentage(
                    row[
                        "true_shooting_percentage"
                    ]
                ),
            ]
        )

    return output.getvalue()