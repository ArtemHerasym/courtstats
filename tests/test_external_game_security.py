from datetime import date

from app.models.game import (
    GameStatus,
    VenueType,
)
from app.schemas.external_game import (
    ExternalGameCreate,
)
from app.schemas.player import PlayerCreate
from app.schemas.team import TeamCreate
from app.services.external_game import (
    create_external_game,
)
from app.services.external_game_workflow import (
    sync_external_game_players,
)
from app.services.player import create_player
from app.services.team import create_team


def create_security_test_game(
    db_session,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="Security Opponent",
            abbreviation="SEC",
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Security Test Game",
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
            full_name="Security Player",
        ),
    )

    sync_external_game_players(
        db_session,
        game.id,
        [player.id],
    )

    return game, player


def test_external_games_library_requires_login(
    client,
):
    response = client.get(
        "/app/external-games",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_new_external_game_page_requires_login(
    client,
):
    response = client.get(
        "/app/external-games/new",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_external_game_players_page_requires_login(
    client,
    db_session,
):
    game, _ = create_security_test_game(
        db_session
    )

    response = client.get(
        (
            "/app/external-games/"
            f"{game.id}/players"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_external_game_stats_page_requires_login(
    client,
    db_session,
):
    game, _ = create_security_test_game(
        db_session
    )

    response = client.get(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login"


def test_create_external_game_rejects_missing_csrf(
    logged_in_client,
):
    response = logged_in_client.post(
        "/app/external-games/new",
        data={
            "name": "Unauthorized CSRF Game",
            "game_date": "09/04/2026",
            "opponent_team_id": "",
            "venue_type": "HOME",
            "opponent_score": "",
            "notes": "",
        },
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_player_selection_rejects_missing_csrf(
    logged_in_client,
    db_session,
):
    game, player = create_security_test_game(
        db_session
    )

    response = logged_in_client.post(
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

    assert response.status_code == 403


def test_stats_save_rejects_missing_csrf(
    logged_in_client,
    db_session,
):
    game, player = create_security_test_game(
        db_session
    )

    response = logged_in_client.post(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        ),
        data={
            "action": "save",
            "opponent_score": "50",
            "player_ids": [
                str(player.id),
            ],
            f"participation_{player.id}": (
                "PLAYED"
            ),
            f"three_point_attempts_{player.id}": "0",
            f"three_point_makes_{player.id}": "0",
            f"two_point_attempts_{player.id}": "0",
            f"two_point_makes_{player.id}": "0",
            f"free_throw_attempts_{player.id}": "0",
            f"free_throw_makes_{player.id}": "0",
            f"turnovers_{player.id}": "0",
            f"assists_{player.id}": "0",
            f"offensive_rebounds_{player.id}": "0",
            f"defensive_rebounds_{player.id}": "0",
            f"steals_{player.id}": "0",
            f"deflections_{player.id}": "0",
            f"personal_fouls_{player.id}": "0",
        },
        follow_redirects=False,
    )

    assert response.status_code == 403


def test_new_external_game_form_contains_csrf_token(
    logged_in_client,
):
    response = logged_in_client.get(
        "/app/external-games/new"
    )

    assert response.status_code == 200
    assert 'name="csrf_token"' in response.text


def test_player_selection_form_contains_csrf_token(
    logged_in_client,
    db_session,
):
    game, _ = create_security_test_game(
        db_session
    )

    response = logged_in_client.get(
        (
            "/app/external-games/"
            f"{game.id}/players"
        )
    )

    assert response.status_code == 200
    assert 'name="csrf_token"' in response.text


def test_stats_form_contains_csrf_token(
    logged_in_client,
    db_session,
):
    game, _ = create_security_test_game(
        db_session
    )

    response = logged_in_client.get(
        (
            "/app/external-games/"
            f"{game.id}/stats"
        )
    )

    assert response.status_code == 200
    assert 'name="csrf_token"' in response.text