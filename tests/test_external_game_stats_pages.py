from datetime import date

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
    list_external_game_player_stats,
)
from app.services.external_game_workflow import (
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


def create_external_game_with_players(
    db_session,
    *,
    player_count: int = 1,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="Stats Opponent",
            abbreviation="ST",
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="External Stats Test",
            opponent_team_id=opponent.id,
            game_date=date(2026, 9, 1),
            venue_type=VenueType.NEUTRAL,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    players = []

    for number in range(
        1,
        player_count + 1,
    ):
        player = create_player(
            db_session,
            PlayerCreate(
                full_name=(
                    f"External Player {number}"
                ),
            ),
        )

        players.append(player)

    sync_external_game_players(
        db_session,
        game.id,
        [
            player.id
            for player in players
        ],
    )

    return game, players


def build_stats_form(
    player_ids: list[int],
):
    data = {
        "action": "save",
        "opponent_score": "70",
        "player_ids": [
            str(player_id)
            for player_id in player_ids
        ],
    }

    for player_id in player_ids:
        data[
            f"participation_{player_id}"
        ] = "PLAYED"

        for field in STAT_FIELDS:
            data[
                f"{field}_{player_id}"
            ] = "0"

    return data


def test_external_stats_requires_login(
    client,
    db_session,
):
    game, _ = (
        create_external_game_with_players(
            db_session
        )
    )

    response = client.get(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"]
        == "/login"
    )


def test_external_stats_page_renders_selected_player(
    logged_in_client,
    db_session,
):
    game, players = (
        create_external_game_with_players(
            db_session
        )
    )

    response = logged_in_client.get(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        )
    )

    assert response.status_code == 200
    assert "External Stats Test" in response.text
    assert (
        players[0].full_name
        in response.text
    )

    assert "3PA" in response.text
    assert "3PM" in response.text
    assert "OREB" in response.text
    assert "DEF" in response.text


def test_valid_played_stats_save(
    authenticated_client,
    db_session,
):
    game, players = (
        create_external_game_with_players(
            db_session
        )
    )

    player = players[0]

    data = build_stats_form(
        [player.id]
    )

    data[
        f"three_point_attempts_{player.id}"
    ] = "5"

    data[
        f"three_point_makes_{player.id}"
    ] = "2"

    data[
        f"two_point_attempts_{player.id}"
    ] = "7"

    data[
        f"two_point_makes_{player.id}"
    ] = "4"

    data[
        f"assists_{player.id}"
    ] = "6"

    response = authenticated_client.post(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        ),
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 303

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert len(rows) == 1

    row = rows[0]

    assert row.player_id == player.id
    assert (
        row.participation_status
        == ParticipationStatus.PLAYED
    )
    assert row.three_point_attempts == 5
    assert row.three_point_makes == 2
    assert row.two_point_attempts == 7
    assert row.two_point_makes == 4
    assert row.assists == 6

    db_session.refresh(game)

    assert game.opponent_score == 70
    assert game.status == GameStatus.DRAFT


def test_valid_dnp_stats_save(
    authenticated_client,
    db_session,
):
    game, players = (
        create_external_game_with_players(
            db_session
        )
    )

    player = players[0]

    data = build_stats_form(
        [player.id]
    )

    data[
        f"participation_{player.id}"
    ] = "DID_NOT_PLAY"

    response = authenticated_client.post(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        ),
        data=data,
        follow_redirects=False,
    )

    assert response.status_code == 303

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    row = rows[0]

    assert (
        row.participation_status
        == ParticipationStatus.DID_NOT_PLAY
    )

    for field in STAT_FIELDS:
        assert getattr(row, field) == 0


def test_invalid_shooting_values_rejected(
    authenticated_client,
    db_session,
):
    game, players = (
        create_external_game_with_players(
            db_session
        )
    )

    player = players[0]

    data = build_stats_form(
        [player.id]
    )

    data[
        f"three_point_attempts_{player.id}"
    ] = "1"

    data[
        f"three_point_makes_{player.id}"
    ] = "2"

    response = authenticated_client.post(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        ),
        data=data,
    )

    assert response.status_code == 422
    assert (
        "Three-point makes cannot exceed "
        "three-point attempts"
        in response.text
    )

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert rows[0].three_point_attempts == 0
    assert rows[0].three_point_makes == 0


def test_atomic_multi_player_validation_failure(
    authenticated_client,
    db_session,
):
    game, players = (
        create_external_game_with_players(
            db_session,
            player_count=2,
        )
    )

    first = players[0]
    second = players[1]

    data = build_stats_form(
        [
            first.id,
            second.id,
        ]
    )

    data[
        f"assists_{first.id}"
    ] = "8"

    data[
        f"three_point_attempts_{second.id}"
    ] = "1"

    data[
        f"three_point_makes_{second.id}"
    ] = "3"

    response = authenticated_client.post(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        ),
        data=data,
    )

    assert response.status_code == 422

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    rows_by_player = {
        row.player_id: row
        for row in rows
    }

    # First player's otherwise valid change
    # must NOT partially save.
    assert (
        rows_by_player[
            first.id
        ].assists
        == 0
    )

    assert (
        rows_by_player[
            second.id
        ].three_point_attempts
        == 0
    )

    assert (
        rows_by_player[
            second.id
        ].three_point_makes
        == 0
    )


def test_saved_draft_reopens_with_existing_stats(
    authenticated_client,
    db_session,
):
    game, players = (
        create_external_game_with_players(
            db_session
        )
    )

    player = players[0]

    data = build_stats_form(
        [player.id]
    )

    data[
        f"steals_{player.id}"
    ] = "4"

    save_response = (
        authenticated_client.post(
            (
                "/app/external-games/"
                f"{game.id}/stats"
            ),
            data=data,
            follow_redirects=False,
        )
    )

    assert save_response.status_code == 303

    response = authenticated_client.get(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        )
    )

    assert response.status_code == 200

    assert (
        f'name="steals_{player.id}"'
        in response.text
    )

    assert 'value="4"' in response.text