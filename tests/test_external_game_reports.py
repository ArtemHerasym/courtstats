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


def _create_completed_external_game(
    db_session,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="Report Opponent",
            abbreviation="RPT",
        ),
    )

    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Report Player",
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Report Showcase",
            opponent_team_id=opponent.id,
            game_date=date(
                2026,
                9,
                1,
            ),
            venue_type=VenueType.HOME,
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
        three_point_attempts=4,
        three_point_makes=2,
        two_point_attempts=6,
        two_point_makes=3,
        free_throw_attempts=4,
        free_throw_makes=3,
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
        opponent_score=12,
    )

    return game, player


def test_external_game_report_requires_login(
    client,
):
    response = client.get(
        "/app/external-games/1/report",
        follow_redirects=False,
    )

    assert response.status_code == 303

    assert (
        response.headers["location"]
        == "/login"
    )


def test_completed_external_game_report_renders(
    logged_in_client,
    db_session,
):
    game, _ = (
        _create_completed_external_game(
            db_session
        )
    )

    response = logged_in_client.get(
        (
            "/app/external-games/"
            f"{game.id}/report"
        )
    )

    assert response.status_code == 200

    html = response.text

    assert "External Game Report" in html
    assert "Report Showcase" in html
    assert "Report Opponent" in html
    assert "Report Player" in html

    assert "WIN" in html

    assert "15" in html
    assert "12" in html
    assert "+3" in html

    assert "50.0%" in html
    assert "75.0%" in html

    assert "2.00" in html

    assert (
        "/app/external-games/"
        f"{game.id}/stats"
        in html
    )


def test_external_game_report_missing_game_returns_404(
    logged_in_client,
):
    response = logged_in_client.get(
        "/app/external-games/999999/report"
    )

    assert response.status_code == 404

    assert (
        "External game not found."
        in response.text
    )


def test_external_game_report_rejects_draft(
    logged_in_client,
    db_session,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="Draft Report Opponent",
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Draft Report Game",
            opponent_team_id=opponent.id,
            game_date=date(
                2026,
                9,
                1,
            ),
            venue_type=VenueType.AWAY,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    response = logged_in_client.get(
        (
            "/app/external-games/"
            f"{game.id}/report"
        )
    )

    assert response.status_code == 409

    assert (
        "must be completed"
        in response.text
    )


def test_completed_external_game_library_has_report_link(
    logged_in_client,
    db_session,
):
    game, _ = (
        _create_completed_external_game(
            db_session
        )
    )

    response = logged_in_client.get(
        "/app/external-games"
    )

    assert response.status_code == 200

    assert "View Report" in response.text
    assert "Edit Stats" in response.text

    assert (
        "/app/external-games/"
        f"{game.id}/report"
        in response.text
    )