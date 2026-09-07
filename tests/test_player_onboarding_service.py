import pytest
from sqlalchemy import func, select

from app.models.player import Player
from app.schemas.player import PlayerCreate
from app.services.player import (
    create_player,
    create_players,
    get_player,
    search_players,
)


def test_search_players_matches_full_name(
    db_session,
):
    first = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
        ),
    )

    create_player(
        db_session,
        PlayerCreate(
            full_name="Michael Brown",
        ),
    )

    results = search_players(
        db_session,
        "Smith",
    )

    assert [
        player.id
        for player in results
    ] == [
        first.id,
    ]


def test_search_players_is_case_insensitive(
    db_session,
):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
        ),
    )

    results = search_players(
        db_session,
        "jOhN sMiTh",
    )

    assert len(results) == 1
    assert results[0].id == player.id


def test_search_players_matches_partial_name(
    db_session,
):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Alexander Johnson",
        ),
    )

    results = search_players(
        db_session,
        "john",
    )

    assert len(results) == 1
    assert results[0].id == player.id


def test_search_players_matches_display_name(
    db_session,
):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Jonathan Smith",
            display_name="Johnny",
        ),
    )

    results = search_players(
        db_session,
        "johnny",
    )

    assert len(results) == 1
    assert results[0].id == player.id


def test_search_players_trims_query_whitespace(
    db_session,
):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
        ),
    )

    results = search_players(
        db_session,
        "  Smith  ",
    )

    assert len(results) == 1
    assert results[0].id == player.id


def test_search_players_blank_query_returns_empty_list(
    db_session,
):
    create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
        ),
    )

    assert (
        search_players(
            db_session,
            "   ",
        )
        == []
    )


def test_search_does_not_merge_same_name_players(
    db_session,
):
    first = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
        ),
    )

    second = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
        ),
    )

    results = search_players(
        db_session,
        "John Smith",
    )

    result_ids = {
        player.id
        for player in results
    }

    assert result_ids == {
        first.id,
        second.id,
    }


def test_existing_player_can_be_explicitly_reused(
    db_session,
):
    player = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
        ),
    )

    selected_player = get_player(
        db_session,
        player.id,
    )

    assert selected_player.id == player.id


def test_explicit_create_new_does_not_reuse_name_match(
    db_session,
):
    first = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
        ),
    )

    second = create_player(
        db_session,
        PlayerCreate(
            full_name="John Smith",
        ),
    )

    assert first.id != second.id

    player_count = db_session.scalar(
        select(
            func.count(Player.id)
        )
    )

    assert player_count == 2


def test_create_players_creates_multiple_players(
    db_session,
):
    players = create_players(
        db_session,
        [
            PlayerCreate(
                full_name="Player One",
            ),
            PlayerCreate(
                full_name="Player Two",
            ),
            PlayerCreate(
                full_name="Player Three",
            ),
        ],
    )

    assert len(players) == 3

    assert [
        player.full_name
        for player in players
    ] == [
        "Player One",
        "Player Two",
        "Player Three",
    ]

    assert all(
        player.id is not None
        for player in players
    )


def test_create_players_allows_duplicate_names(
    db_session,
):
    players = create_players(
        db_session,
        [
            PlayerCreate(
                full_name="Same Name",
            ),
            PlayerCreate(
                full_name="Same Name",
            ),
        ],
    )

    assert len(players) == 2

    assert (
        players[0].id
        != players[1].id
    )

    assert (
        players[0].full_name
        == players[1].full_name
    )


def test_create_players_empty_list_does_nothing(
    db_session,
):
    players = create_players(
        db_session,
        [],
    )

    assert players == []

    count = db_session.scalar(
        select(
            func.count(Player.id)
        )
    )

    assert count == 0


def test_create_players_rolls_back_batch_on_failure(
    db_session,
    monkeypatch,
):
    original_commit = db_session.commit

    def failing_commit():
        raise RuntimeError(
            "Simulated batch failure"
        )

    monkeypatch.setattr(
        db_session,
        "commit",
        failing_commit,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated batch failure",
    ):
        create_players(
            db_session,
            [
                PlayerCreate(
                    full_name="Player One",
                ),
                PlayerCreate(
                    full_name="Player Two",
                ),
            ],
        )

    monkeypatch.setattr(
        db_session,
        "commit",
        original_commit,
    )

    db_session.expire_all()

    count = db_session.scalar(
        select(
            func.count(Player.id)
        )
    )

    assert count == 0