from datetime import date

from sqlalchemy import select

from app.models.external_game import (
    ExternalGame,
)
from app.models.game import (
    GameStatus,
    VenueType,
)
from app.models.player import Player
from app.models.team import Team
from app.services.external_game_player_stats import (
    list_external_game_player_stats,
)


def _external_game(
    db_session,
):
    opponent = Team(
        name="External Onboarding Opponent",
        abbreviation="EOO",
    )

    db_session.add(opponent)
    db_session.flush()

    external_game = ExternalGame(
        name="External Onboarding Game",
        opponent_team_id=opponent.id,
        game_date=date(
            2035,
            1,
            10,
        ),
        venue_type=VenueType.NEUTRAL,
        status=GameStatus.DRAFT,
        opponent_score=None,
        notes=None,
    )

    db_session.add(external_game)
    db_session.commit()

    db_session.refresh(external_game)

    return external_game


def test_empty_external_player_library_has_add_player(
    logged_in_client,
    db_session,
):
    game = _external_game(
        db_session
    )

    response = logged_in_client.get(
        (
            "/app/external-games/"
            f"{game.id}/players"
        )
    )

    assert response.status_code == 200

    assert (
        "No players available"
        in response.text
    )

    assert "+ Add Player" in response.text

    assert (
        "return_context=external_game"
        in response.text
    )

    assert (
        f"external_game_id={game.id}"
        in response.text
    )


def test_external_game_player_form_preserves_context(
    logged_in_client,
    db_session,
):
    game = _external_game(
        db_session
    )

    response = logged_in_client.get(
        (
            "/app/players/new?"
            "return_context=external_game&"
            f"external_game_id={game.id}"
        )
    )

    assert response.status_code == 200

    normalized_html = " ".join(
        response.text.split()
    )

    assert (
        'name="return_context" '
        'value="external_game"'
        in normalized_html
    )

    assert (
        'name="external_game_id" '
        f'value="{game.id}"'
        in normalized_html
    )

    assert (
        f"/app/external-games/"
        f"{game.id}/players"
        in response.text
    )


def test_create_player_returns_to_same_external_game(
    authenticated_client,
    db_session,
):
    game = _external_game(
        db_session
    )

    response = authenticated_client.post(
        "/app/players/new",
        data={
            "full_name": (
                "New External Player"
            ),
            "display_name": "External",
            "return_context": (
                "external_game"
            ),
            "season_id": "",
            "external_game_id": str(
                game.id
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    player = db_session.scalar(
        select(Player).where(
            Player.full_name
            == "New External Player"
        )
    )

    assert player is not None

    assert (
        response.headers["location"]
        == (
            "/app/external-games/"
            f"{game.id}/players?"
            f"new_player_id={player.id}"
        )
    )

    rows = (
        list_external_game_player_stats(
            db_session,
            game.id,
        )
    )

    assert rows == []


def test_new_external_player_is_preselected_only(
    logged_in_client,
    db_session,
):
    game = _external_game(
        db_session
    )

    player = Player(
        full_name="Preselected External",
    )

    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)

    response = logged_in_client.get(
        (
            "/app/external-games/"
            f"{game.id}/players?"
            f"new_player_id={player.id}"
        )
    )

    assert response.status_code == 200

    assert (
        "New Player created and preselected."
        in response.text
    )

    normalized_html = " ".join(
        response.text.split()
    )

    assert (
        f'value="{player.id}" checked'
        in normalized_html
    )

    rows = (
        list_external_game_player_stats(
            db_session,
            game.id,
        )
    )

    assert rows == []


def test_save_preselected_external_player(
    authenticated_client,
    db_session,
):
    game = _external_game(
        db_session
    )

    player = Player(
        full_name="Saved External Player",
    )

    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)

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

    assert (
        response.headers["location"]
        == (
            "/app/external-games/"
            f"{game.id}/stats"
        )
    )

    rows = (
        list_external_game_player_stats(
            db_session,
            game.id,
        )
    )

    assert len(rows) == 1
    assert rows[0].player_id == player.id


def test_external_player_page_has_search(
    logged_in_client,
    db_session,
):
    game = _external_game(
        db_session
    )

    db_session.add_all(
        [
            Player(
                full_name="Alpha Player",
            ),
            Player(
                full_name="Beta Player",
            ),
        ]
    )

    db_session.commit()

    response = logged_in_client.get(
        (
            "/app/external-games/"
            f"{game.id}/players"
        )
    )

    assert response.status_code == 200

    assert "Search Players" in (
        response.text
    )

    assert (
        "data-external-player-search"
        in response.text
    )

    assert "Alpha Player" in response.text
    assert "Beta Player" in response.text


def test_invalid_external_game_context_does_not_create_player(
    authenticated_client,
    db_session,
):
    response = authenticated_client.post(
        "/app/players/new",
        data={
            "full_name": (
                "Should Not Be Created"
            ),
            "display_name": "",
            "return_context": (
                "external_game"
            ),
            "season_id": "",
            "external_game_id": "999999",
        },
        follow_redirects=False,
    )

    assert response.status_code == 422

    player = db_session.scalar(
        select(Player).where(
            Player.full_name
            == "Should Not Be Created"
        )
    )

    assert player is None


def test_untrusted_player_return_context_is_not_used(
    authenticated_client,
    db_session,
):
    game = _external_game(
        db_session
    )

    response = authenticated_client.post(
        "/app/players/new",
        data={
            "full_name": "Safe Redirect Player",
            "display_name": "",
            "return_context": (
                "https://evil.example"
            ),
            "season_id": "",
            "external_game_id": str(
                game.id
            ),
        },
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert (
        response.headers["location"]
        == "/app/players"
    )

    assert (
        "evil.example"
        not in response.headers["location"]
    )