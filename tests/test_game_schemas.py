from datetime import date, datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.game import GameStatus, VenueType
from app.schemas.game import GameCreate, GameRead, GameUpdate


def test_game_create_valid_draft():
    game = GameCreate(
        season_id=1,
        opponent_team_id=2,
        game_date=date(2026, 10, 29),
        venue_type=VenueType.HOME,
    )

    assert game.season_id == 1
    assert game.opponent_team_id == 2
    assert game.game_date == date(2026, 10, 29)
    assert game.venue_type == VenueType.HOME
    assert game.status == GameStatus.DRAFT
    assert game.opponent_score is None
    assert game.notes is None


def test_game_create_rejects_negative_opponent_score():
    with pytest.raises(ValidationError):
        GameCreate(
            season_id=1,
            opponent_team_id=2,
            game_date=date(2026, 10, 29),
            venue_type=VenueType.AWAY,
            opponent_score=-1,
        )


def test_game_update_allows_partial_update():
    update = GameUpdate(
        opponent_score=72,
    )

    assert update.opponent_score == 72
    assert update.season_id is None
    assert update.opponent_team_id is None
    assert update.game_date is None
    assert update.venue_type is None
    assert update.status is None


def test_game_update_exclude_unset():
    update = GameUpdate(
        opponent_score=72,
    )

    assert update.model_dump(exclude_unset=True) == {
        "opponent_score": 72,
    }


def test_game_update_can_explicitly_clear_optional_fields():
    update = GameUpdate(
        opponent_score=None,
        notes=None,
    )

    assert update.model_dump(exclude_unset=True) == {
        "opponent_score": None,
        "notes": None,
    }


def test_game_update_rejects_negative_opponent_score():
    with pytest.raises(ValidationError):
        GameUpdate(
            opponent_score=-1,
        )


def test_game_create_validates_enum_values():
    with pytest.raises(ValidationError):
        GameCreate(
            season_id=1,
            opponent_team_id=2,
            game_date=date(2026, 10, 29),
            venue_type="INVALID",
        )

    with pytest.raises(ValidationError):
        GameCreate(
            season_id=1,
            opponent_team_id=2,
            game_date=date(2026, 10, 29),
            venue_type=VenueType.HOME,
            status="INVALID",
        )


def test_game_schema_allows_completed_without_score_for_service_validation():
    game = GameCreate(
        season_id=1,
        opponent_team_id=2,
        game_date=date(2026, 10, 29),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
    )

    assert game.status == GameStatus.COMPLETED
    assert game.opponent_score is None


def test_game_read_from_attributes():
    class FakeGame:
        id = 1
        season_id = 2
        opponent_team_id = 3
        game_date = date(2026, 10, 29)
        venue_type = VenueType.NEUTRAL
        status = GameStatus.DRAFT
        opponent_score = None
        notes = "Tournament game"
        created_at = datetime(
            2026,
            8,
            16,
            12,
            0,
            tzinfo=timezone.utc,
        )
        updated_at = datetime(
            2026,
            8,
            16,
            13,
            0,
            tzinfo=timezone.utc,
        )

    game = GameRead.model_validate(FakeGame())

    assert game.id == 1
    assert game.season_id == 2
    assert game.opponent_team_id == 3
    assert game.game_date == date(2026, 10, 29)
    assert game.venue_type == VenueType.NEUTRAL
    assert game.status == GameStatus.DRAFT
    assert game.opponent_score is None
    assert game.notes == "Tournament game"