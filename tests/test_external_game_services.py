from datetime import date, timedelta

import pytest

from app.models.game import (
    GameStatus,
    VenueType,
)
from app.models.player import Player
from app.models.player_game_stats import (
    ParticipationStatus,
)
from app.models.team import Team
from app.schemas.external_game import (
    ExternalGameCreate,
    ExternalGameUpdate,
)
from app.schemas.external_game_player_stats import (
    ExternalGamePlayerStatsCreate,
    ExternalGamePlayerStatsUpdate,
)
from app.services.external_game import (
    create_external_game,
    update_external_game,
)
from app.services.external_game_player_stats import (
    ExternalGamePlayerStatsConflictError,
    create_external_game_player_stats,
    update_external_game_player_stats,
)


def _create_team(
    db_session,
    name: str,
) -> Team:
    team = Team(
        name=name,
        abbreviation=name[:4],
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _create_player(
    db_session,
    name: str,
) -> Player:
    player = Player(
        full_name=name,
    )
    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)
    return player


def _create_external_game(
    db_session,
    opponent: Team,
    *,
    game_date: date | None = None,
):
    return create_external_game(
        db_session,
        ExternalGameCreate(
            name="Preseason Showcase",
            opponent_team_id=opponent.id,
            game_date=(
                game_date
                or date.today()
            ),
            venue_type=VenueType.NEUTRAL,
        ),
    )


def test_new_external_game_starts_draft(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Opponent One",
    )

    game = _create_external_game(
        db_session,
        opponent,
    )

    assert game.status == GameStatus.DRAFT
    assert game.opponent_score is None


def test_future_external_draft_is_allowed(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Future Opponent",
    )

    game = _create_external_game(
        db_session,
        opponent,
        game_date=(
            date.today()
            + timedelta(days=5)
        ),
    )

    assert game.status == GameStatus.DRAFT


def test_future_external_completion_is_rejected(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Future Complete Opponent",
    )
    player = _create_player(
        db_session,
        "Future Player",
    )

    game = _create_external_game(
        db_session,
        opponent,
        game_date=(
            date.today()
            + timedelta(days=1)
        ),
    )

    create_external_game_player_stats(
        db_session,
        ExternalGamePlayerStatsCreate(
            external_game_id=game.id,
            player_id=player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="Future-dated",
    ):
        update_external_game(
            db_session,
            game.id,
            ExternalGameUpdate(
                opponent_score=0,
                status=GameStatus.COMPLETED,
            ),
        )


def test_completion_requires_opponent_score(
    db_session,
):
    opponent = _create_team(
        db_session,
        "No Score Opponent",
    )
    player = _create_player(
        db_session,
        "No Score Player",
    )

    game = _create_external_game(
        db_session,
        opponent,
    )

    create_external_game_player_stats(
        db_session,
        ExternalGamePlayerStatsCreate(
            external_game_id=game.id,
            player_id=player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="opponent score",
    ):
        update_external_game(
            db_session,
            game.id,
            ExternalGameUpdate(
                status=GameStatus.COMPLETED
            ),
        )


def test_completion_requires_player_rows(
    db_session,
):
    opponent = _create_team(
        db_session,
        "No Rows Opponent",
    )

    game = _create_external_game(
        db_session,
        opponent,
    )

    with pytest.raises(
        ValueError,
        match="at least one player stats row",
    ):
        update_external_game(
            db_session,
            game.id,
            ExternalGameUpdate(
                opponent_score=0,
                status=GameStatus.COMPLETED,
            ),
        )


def test_dnp_only_completion_is_rejected(
    db_session,
):
    opponent = _create_team(
        db_session,
        "DNP Opponent",
    )
    player = _create_player(
        db_session,
        "DNP Player",
    )

    game = _create_external_game(
        db_session,
        opponent,
    )

    create_external_game_player_stats(
        db_session,
        ExternalGamePlayerStatsCreate(
            external_game_id=game.id,
            player_id=player.id,
            participation_status=(
                ParticipationStatus.DID_NOT_PLAY
            ),
        ),
    )

    with pytest.raises(
        ValueError,
        match="at least one PLAYED",
    ):
        update_external_game(
            db_session,
            game.id,
            ExternalGameUpdate(
                opponent_score=0,
                status=GameStatus.COMPLETED,
            ),
        )


def test_valid_external_completion_succeeds(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Valid Opponent",
    )
    player = _create_player(
        db_session,
        "Valid Player",
    )

    game = _create_external_game(
        db_session,
        opponent,
    )

    create_external_game_player_stats(
        db_session,
        ExternalGamePlayerStatsCreate(
            external_game_id=game.id,
            player_id=player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),
            two_point_attempts=5,
            two_point_makes=3,
        ),
    )

    updated = update_external_game(
        db_session,
        game.id,
        ExternalGameUpdate(
            opponent_score=4,
            status=GameStatus.COMPLETED,
        ),
    )

    assert updated.status == GameStatus.COMPLETED
    assert updated.opponent_score == 4


def test_valid_completed_game_edit_succeeds(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Edit Opponent",
    )
    player = _create_player(
        db_session,
        "Edit Player",
    )

    game = _create_external_game(
        db_session,
        opponent,
    )

    stats = create_external_game_player_stats(
        db_session,
        ExternalGamePlayerStatsCreate(
            external_game_id=game.id,
            player_id=player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),
            assists=2,
        ),
    )

    update_external_game(
        db_session,
        game.id,
        ExternalGameUpdate(
            opponent_score=8,
            status=GameStatus.COMPLETED,
        ),
    )

    updated = update_external_game_player_stats(
        db_session,
        stats.id,
        ExternalGamePlayerStatsUpdate(
            assists=5,
        ),
    )

    assert updated.assists == 5


def test_completed_game_cannot_lose_last_played_player(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Last Played Opponent",
    )
    player = _create_player(
        db_session,
        "Last Played Player",
    )

    game = _create_external_game(
        db_session,
        opponent,
    )

    stats = create_external_game_player_stats(
        db_session,
        ExternalGamePlayerStatsCreate(
            external_game_id=game.id,
            player_id=player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),
        ),
    )

    update_external_game(
        db_session,
        game.id,
        ExternalGameUpdate(
            opponent_score=0,
            status=GameStatus.COMPLETED,
        ),
    )

    with pytest.raises(
        ValueError,
        match="at least one PLAYED",
    ):
        update_external_game_player_stats(
            db_session,
            stats.id,
            ExternalGamePlayerStatsUpdate(
                participation_status=(
                    ParticipationStatus.DID_NOT_PLAY
                ),
            ),
        )


def test_external_player_needs_no_season_roster(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Global Player Opponent",
    )
    player = _create_player(
        db_session,
        "Global Only Player",
    )

    game = _create_external_game(
        db_session,
        opponent,
    )

    stats = create_external_game_player_stats(
        db_session,
        ExternalGamePlayerStatsCreate(
            external_game_id=game.id,
            player_id=player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),
        ),
    )

    assert stats.player_id == player.id


def test_same_player_can_appear_in_different_external_games(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Multi Game Opponent",
    )
    player = _create_player(
        db_session,
        "Multi Game Player",
    )

    game_one = _create_external_game(
        db_session,
        opponent,
    )

    game_two = _create_external_game(
        db_session,
        opponent,
    )

    first = create_external_game_player_stats(
        db_session,
        ExternalGamePlayerStatsCreate(
            external_game_id=game_one.id,
            player_id=player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),
        ),
    )

    second = create_external_game_player_stats(
        db_session,
        ExternalGamePlayerStatsCreate(
            external_game_id=game_two.id,
            player_id=player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),
        ),
    )

    assert first.id != second.id


def test_same_player_cannot_appear_twice_in_same_external_game(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Duplicate Opponent",
    )
    player = _create_player(
        db_session,
        "Duplicate Player",
    )

    game = _create_external_game(
        db_session,
        opponent,
    )

    data = ExternalGamePlayerStatsCreate(
        external_game_id=game.id,
        player_id=player.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
    )

    create_external_game_player_stats(
        db_session,
        data,
    )

    with pytest.raises(
        ExternalGamePlayerStatsConflictError,
    ):
        create_external_game_player_stats(
            db_session,
            data,
        )