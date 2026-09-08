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
    ExternalGameNotFoundError,
    create_external_game,
)
from app.services.external_game_analysis import (
    ExternalGameNotCompletedError,
    get_external_game_report,
)
from app.services.external_game_workflow import (
    finalize_external_game_with_stats,
    sync_external_game_players,
)
from app.services.player import create_player
from app.services.team import create_team


def _create_external_game_setup(
    db_session,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="Analysis Opponent",
            abbreviation="ANL",
        ),
    )

    played_player = create_player(
        db_session,
        PlayerCreate(
            full_name="Played Player",
        ),
    )

    dnp_player = create_player(
        db_session,
        PlayerCreate(
            full_name="DNP Player",
        ),
    )

    external_game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Analysis Test Game",
            opponent_team_id=opponent.id,
            game_date=date(2026, 9, 1),
            venue_type=VenueType.HOME,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    sync_external_game_players(
        db_session,
        external_game.id,
        [
            played_player.id,
            dnp_player.id,
        ],
    )

    return (
        external_game,
        played_player,
        dnp_player,
    )


def _finalize_known_external_game(
    db_session,
    external_game,
    played_player,
    dnp_player,
):
    played_stats = (
        ExternalGamePlayerStatsCreate(
            external_game_id=external_game.id,
            player_id=played_player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),

            # 2/4 from 3PT = 6 points
            three_point_attempts=4,
            three_point_makes=2,

            # 3/6 from 2PT = 6 points
            two_point_attempts=6,
            two_point_makes=3,

            # 3/4 FT = 3 points
            free_throw_attempts=4,
            free_throw_makes=3,

            # Total = 15 points
            turnovers=2,
            assists=4,
            offensive_rebounds=2,
            defensive_rebounds=3,
            steals=1,
            deflections=2,
            personal_fouls=2,
        )
    )

    dnp_stats = (
        ExternalGamePlayerStatsCreate(
            external_game_id=external_game.id,
            player_id=dnp_player.id,
            participation_status=(
                ParticipationStatus.DID_NOT_PLAY
            ),
            three_point_attempts=0,
            three_point_makes=0,
            two_point_attempts=0,
            two_point_makes=0,
            free_throw_attempts=0,
            free_throw_makes=0,
            turnovers=0,
            assists=0,
            offensive_rebounds=0,
            defensive_rebounds=0,
            steals=0,
            deflections=0,
            personal_fouls=0,
        )
    )

    finalize_external_game_with_stats(
        db_session,
        external_game.id,
        [
            played_stats,
            dnp_stats,
        ],
        opponent_score=12,
    )


def test_external_game_report_calculates_known_team_values(
    db_session,
):
    (
        external_game,
        played_player,
        dnp_player,
    ) = _create_external_game_setup(
        db_session,
    )

    _finalize_known_external_game(
        db_session,
        external_game,
        played_player,
        dnp_player,
    )

    report = get_external_game_report(
        db_session,
        external_game.id,
    )

    summary = report["summary"]

    assert summary["team_score"] == 15
    assert summary["opponent_score"] == 12

    assert summary["result"] == "WIN"
    assert summary["score_margin"] == 3

    assert summary["rebounds"] == 5
    assert summary["assists"] == 4
    assert summary["turnovers"] == 2
    assert summary["steals"] == 1
    assert summary["deflections"] == 2
    assert summary["personal_fouls"] == 2

    assert summary["field_goal_makes"] == 5
    assert summary["field_goal_attempts"] == 10

    assert summary[
        "field_goal_percentage"
    ] == pytest.approx(0.5)

    assert summary[
        "two_point_percentage"
    ] == pytest.approx(0.5)

    assert summary[
        "three_point_percentage"
    ] == pytest.approx(0.5)

    assert summary[
        "free_throw_percentage"
    ] == pytest.approx(0.75)

    assert summary[
        "true_shooting_percentage"
    ] == pytest.approx(
        15 / (2 * (10 + 0.44 * 4))
    )

    assert summary[
        "assist_turnover_ratio"
    ] == pytest.approx(2.0)


def test_external_game_report_calculates_known_player_values(
    db_session,
):
    (
        external_game,
        played_player,
        dnp_player,
    ) = _create_external_game_setup(
        db_session,
    )

    _finalize_known_external_game(
        db_session,
        external_game,
        played_player,
        dnp_player,
    )

    report = get_external_game_report(
        db_session,
        external_game.id,
    )

    played_row = next(
        row
        for row in report["player_rows"]
        if row["player_id"]
        == played_player.id
    )

    assert (
        played_row["player_name"]
        == "Played Player"
    )

    assert (
        played_row["participation_status"]
        == ParticipationStatus.PLAYED
    )

    assert played_row["points"] == 15
    assert played_row["rebounds"] == 5

    assert played_row["assists"] == 4
    assert played_row["turnovers"] == 2

    assert played_row["field_goal_makes"] == 5
    assert played_row["field_goal_attempts"] == 10

    assert played_row[
        "field_goal_percentage"
    ] == pytest.approx(0.5)

    assert played_row[
        "true_shooting_percentage"
    ] == pytest.approx(
        15 / (2 * (10 + 0.44 * 4))
    )

    assert played_row[
        "assist_turnover_ratio"
    ] == pytest.approx(2.0)


def test_external_game_report_keeps_dnp_player_without_team_effect(
    db_session,
):
    (
        external_game,
        played_player,
        dnp_player,
    ) = _create_external_game_setup(
        db_session,
    )

    _finalize_known_external_game(
        db_session,
        external_game,
        played_player,
        dnp_player,
    )

    report = get_external_game_report(
        db_session,
        external_game.id,
    )

    dnp_row = next(
        row
        for row in report["player_rows"]
        if row["player_id"]
        == dnp_player.id
    )

    assert (
        dnp_row["participation_status"]
        == ParticipationStatus.DID_NOT_PLAY
    )

    assert dnp_row["points"] == 0
    assert dnp_row["rebounds"] == 0
    assert dnp_row["assists"] == 0

    assert (
        dnp_row["field_goal_percentage"]
        is None
    )

    assert (
        dnp_row["true_shooting_percentage"]
        is None
    )

    assert (
        dnp_row["assist_turnover_ratio"]
        is None
    )

    # DNP zeros must not alter the team result.
    assert report["summary"]["team_score"] == 15


def test_external_game_report_rejects_draft_game(
    db_session,
):
    (
        external_game,
        _,
        _,
    ) = _create_external_game_setup(
        db_session,
    )

    with pytest.raises(
        ExternalGameNotCompletedError,
        match="must be completed",
    ):
        get_external_game_report(
            db_session,
            external_game.id,
        )


def test_external_game_report_rejects_missing_game(
    db_session,
):
    with pytest.raises(
        ExternalGameNotFoundError,
    ):
        get_external_game_report(
            db_session,
            999999,
        )