from datetime import date, timedelta

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
    list_external_game_player_stats,
)
from app.services.external_game_workflow import (
    finalize_external_game_with_stats,
    sync_external_game_players,
)
from app.services.player import create_player
from app.services.team import create_team


def create_finalize_game(
    db_session,
    *,
    game_date: date | None = None,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="Finalize Opponent",
            abbreviation="FIN",
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Finalize Test",
            opponent_team_id=opponent.id,
            game_date=(
                game_date
                or date.today()
            ),
            venue_type=VenueType.NEUTRAL,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Finalize Player",
        ),
    )

    sync_external_game_players(
        db_session,
        game.id,
        [player.id],
    )

    return game, player


def played_row(
    game_id: int,
    player_id: int,
    *,
    assists: int = 0,
):
    return ExternalGamePlayerStatsCreate(
        external_game_id=game_id,
        player_id=player_id,
        participation_status="PLAYED",
        three_point_attempts=0,
        three_point_makes=0,
        two_point_attempts=0,
        two_point_makes=0,
        free_throw_attempts=0,
        free_throw_makes=0,
        turnovers=0,
        assists=assists,
        offensive_rebounds=0,
        defensive_rebounds=0,
        steals=0,
        deflections=0,
        personal_fouls=0,
    )


def test_successful_external_game_finalization(
    db_session,
):
    game, player = create_finalize_game(
        db_session
    )

    finalize_external_game_with_stats(
        db_session,
        game.id,
        [
            played_row(
                game.id,
                player.id,
                assists=5,
            )
        ],
        opponent_score=65,
    )

    db_session.refresh(game)

    assert game.status == GameStatus.COMPLETED
    assert game.opponent_score == 65

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert rows[0].assists == 5


def test_finalize_missing_score_rolls_back(
    db_session,
):
    game, player = create_finalize_game(
        db_session
    )

    try:
        finalize_external_game_with_stats(
            db_session,
            game.id,
            [
                played_row(
                    game.id,
                    player.id,
                    assists=7,
                )
            ],
            opponent_score=None,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected finalization to fail."
        )

    db_session.refresh(game)

    assert game.status == GameStatus.DRAFT
    assert game.opponent_score is None

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    # Submitted assists=7 must roll back.
    assert rows[0].assists == 0


def test_finalize_future_game_rolls_back(
    db_session,
):
    game, player = create_finalize_game(
        db_session,
        game_date=(
            date.today()
            + timedelta(days=1)
        ),
    )

    try:
        finalize_external_game_with_stats(
            db_session,
            game.id,
            [
                played_row(
                    game.id,
                    player.id,
                    assists=9,
                )
            ],
            opponent_score=70,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected future game finalization "
            "to fail."
        )

    db_session.refresh(game)

    assert game.status == GameStatus.DRAFT
    assert game.opponent_score is None

    rows = list_external_game_player_stats(
        db_session,
        game.id,
    )

    assert rows[0].assists == 0


def test_finalize_dnp_only_rejected(
    db_session,
):
    game, player = create_finalize_game(
        db_session
    )

    dnp_row = ExternalGamePlayerStatsCreate(
        external_game_id=game.id,
        player_id=player.id,
        participation_status="DID_NOT_PLAY",
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

    try:
        finalize_external_game_with_stats(
            db_session,
            game.id,
            [dnp_row],
            opponent_score=50,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected DNP-only finalization "
            "to fail."
        )

    db_session.refresh(game)

    assert game.status == GameStatus.DRAFT
    assert game.opponent_score is None


def test_finalize_without_stats_rejected(
    db_session,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="No Stats Opponent",
            abbreviation="NS",
        ),
    )

    game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="No Stats Game",
            opponent_team_id=opponent.id,
            game_date=date.today(),
            venue_type=VenueType.HOME,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    try:
        finalize_external_game_with_stats(
            db_session,
            game.id,
            [],
            opponent_score=40,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Expected no-stats finalization "
            "to fail."
        )

    db_session.refresh(game)

    assert game.status == GameStatus.DRAFT
    assert game.opponent_score is None