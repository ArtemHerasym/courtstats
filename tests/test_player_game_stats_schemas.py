from datetime import datetime, timezone
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

from app.models.player_game_stats import ParticipationStatus
from app.schemas.player_game_stats import (
    PlayerGameStatsCreate,
    PlayerGameStatsRead,
    PlayerGameStatsUpdate,
)


def test_player_game_stats_create_valid_played():
    stats = PlayerGameStatsCreate(
        game_id=1,
        season_roster_id=2,
        participation_status=ParticipationStatus.PLAYED,
        three_point_attempts=5,
        three_point_makes=2,
        two_point_attempts=8,
        two_point_makes=4,
        free_throw_attempts=3,
        free_throw_makes=2,
        turnovers=2,
        assists=6,
        offensive_rebounds=1,
        defensive_rebounds=5,
        steals=2,
        deflections=3,
        personal_fouls=2,
    )

    assert stats.game_id == 1
    assert stats.season_roster_id == 2
    assert stats.participation_status == ParticipationStatus.PLAYED
    assert stats.three_point_attempts == 5
    assert stats.three_point_makes == 2
    assert stats.assists == 6
    assert stats.steals == 2


def test_player_game_stats_create_valid_played_all_zero_stats():
    stats = PlayerGameStatsCreate(
        game_id=1,
        season_roster_id=2,
        participation_status=ParticipationStatus.PLAYED,
    )

    assert stats.participation_status == ParticipationStatus.PLAYED
    assert stats.three_point_attempts == 0
    assert stats.assists == 0
    assert stats.personal_fouls == 0


def test_player_game_stats_create_valid_dnp_with_zero_stats():
    stats = PlayerGameStatsCreate(
        game_id=1,
        season_roster_id=2,
        participation_status=ParticipationStatus.DID_NOT_PLAY,
    )

    assert stats.participation_status == ParticipationStatus.DID_NOT_PLAY
    assert stats.three_point_attempts == 0
    assert stats.three_point_makes == 0
    assert stats.assists == 0
    assert stats.personal_fouls == 0


def test_player_game_stats_create_rejects_dnp_with_nonzero_stat():
    with pytest.raises(
        ValidationError,
        match="DID_NOT_PLAY requires all statistics to be zero",
    ):
        PlayerGameStatsCreate(
            game_id=1,
            season_roster_id=2,
            participation_status=ParticipationStatus.DID_NOT_PLAY,
            assists=1,
        )


def test_player_game_stats_create_rejects_negative_stat():
    with pytest.raises(ValidationError):
        PlayerGameStatsCreate(
            game_id=1,
            season_roster_id=2,
            participation_status=ParticipationStatus.PLAYED,
            turnovers=-1,
        )


def test_player_game_stats_create_rejects_three_point_makes_above_attempts():
    with pytest.raises(
        ValidationError,
        match="Three-point makes cannot exceed three-point attempts",
    ):
        PlayerGameStatsCreate(
            game_id=1,
            season_roster_id=2,
            participation_status=ParticipationStatus.PLAYED,
            three_point_attempts=4,
            three_point_makes=5,
        )


def test_player_game_stats_create_rejects_two_point_makes_above_attempts():
    with pytest.raises(
        ValidationError,
        match="Two-point makes cannot exceed two-point attempts",
    ):
        PlayerGameStatsCreate(
            game_id=1,
            season_roster_id=2,
            participation_status=ParticipationStatus.PLAYED,
            two_point_attempts=6,
            two_point_makes=7,
        )


def test_player_game_stats_create_rejects_free_throw_makes_above_attempts():
    with pytest.raises(
        ValidationError,
        match="Free-throw makes cannot exceed free-throw attempts",
    ):
        PlayerGameStatsCreate(
            game_id=1,
            season_roster_id=2,
            participation_status=ParticipationStatus.PLAYED,
            free_throw_attempts=2,
            free_throw_makes=3,
        )


def test_player_game_stats_update_allows_partial_update():
    update = PlayerGameStatsUpdate(
        assists=7,
        steals=3,
    )

    assert update.assists == 7
    assert update.steals == 3

    assert update.model_dump(exclude_unset=True) == {
        "assists": 7,
        "steals": 3,
    }


def test_player_game_stats_update_allows_incomplete_cross_field_state():
    update = PlayerGameStatsUpdate(
        three_point_makes=6,
    )

    assert update.model_dump(exclude_unset=True) == {
        "three_point_makes": 6,
    }


def test_player_game_stats_update_rejects_negative_stat():
    with pytest.raises(ValidationError):
        PlayerGameStatsUpdate(
            defensive_rebounds=-1,
        )


def test_player_game_stats_read_from_attributes():
    now = datetime.now(timezone.utc)

    orm_object = SimpleNamespace(
        id=10,
        game_id=3,
        season_roster_id=7,
        participation_status=ParticipationStatus.PLAYED,
        three_point_attempts=5,
        three_point_makes=2,
        two_point_attempts=8,
        two_point_makes=4,
        free_throw_attempts=3,
        free_throw_makes=2,
        turnovers=1,
        assists=6,
        offensive_rebounds=2,
        defensive_rebounds=5,
        steals=2,
        deflections=3,
        personal_fouls=2,
        created_at=now,
        updated_at=now,
    )

    stats = PlayerGameStatsRead.model_validate(
        orm_object
    )

    assert stats.id == 10
    assert stats.game_id == 3
    assert stats.season_roster_id == 7
    assert stats.participation_status == ParticipationStatus.PLAYED
    assert stats.assists == 6
    assert stats.three_point_attempts == 5
    assert stats.created_at == now
    assert stats.updated_at == now