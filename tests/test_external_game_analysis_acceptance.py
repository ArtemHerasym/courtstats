from datetime import date

import pytest

from app.models.game import (
    GameStatus,
    VenueType,
)
from app.models.player_game_stats import (
    ParticipationStatus,
)
from app.schemas.external_game import (
    ExternalGameCreate,
)
from app.schemas.external_game_player_stats import (
    ExternalGamePlayerStatsCreate,
)
from app.schemas.player import PlayerCreate
from app.schemas.team import TeamCreate
from app.services.external_game import (
    create_external_game,
)
from app.services.external_game_analysis import (
    analyze_external_games,
)
from app.services.external_game_workflow import (
    finalize_external_game_with_stats,
    sync_external_game_players,
)
from app.services.player import create_player
from app.services.team import create_team


def _zero_stats() -> dict[str, int]:
    return {
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


def _create_player(
    db_session,
    name: str,
):
    return create_player(
        db_session,
        PlayerCreate(
            full_name=name,
        ),
    )


def _create_completed_game(
    db_session,
    *,
    name: str,
    opponent_name: str,
    game_date: date,
    opponent_score: int,
    rows: list[dict],
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name=opponent_name,
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name=name,
            opponent_team_id=opponent.id,
            game_date=game_date,
            venue_type=VenueType.NEUTRAL,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    sync_external_game_players(
        db_session,
        game.id,
        [
            row["player"].id
            for row in rows
        ],
    )

    stat_rows = []

    for row in rows:
        stat_rows.append(
            ExternalGamePlayerStatsCreate(
                external_game_id=game.id,
                player_id=row["player"].id,
                participation_status=(
                    row["participation"]
                ),
                **row["stats"],
            )
        )

    finalize_external_game_with_stats(
        db_session,
        game.id,
        stat_rows,
        opponent_score=opponent_score,
    )

    return game


def test_combined_shooting_uses_total_makes_and_attempts(
    db_session,
):
    player = _create_player(
        db_session,
        "Combined Shooter",
    )

    game_one_stats = _zero_stats()
    game_one_stats.update(
        {
            "two_point_attempts": 2,
            "two_point_makes": 1,
            "free_throw_attempts": 2,
            "free_throw_makes": 1,
        }
    )

    game_two_stats = _zero_stats()
    game_two_stats.update(
        {
            "two_point_attempts": 20,
            "two_point_makes": 8,
            "free_throw_attempts": 10,
            "free_throw_makes": 9,
        }
    )

    game_one = _create_completed_game(
        db_session,
        name="Combined Game One",
        opponent_name="Combined Opponent One",
        game_date=date(2026, 9, 1),
        opponent_score=2,
        rows=[
            {
                "player": player,
                "participation": (
                    ParticipationStatus.PLAYED
                ),
                "stats": game_one_stats,
            }
        ],
    )

    game_two = _create_completed_game(
        db_session,
        name="Combined Game Two",
        opponent_name="Combined Opponent Two",
        game_date=date(2026, 9, 2),
        opponent_score=30,
        rows=[
            {
                "player": player,
                "participation": (
                    ParticipationStatus.PLAYED
                ),
                "stats": game_two_stats,
            }
        ],
    )

    analysis = analyze_external_games(
        db_session,
        [
            game_one.id,
            game_two.id,
        ],
    )

    summary = analysis["team_summary"]

    # Combined FG:
    # (1 + 8) / (2 + 20) = 9 / 22
    assert (
        summary["field_goal_percentage"]
        == pytest.approx(9 / 22)
    )

    assert (
        summary["two_point_percentage"]
        == pytest.approx(9 / 22)
    )

    # Do NOT average 50% and 40%.
    assert (
        summary["field_goal_percentage"]
        != pytest.approx(0.45)
    )

    # Combined FT:
    # (1 + 9) / (2 + 10)
    assert (
        summary["free_throw_percentage"]
        == pytest.approx(10 / 12)
    )

    # 3 + 25 = 28 total points.
    assert summary["points"] == 28

    assert (
        summary["points_per_game"]
        == pytest.approx(14.0)
    )

    # Combined TS% must use combined totals.
    assert (
        summary[
            "true_shooting_percentage"
        ]
        == pytest.approx(
            28
            / (
                2
                * (
                    22
                    + 0.44 * 12
                )
            )
        )
    )


def test_player_gp_counts_only_played_rows(
    db_session,
):
    player_a = _create_player(
        db_session,
        "Player A",
    )

    player_b = _create_player(
        db_session,
        "Player B",
    )

    player_c = _create_player(
        db_session,
        "Player C DNP Only",
    )

    a_stats = _zero_stats()
    a_stats.update(
        {
            "two_point_attempts": 5,
            "two_point_makes": 5,
        }
    )

    b_dnp = _zero_stats()
    c_dnp_one = _zero_stats()

    game_one = _create_completed_game(
        db_session,
        name="GP Game One",
        opponent_name="GP Opponent One",
        game_date=date(2026, 9, 1),
        opponent_score=5,
        rows=[
            {
                "player": player_a,
                "participation": (
                    ParticipationStatus.PLAYED
                ),
                "stats": a_stats,
            },
            {
                "player": player_b,
                "participation": (
                    ParticipationStatus.DID_NOT_PLAY
                ),
                "stats": b_dnp,
            },
            {
                "player": player_c,
                "participation": (
                    ParticipationStatus.DID_NOT_PLAY
                ),
                "stats": c_dnp_one,
            },
        ],
    )

    b_stats = _zero_stats()
    b_stats.update(
        {
            "three_point_attempts": 2,
            "three_point_makes": 2,
        }
    )

    c_dnp_two = _zero_stats()

    game_two = _create_completed_game(
        db_session,
        name="GP Game Two",
        opponent_name="GP Opponent Two",
        game_date=date(2026, 9, 2),
        opponent_score=4,
        rows=[
            {
                "player": player_b,
                "participation": (
                    ParticipationStatus.PLAYED
                ),
                "stats": b_stats,
            },
            {
                "player": player_c,
                "participation": (
                    ParticipationStatus.DID_NOT_PLAY
                ),
                "stats": c_dnp_two,
            },
        ],
    )

    analysis = analyze_external_games(
        db_session,
        [
            game_one.id,
            game_two.id,
        ],
    )

    rows = {
        row["player_id"]: row
        for row in analysis["player_rows"]
    }

    a = rows[player_a.id]
    b = rows[player_b.id]
    c = rows[player_c.id]

    # Player A was absent from game two.
    assert a["games_played"] == 1
    assert a["points"] == 10
    assert a["points_per_game"] == 10.0

    # Player B was DNP once and PLAYED once.
    assert b["games_played"] == 1
    assert b["points"] == 6
    assert b["points_per_game"] == 6.0

    # Player C appeared only as DNP.
    assert c["games_played"] == 0
    assert c["points"] == 0

    assert c["points_per_game"] is None
    assert c["rebounds_per_game"] is None
    assert c["assists_per_game"] is None

    assert (
        c["field_goal_percentage"]
        is None
    )

    assert (
        c["true_shooting_percentage"]
        is None
    )


def test_selected_game_breakdown_is_chronological(
    db_session,
):
    player = _create_player(
        db_session,
        "Breakdown Player",
    )

    stats = _zero_stats()
    stats.update(
        {
            "two_point_attempts": 2,
            "two_point_makes": 2,
        }
    )

    earlier = _create_completed_game(
        db_session,
        name="Earlier Game",
        opponent_name="Earlier Opponent",
        game_date=date(2026, 9, 1),
        opponent_score=2,
        rows=[
            {
                "player": player,
                "participation": (
                    ParticipationStatus.PLAYED
                ),
                "stats": stats,
            }
        ],
    )

    later = _create_completed_game(
        db_session,
        name="Later Game",
        opponent_name="Later Opponent",
        game_date=date(2026, 9, 3),
        opponent_score=6,
        rows=[
            {
                "player": player,
                "participation": (
                    ParticipationStatus.PLAYED
                ),
                "stats": stats,
            }
        ],
    )

    # Intentionally pass them backwards.
    analysis = analyze_external_games(
        db_session,
        [
            later.id,
            earlier.id,
        ],
    )

    breakdown = analysis[
        "game_breakdown"
    ]

    assert len(breakdown) == 2

    assert (
        breakdown[0]["game_name"]
        == "Earlier Game"
    )

    assert (
        breakdown[1]["game_name"]
        == "Later Game"
    )

    assert breakdown[0]["result"] == "WIN"
    assert breakdown[1]["result"] == "LOSS"

    assert breakdown[0]["team_score"] == 4
    assert breakdown[1]["team_score"] == 4


def test_analysis_contains_only_selected_games(
    db_session,
):
    player = _create_player(
        db_session,
        "Selection Player",
    )

    stats = _zero_stats()
    stats.update(
        {
            "two_point_attempts": 2,
            "two_point_makes": 1,
        }
    )

    game_one = _create_completed_game(
        db_session,
        name="Selected One",
        opponent_name="Selected Opponent One",
        game_date=date(2026, 9, 1),
        opponent_score=1,
        rows=[
            {
                "player": player,
                "participation": (
                    ParticipationStatus.PLAYED
                ),
                "stats": stats,
            }
        ],
    )

    game_two = _create_completed_game(
        db_session,
        name="Selected Two",
        opponent_name="Selected Opponent Two",
        game_date=date(2026, 9, 2),
        opponent_score=3,
        rows=[
            {
                "player": player,
                "participation": (
                    ParticipationStatus.PLAYED
                ),
                "stats": stats,
            }
        ],
    )

    _create_completed_game(
        db_session,
        name="Not Selected",
        opponent_name="Unselected Opponent",
        game_date=date(2026, 9, 3),
        opponent_score=100,
        rows=[
            {
                "player": player,
                "participation": (
                    ParticipationStatus.PLAYED
                ),
                "stats": stats,
            }
        ],
    )

    analysis = analyze_external_games(
        db_session,
        [
            game_one.id,
            game_two.id,
        ],
    )

    assert (
        analysis["team_summary"][
            "games_played"
        ]
        == 2
    )

    names = [
        row["game_name"]
        for row in analysis[
            "game_breakdown"
        ]
    ]

    assert names == [
        "Selected One",
        "Selected Two",
    ]

    assert "Not Selected" not in names


def test_library_renders_analysis_controls(
    logged_in_client,
    db_session,
):
    player = _create_player(
        db_session,
        "Library Analysis Player",
    )

    stats = _zero_stats()
    stats.update(
        {
            "two_point_attempts": 2,
            "two_point_makes": 1,
        }
    )

    completed = _create_completed_game(
        db_session,
        name="Completed Analysis Game",
        opponent_name="Completed Analysis Opponent",
        game_date=date(2026, 9, 1),
        opponent_score=1,
        rows=[
            {
                "player": player,
                "participation": (
                    ParticipationStatus.PLAYED
                ),
                "stats": stats,
            }
        ],
    )

    draft_opponent = create_team(
        db_session,
        TeamCreate(
            name="Draft Analysis Opponent UI",
        ),
    )

    create_external_game(
        db_session,
        ExternalGameCreate(
            name="Draft Analysis Game UI",
            opponent_team_id=(
                draft_opponent.id
            ),
            game_date=date(2026, 9, 2),
            venue_type=VenueType.HOME,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    response = logged_in_client.get(
        "/app/external-games"
    )

    assert response.status_code == 200

    html = response.text

    assert "Analyze Games" in html
    assert "View Statistics" in html

    assert (
        'id="analysis-selection-count"'
        in html
    )

    assert (
        'name="game_ids"'
        in html
    )

    assert (
        f'value="{completed.id}"'
        in html
    )

    assert (
        "Finalize to analyze"
        in html
    )