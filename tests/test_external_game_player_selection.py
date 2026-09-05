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
from app.schemas.player import PlayerCreate
from app.schemas.team import TeamCreate
from app.services.external_game import (
    create_external_game,
)
from app.services.external_game_player_stats import (
    ExternalGamePlayerStatsConflictError,
    list_external_game_player_stats,
)
from app.services.external_game_workflow import (
    sync_external_game_players,
)
from app.services.player import create_player
from app.services.team import create_team


def create_test_external_game(
    db_session,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="Selection Opponent",
            abbreviation="SEL",
        ),
    )

    return create_external_game(
        db_session,
        ExternalGameCreate(
            name="Selection Test Game",
            opponent_team_id=opponent.id,
            game_date=date(2026, 9, 1),
            venue_type=VenueType.NEUTRAL,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )


def test_global_player_appears_in_selection(
    logged_in_client,
    db_session,
):
    game = create_test_external_game(
        db_session
    )

    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Global Player",
            display_name=None,
        ),
    )

    response = logged_in_client.get(
        (
            "/app/external-games/"
            f"{game.id}/players"
        )
    )

    assert response.status_code == 200
    assert "Global Player" in response.text
    assert str(player.id) in response.text


def test_player_without_season_roster_can_be_selected(
    authenticated_client,
    db_session,
):
    game = create_test_external_game(
        db_session
    )

    player = create_player(
        db_session,
        PlayerCreate(
            full_name="No Roster Player",
            display_name=None,
        ),
    )

    response = authenticated_client.post(
        (
            "/app/external-games/"
            f"{game.id}/players"
        ),
        data={
            "player_ids": [
                str(player.id),
            ],
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert len(rows) == 1
    assert rows[0].player_id == player.id
    assert (
        rows[0].participation_status
        == ParticipationStatus.PLAYED
    )

    assert rows[0].three_point_attempts == 0
    assert rows[0].three_point_makes == 0
    assert rows[0].two_point_attempts == 0
    assert rows[0].two_point_makes == 0


def test_draft_player_selection_can_be_changed(
    authenticated_client,
    db_session,
):
    game = create_test_external_game(
        db_session
    )

    player_one = create_player(
        db_session,
        PlayerCreate(
            full_name="Player One",
        ),
    )

    player_two = create_player(
        db_session,
        PlayerCreate(
            full_name="Player Two",
        ),
    )

    player_three = create_player(
        db_session,
        PlayerCreate(
            full_name="Player Three",
        ),
    )

    response = authenticated_client.post(
        (
            "/app/external-games/"
            f"{game.id}/players"
        ),
        data={
            "player_ids": [
                str(player_one.id),
                str(player_two.id),
            ],
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    response = authenticated_client.post(
        (
            "/app/external-games/"
            f"{game.id}/players"
        ),
        data={
            "player_ids": [
                str(player_two.id),
                str(player_three.id),
            ],
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    player_ids = {
        row.player_id
        for row in rows
    }

    assert player_ids == {
        player_two.id,
        player_three.id,
    }


def test_duplicate_player_selection_rejected(
    db_session,
):
    game = create_test_external_game(
        db_session
    )

    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Duplicate Player",
        ),
    )

    with pytest.raises(
        ExternalGamePlayerStatsConflictError,
        match="Duplicate player selection",
    ):
        sync_external_game_players(
            db_session,
            game.id,
            [
                player.id,
                player.id,
            ],
        )

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert rows == []


def test_player_selection_is_atomic_on_invalid_player(
    db_session,
):
    game = create_test_external_game(
        db_session
    )

    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Valid Player",
        ),
    )

    sync_external_game_players(
        db_session,
        game.id,
        [player.id],
    )

    with pytest.raises(Exception):
        sync_external_game_players(
            db_session,
            game.id,
            [
                999999999,
            ],
        )

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert len(rows) == 1
    assert rows[0].player_id == player.id