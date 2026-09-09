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
from app.schemas.external_game_player_stats import (
    ExternalGamePlayerStatsCreate,
)
from app.schemas.player import PlayerCreate
from app.schemas.team import TeamCreate
from app.services.external_game import (
    create_external_game,
)
from app.services.external_game_workflow import (
    finalize_external_game_with_stats,
    sync_external_game_players,
)
from app.services.player import create_player
from app.services.team import create_team


def _create_completed_game(
    db_session,
    *,
    name: str,
    opponent_name: str,
    player,
    game_date: date,
    opponent_score: int,
    two_makes: int,
    two_attempts: int,
    three_makes: int,
    three_attempts: int,
    free_makes: int,
    free_attempts: int,
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
        [player.id],
    )

    stats = ExternalGamePlayerStatsCreate(
        external_game_id=game.id,
        player_id=player.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        two_point_makes=two_makes,
        two_point_attempts=two_attempts,
        three_point_makes=three_makes,
        three_point_attempts=three_attempts,
        free_throw_makes=free_makes,
        free_throw_attempts=free_attempts,
        turnovers=2,
        assists=4,
        offensive_rebounds=2,
        defensive_rebounds=3,
        steals=1,
        deflections=2,
        personal_fouls=2,
    )

    finalize_external_game_with_stats(
        db_session,
        game.id,
        [stats],
        opponent_score=opponent_score,
    )

    return game


def test_analysis_requires_login(
    client,
):
    response = client.get(
        "/app/external-games/analysis",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert (
        response.headers["location"]
        == "/login"
    )


def test_zero_analysis_selection_rejected(
    logged_in_client,
):
    response = logged_in_client.get(
        "/app/external-games/analysis"
    )

    assert response.status_code == 422
    assert (
        "Select at least one"
        in response.text
    )
    assert (
        "Back to External Games"
        in response.text
    )


def test_one_game_redirects_to_report(
    logged_in_client,
    db_session,
):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Analysis Player",
        ),
    )

    game = _create_completed_game(
        db_session,
        name="Single Analysis Game",
        opponent_name="Single Opponent",
        player=player,
        game_date=date(2026, 9, 1),
        opponent_score=10,
        two_makes=3,
        two_attempts=6,
        three_makes=2,
        three_attempts=4,
        free_makes=2,
        free_attempts=2,
    )

    response = logged_in_client.get(
        (
            "/app/external-games/analysis"
            f"?game_ids={game.id}"
        ),
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert response.headers[
        "location"
    ] == (
        f"/app/external-games/{game.id}/report"
    )


def test_multiple_games_render_analysis(
    logged_in_client,
    db_session,
):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Aggregate Player",
        ),
    )

    game_one = _create_completed_game(
        db_session,
        name="Aggregate Game One",
        opponent_name="Aggregate Opponent One",
        player=player,
        game_date=date(2026, 9, 1),
        opponent_score=10,
        two_makes=3,
        two_attempts=6,
        three_makes=2,
        three_attempts=4,
        free_makes=2,
        free_attempts=2,
    )

    game_two = _create_completed_game(
        db_session,
        name="Aggregate Game Two",
        opponent_name="Aggregate Opponent Two",
        player=player,
        game_date=date(2026, 9, 2),
        opponent_score=20,
        two_makes=4,
        two_attempts=8,
        three_makes=1,
        three_attempts=6,
        free_makes=3,
        free_attempts=4,
    )

    response = logged_in_client.get(
        (
            "/app/external-games/analysis"
            f"?game_ids={game_one.id}"
            f"&game_ids={game_two.id}"
        )
    )

    assert response.status_code == 200

    html = response.text

    assert "External Game Analysis" in html
    assert "2 Selected Games" in html
    assert "Aggregate Player" in html
    assert "Aggregate Game One" in html
    assert "Aggregate Game Two" in html


def test_duplicate_analysis_ids_rejected(
    logged_in_client,
    db_session,
):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Duplicate Player",
        ),
    )

    game = _create_completed_game(
        db_session,
        name="Duplicate Game",
        opponent_name="Duplicate Opponent",
        player=player,
        game_date=date(2026, 9, 1),
        opponent_score=10,
        two_makes=1,
        two_attempts=2,
        three_makes=1,
        three_attempts=2,
        free_makes=1,
        free_attempts=2,
    )

    response = logged_in_client.get(
        (
            "/app/external-games/analysis"
            f"?game_ids={game.id}"
            f"&game_ids={game.id}"
        )
    )

    assert response.status_code == 422
    assert "Duplicate" in response.text


def test_draft_game_cannot_be_analyzed(
    logged_in_client,
    db_session,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="Draft Analysis Opponent",
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Draft Analysis Game",
            opponent_team_id=opponent.id,
            game_date=date(2026, 9, 1),
            venue_type=VenueType.HOME,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    response = logged_in_client.get(
        (
            "/app/external-games/analysis"
            f"?game_ids={game.id}"
        )
    )

    assert response.status_code == 409
    assert (
        "must be completed"
        in response.text
    )
    assert (
        "Back to External Games"
        in response.text
    )


def test_missing_analysis_game_returns_404(
    logged_in_client,
):
    response = logged_in_client.get(
        (
            "/app/external-games/analysis"
            "?game_ids=999999"
        )
    )

    assert response.status_code == 404
    assert (
        "External game not found."
        in response.text
    )
    assert (
        "Back to External Games"
        in response.text
    )
