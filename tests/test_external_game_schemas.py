from datetime import date

import pytest
from pydantic import ValidationError

from app.models.game import (
    GameStatus,
    VenueType,
)
from app.models.player_game_stats import (
    ParticipationStatus,
)
from app.schemas.external_game import (
    ExternalGameCreate,
    ExternalGameUpdate,
)
from app.schemas.external_game_player_stats import (
    ExternalGamePlayerStatsCreate,
)


def test_external_game_create_trims_name():
    data = ExternalGameCreate(
        name="  Preseason Showcase  ",
        opponent_team_id=1,
        game_date=date(2026, 9, 1),
        venue_type=VenueType.NEUTRAL,
    )

    assert data.name == "Preseason Showcase"
    assert data.status == GameStatus.DRAFT


def test_external_game_create_rejects_blank_name():
    with pytest.raises(
        ValidationError,
        match="External game name cannot be blank",
    ):
        ExternalGameCreate(
            name="   ",
            opponent_team_id=1,
            game_date=date(2026, 9, 1),
            venue_type=VenueType.HOME,
        )


def test_external_game_rejects_negative_opponent_score():
    with pytest.raises(ValidationError):
        ExternalGameCreate(
            name="Test Game",
            opponent_team_id=1,
            game_date=date(2026, 9, 1),
            venue_type=VenueType.HOME,
            opponent_score=-1,
        )


def test_external_game_update_preserves_unset_fields():
    update = ExternalGameUpdate(
        notes="Updated notes"
    )

    assert update.model_dump(
        exclude_unset=True
    ) == {
        "notes": "Updated notes",
    }


def test_external_game_update_allows_explicit_score_clear():
    update = ExternalGameUpdate(
        opponent_score=None
    )

    assert update.model_dump(
        exclude_unset=True
    ) == {
        "opponent_score": None,
    }


def test_external_stats_accept_valid_played_row():
    stats = ExternalGamePlayerStatsCreate(
        external_game_id=1,
        player_id=2,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        three_point_attempts=4,
        three_point_makes=2,
        two_point_attempts=6,
        two_point_makes=3,
        free_throw_attempts=4,
        free_throw_makes=3,
        assists=4,
        turnovers=2,
    )

    assert stats.three_point_makes == 2
    assert stats.two_point_makes == 3


def test_external_stats_reject_makes_above_attempts():
    with pytest.raises(ValidationError):
        ExternalGamePlayerStatsCreate(
            external_game_id=1,
            player_id=2,
            participation_status=(
                ParticipationStatus.PLAYED
            ),
            three_point_attempts=2,
            three_point_makes=3,
        )


def test_external_stats_reject_nonzero_dnp():
    with pytest.raises(
        ValidationError,
        match=(
            "DID_NOT_PLAY requires all "
            "statistics to be zero"
        ),
    ):
        ExternalGamePlayerStatsCreate(
            external_game_id=1,
            player_id=2,
            participation_status=(
                ParticipationStatus.DID_NOT_PLAY
            ),
            assists=1,
        )


def test_external_stats_accept_zero_stat_dnp():
    stats = ExternalGamePlayerStatsCreate(
        external_game_id=1,
        player_id=2,
        participation_status=(
            ParticipationStatus.DID_NOT_PLAY
        ),
    )

    assert stats.assists == 0
    assert stats.three_point_attempts == 0


def test_external_stats_accept_zero_stat_played():
    stats = ExternalGamePlayerStatsCreate(
        external_game_id=1,
        player_id=2,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
    )

    assert stats.assists == 0
    assert stats.two_point_makes == 0