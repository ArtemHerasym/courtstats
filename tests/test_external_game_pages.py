from datetime import date

from app.models.game import (
    GameStatus,
    VenueType,
)
from app.schemas.external_game import (
    ExternalGameCreate,
)
from app.schemas.team import TeamCreate
from app.services.external_game import (
    create_external_game,
)
from app.services.team import create_team


def test_external_games_requires_login(
    client,
):
    response = client.get(
        "/app/external-games",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"]
        == "/login"
    )


def test_external_games_empty_library(
    logged_in_client,
):
    response = logged_in_client.get(
        "/app/external-games"
    )

    assert response.status_code == 200

    assert (
        "External Games"
        in response.text
    )

    assert (
        "No external games"
        in response.text
    )


def test_external_games_nav_link(
    logged_in_client,
):
    response = logged_in_client.get(
        "/"
    )

    assert response.status_code == 200

    assert (
        "External Games"
        in response.text
    )

    assert (
        "/app/external-games"
        in response.text
    )


def test_saved_external_game_appears_in_library(
    logged_in_client,
    db_session,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="External Opponent",
            abbreviation="EXT",
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Fall Showcase",
            opponent_team_id=opponent.id,
            game_date=date(
                2026,
                9,
                1,
            ),
            venue_type=VenueType.NEUTRAL,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    response = logged_in_client.get(
        "/app/external-games"
    )

    assert response.status_code == 200

    assert (
        "Fall Showcase"
        in response.text
    )

    assert (
        "External Opponent"
        in response.text
    )

    assert (
        "09/01/2026"
        in response.text
    )

    assert (
        "NEUTRAL"
        in response.text
    )

    assert (
        "DRAFT"
        in response.text
    )

    assert (
        "Continue"
        in response.text
    )

    assert (
        (
            "/app/external-games/"
            f"{game.id}/players"
        )
        in response.text
    )


def test_completed_external_game_links_to_stats(
    logged_in_client,
    db_session,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="Completed Opponent",
            abbreviation="COMP",
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Completed Showcase",
            opponent_team_id=opponent.id,
            game_date=date(
                2026,
                9,
                2,
            ),
            venue_type=VenueType.AWAY,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    game.status = GameStatus.COMPLETED
    game.opponent_score = 61

    db_session.commit()
    db_session.refresh(game)

    response = logged_in_client.get(
        "/app/external-games"
    )

    assert response.status_code == 200

    assert (
        "Completed Showcase"
        in response.text
    )

    assert (
        "COMPLETED"
        in response.text
    )

    assert (
        "Edit Stats"
        in response.text
    )

    assert (
        (
            "/app/external-games/"
            f"{game.id}/stats"
        )
        in response.text
    )