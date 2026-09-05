from datetime import date

from app.models.game import (
    GameStatus,
    VenueType,
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
from app.services.external_game_player_stats import (
    ExternalGamePlayerStatsConflictError,
    list_external_game_player_stats,
)
from app.services.external_game_workflow import (
    finalize_external_game_with_stats,
    sync_external_game_players,
)
from app.services.player import create_player
from app.services.team import create_team


STAT_FIELDS = (
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


def create_completed_external_game(
    db_session,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="Completed Edit Opponent",
            abbreviation="CEO",
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Completed Edit Test",
            opponent_team_id=opponent.id,
            game_date=date.today(),
            venue_type=VenueType.NEUTRAL,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Completed Edit Player",
        ),
    )

    sync_external_game_players(
        db_session,
        game.id,
        [player.id],
    )

    stats = ExternalGamePlayerStatsCreate(
        external_game_id=game.id,
        player_id=player.id,
        participation_status="PLAYED",
        three_point_attempts=4,
        three_point_makes=2,
        two_point_attempts=6,
        two_point_makes=3,
        free_throw_attempts=2,
        free_throw_makes=2,
        turnovers=1,
        assists=3,
        offensive_rebounds=1,
        defensive_rebounds=4,
        steals=2,
        deflections=1,
        personal_fouls=2,
    )

    finalize_external_game_with_stats(
        db_session,
        game.id,
        [stats],
        opponent_score=60,
    )

    db_session.refresh(game)

    return game, player


def build_completed_edit_form(
    player_id: int,
):
    data = {
        "action": "save",
        "opponent_score": "61",
        "player_ids": [
            str(player_id),
        ],
        f"participation_{player_id}": (
            "PLAYED"
        ),
    }

    values = {
        "three_point_attempts": 4,
        "three_point_makes": 2,
        "two_point_attempts": 6,
        "two_point_makes": 3,
        "free_throw_attempts": 2,
        "free_throw_makes": 2,
        "turnovers": 1,
        "assists": 3,
        "offensive_rebounds": 1,
        "defensive_rebounds": 4,
        "steals": 2,
        "deflections": 1,
        "personal_fouls": 2,
    }

    for field, value in values.items():
        data[
            f"{field}_{player_id}"
        ] = str(value)

    return data


def test_completed_external_game_stats_prefill(
    authenticated_client,
    db_session,
):
    game, player = (
        create_completed_external_game(
            db_session
        )
    )

    response = authenticated_client.get(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        )
    )

    assert response.status_code == 200
    assert "COMPLETED" in response.text
    assert "Save Changes" in response.text
    assert (
        "Change Players"
        not in response.text
    )

    assert (
        f'name="assists_{player.id}"'
        in response.text
    )

    assert 'value="3"' in response.text


def test_valid_completed_game_edit_saves(
    authenticated_client,
    db_session,
):
    game, player = (
        create_completed_external_game(
            db_session
        )
    )

    data = build_completed_edit_form(
        player.id
    )

    data[
        f"assists_{player.id}"
    ] = "8"

    data[
        f"steals_{player.id}"
    ] = "5"

    response = authenticated_client.post(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        ),
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 303

    db_session.refresh(game)

    assert game.status == GameStatus.COMPLETED
    assert game.opponent_score == 61

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert len(rows) == 1
    assert rows[0].assists == 8
    assert rows[0].steals == 5


def test_completed_edit_missing_score_rolls_back(
    authenticated_client,
    db_session,
):
    game, player = (
        create_completed_external_game(
            db_session
        )
    )

    data = build_completed_edit_form(
        player.id
    )

    data["opponent_score"] = ""

    data[
        f"assists_{player.id}"
    ] = "9"

    response = authenticated_client.post(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        ),
        data=data,
    )

    assert response.status_code == 422

    db_session.refresh(game)

    assert game.status == GameStatus.COMPLETED
    assert game.opponent_score == 60

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert rows[0].assists == 3


def test_completed_edit_cannot_leave_only_dnp(
    authenticated_client,
    db_session,
):
    game, player = (
        create_completed_external_game(
            db_session
        )
    )

    data = build_completed_edit_form(
        player.id
    )

    data[
        f"participation_{player.id}"
    ] = "DID_NOT_PLAY"

    for field in STAT_FIELDS:
        data[
            f"{field}_{player.id}"
        ] = "0"

    response = authenticated_client.post(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        ),
        data=data,
    )

    assert response.status_code == 422

    db_session.refresh(game)

    assert game.status == GameStatus.COMPLETED
    assert game.opponent_score == 60

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert (
        rows[0].participation_status.value
        == "PLAYED"
    )

    assert rows[0].assists == 3


def test_completed_player_selection_change_rejected(
    db_session,
):
    game, player = (
        create_completed_external_game(
            db_session
        )
    )

    try:
        sync_external_game_players(
            db_session,
            game.id,
            [],
        )

    except (
        ExternalGamePlayerStatsConflictError
    ):
        pass

    else:
        raise AssertionError(
            (
                "Completed external game player "
                "selection should not be mutable."
            )
        )

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert len(rows) == 1
    assert rows[0].player_id == player.id

    db_session.refresh(game)

    assert game.status == GameStatus.COMPLETED