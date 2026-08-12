import pytest

from app.schemas.player import PlayerCreate, PlayerUpdate
from app.services.player import (
    PlayerNotFoundError,
    create_player,
    get_player,
    list_players,
    update_player,
)

def test_create_player(db_session):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
            display_name="J. Smith",
        ),
    )

    assert player.id is not None
    assert player.full_name == "John Smith"
    assert player.display_name == "J. Smith"
    assert player.created_at is not None
    assert player.updated_at is not None


def test_create_player_allows_duplicate_full_names(db_session):
    first_player = create_player(
        db_session,
        PlayerCreate(full_name="John Smith"),
    )

    second_player = create_player(
        db_session,
        PlayerCreate(full_name="John Smith"),
    )

    assert first_player.id != second_player.id
    assert first_player.full_name == second_player.full_name


def test_get_player_returns_existing_player(db_session):
    created_player = create_player(
        db_session,
        PlayerCreate(full_name="John Smith"),
    )

    found_player = get_player(db_session, created_player.id)

    assert found_player.id == created_player.id
    assert found_player.full_name == "John Smith"


def test_get_player_raises_not_found_for_missing_id(db_session):
    with pytest.raises(PlayerNotFoundError):
        get_player(db_session, 999999)


def test_list_players_returns_players_in_id_order(db_session):
    first_player = create_player(
        db_session,
        PlayerCreate(full_name="First Player"),
    )

    second_player = create_player(
        db_session,
        PlayerCreate(full_name="Second Player"),
    )

    players = list_players(db_session)

    assert [player.id for player in players] == [
        first_player.id,
        second_player.id,
    ]


def test_update_player_changes_only_provided_fields(db_session):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
            display_name="J. Smith",
        ),
    )

    updated_player = update_player(
        db_session,
        player.id,
        PlayerUpdate(display_name="Johnny"),
    )

    assert updated_player.full_name == "John Smith"
    assert updated_player.display_name == "Johnny"


def test_update_player_can_clear_display_name(db_session):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
            display_name="J. Smith",
        ),
    )

    updated_player = update_player(
        db_session,
        player.id,
        PlayerUpdate(display_name=None),
    )

    assert updated_player.full_name == "John Smith"
    assert updated_player.display_name is None


def test_update_player_rejects_none_full_name(db_session):
    player = create_player(
        db_session,
        PlayerCreate(full_name="John Smith"),
    )

    with pytest.raises(ValueError):
        update_player(
            db_session,
            player.id,
            PlayerUpdate(full_name=None),
        )


def test_update_player_raises_not_found_for_missing_id(db_session):
    with pytest.raises(PlayerNotFoundError):
        update_player(
            db_session,
            999999,
            PlayerUpdate(display_name="J. Smith"),
        )