from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.player import PlayerCreate, PlayerRead, PlayerUpdate

def test_player_create_valid_minimal():
    player = PlayerCreate(full_name="John Smith")

    assert player.full_name == "John Smith"
    assert player.display_name is None


def test_player_create_trims_names():
    player = PlayerCreate(
        full_name="  John Smith  ",
        display_name="  J. Smith  ",
    )

    assert player.full_name == "John Smith"
    assert player.display_name == "J. Smith"


def test_player_create_rejects_blank_full_name():
    with pytest.raises(ValidationError):
        PlayerCreate(full_name="   ")


def test_player_create_rejects_blank_display_name():
    with pytest.raises(ValidationError):
        PlayerCreate(
            full_name="John Smith",
            display_name="   ",
        )


def test_player_update_allows_partial_update():
    update = PlayerUpdate(display_name="J. Smith")

    assert update.full_name is None
    assert update.display_name == "J. Smith"


def test_player_update_rejects_blank_full_name():
    with pytest.raises(ValidationError):
        PlayerUpdate(full_name="   ")


def test_player_update_rejects_blank_display_name():
    with pytest.raises(ValidationError):
        PlayerUpdate(display_name="   ")


def test_player_update_exclude_unset():
    update = PlayerUpdate(display_name="J. Smith")

    assert update.model_dump(exclude_unset=True) == {
        "display_name": "J. Smith",
    }


def test_player_update_can_explicitly_clear_display_name():
    update = PlayerUpdate(display_name=None)

    assert update.model_dump(exclude_unset=True) == {
        "display_name": None,
    }


def test_player_read_from_attributes():
    class FakePlayer:
        id = 1
        full_name = "John Smith"
        display_name = "J. Smith"
        created_at = datetime(2026, 8, 11, 12, 0, tzinfo=timezone.utc)
        updated_at = datetime(2026, 8, 11, 13, 0, tzinfo=timezone.utc)

    player = PlayerRead.model_validate(FakePlayer())

    assert player.id == 1
    assert player.full_name == "John Smith"
    assert player.display_name == "J. Smith"