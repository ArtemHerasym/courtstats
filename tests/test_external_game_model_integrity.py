from datetime import date

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.external_game import ExternalGame
from app.models.external_game_player_stats import (
    ExternalGamePlayerStats,
)
from app.models.game import GameStatus, VenueType
from app.models.player import Player
from app.models.player_game_stats import (
    ParticipationStatus,
)
from app.models.team import Team


def _create_team(
    db_session,
    name: str = "Integrity Opponent",
) -> Team:
    team = Team(
        name=name,
        abbreviation="INT",
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)
    return team


def _create_player(
    db_session,
    name: str = "Integrity Player",
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
) -> ExternalGame:
    game = ExternalGame(
        name="Integrity External Game",
        opponent_team_id=opponent.id,
        game_date=date(2026, 9, 1),
        venue_type=VenueType.NEUTRAL,
        status=GameStatus.DRAFT,
    )

    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)

    return game


def test_valid_external_game(
    db_session,
):
    opponent = _create_team(db_session)

    game = _create_external_game(
        db_session,
        opponent,
    )

    assert game.id is not None
    assert game.opponent_team_id == opponent.id
    assert game.status == GameStatus.DRAFT


def test_external_game_rejects_invalid_opponent_fk(
    db_session,
):
    game = ExternalGame(
        name="Invalid FK Game",
        opponent_team_id=999999,
        game_date=date(2026, 9, 1),
        venue_type=VenueType.HOME,
        status=GameStatus.DRAFT,
    )

    db_session.add(game)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_external_game_rejects_blank_name_at_database(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Blank Name Opponent",
    )

    game = ExternalGame(
        name="   ",
        opponent_team_id=opponent.id,
        game_date=date(2026, 9, 1),
        venue_type=VenueType.HOME,
        status=GameStatus.DRAFT,
    )

    db_session.add(game)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_external_game_rejects_negative_opponent_score_at_database(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Negative Score Opponent",
    )

    game = ExternalGame(
        name="Negative Score Game",
        opponent_team_id=opponent.id,
        game_date=date(2026, 9, 1),
        venue_type=VenueType.HOME,
        opponent_score=-1,
        status=GameStatus.DRAFT,
    )

    db_session.add(game)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_valid_external_game_player_stats(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Valid Stats Opponent",
    )
    player = _create_player(
        db_session,
        "Valid Stats Player",
    )
    game = _create_external_game(
        db_session,
        opponent,
    )

    stats = ExternalGamePlayerStats(
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
        assists=4,
        turnovers=2,
    )

    db_session.add(stats)
    db_session.commit()
    db_session.refresh(stats)

    assert stats.id is not None
    assert stats.player_id == player.id


def test_external_stats_reject_invalid_external_game_fk(
    db_session,
):
    player = _create_player(
        db_session,
        "Bad Game FK Player",
    )

    stats = ExternalGamePlayerStats(
        external_game_id=999999,
        player_id=player.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
    )

    db_session.add(stats)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_external_stats_reject_invalid_player_fk(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Bad Player FK Opponent",
    )
    game = _create_external_game(
        db_session,
        opponent,
    )

    stats = ExternalGamePlayerStats(
        external_game_id=game.id,
        player_id=999999,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
    )

    db_session.add(stats)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_external_stats_reject_duplicate_game_player(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Duplicate Integrity Opponent",
    )
    player = _create_player(
        db_session,
        "Duplicate Integrity Player",
    )
    game = _create_external_game(
        db_session,
        opponent,
    )

    first = ExternalGamePlayerStats(
        external_game_id=game.id,
        player_id=player.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
    )

    db_session.add(first)
    db_session.commit()

    duplicate = ExternalGamePlayerStats(
        external_game_id=game.id,
        player_id=player.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
    )

    db_session.add(duplicate)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_external_stats_reject_negative_raw_stat(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Negative Stat Opponent",
    )
    player = _create_player(
        db_session,
        "Negative Stat Player",
    )
    game = _create_external_game(
        db_session,
        opponent,
    )

    stats = ExternalGamePlayerStats(
        external_game_id=game.id,
        player_id=player.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        assists=-1,
    )

    db_session.add(stats)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


@pytest.mark.parametrize(
    (
        "attempt_field",
        "make_field",
    ),
    [
        (
            "three_point_attempts",
            "three_point_makes",
        ),
        (
            "two_point_attempts",
            "two_point_makes",
        ),
        (
            "free_throw_attempts",
            "free_throw_makes",
        ),
    ],
)
def test_external_stats_reject_makes_above_attempts(
    db_session,
    attempt_field,
    make_field,
):
    opponent = _create_team(
        db_session,
        (
            "Makes Attempts Opponent "
            f"{attempt_field}"
        ),
    )
    player = _create_player(
        db_session,
        (
            "Makes Attempts Player "
            f"{attempt_field}"
        ),
    )
    game = _create_external_game(
        db_session,
        opponent,
    )

    values = {
        attempt_field: 1,
        make_field: 2,
    }

    stats = ExternalGamePlayerStats(
        external_game_id=game.id,
        player_id=player.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        **values,
    )

    db_session.add(stats)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_external_stats_reject_nonzero_dnp(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Invalid DNP Opponent",
    )
    player = _create_player(
        db_session,
        "Invalid DNP Player",
    )
    game = _create_external_game(
        db_session,
        opponent,
    )

    stats = ExternalGamePlayerStats(
        external_game_id=game.id,
        player_id=player.id,
        participation_status=(
            ParticipationStatus.DID_NOT_PLAY
        ),
        assists=1,
    )

    db_session.add(stats)

    with pytest.raises(IntegrityError):
        db_session.commit()

    db_session.rollback()


def test_external_stats_accept_zero_stat_dnp(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Zero DNP Opponent",
    )
    player = _create_player(
        db_session,
        "Zero DNP Player",
    )
    game = _create_external_game(
        db_session,
        opponent,
    )

    stats = ExternalGamePlayerStats(
        external_game_id=game.id,
        player_id=player.id,
        participation_status=(
            ParticipationStatus.DID_NOT_PLAY
        ),
    )

    db_session.add(stats)
    db_session.commit()
    db_session.refresh(stats)

    assert stats.id is not None
    assert stats.assists == 0


def test_external_stats_accept_zero_stat_played(
    db_session,
):
    opponent = _create_team(
        db_session,
        "Zero Played Opponent",
    )
    player = _create_player(
        db_session,
        "Zero Played Player",
    )
    game = _create_external_game(
        db_session,
        opponent,
    )

    stats = ExternalGamePlayerStats(
        external_game_id=game.id,
        player_id=player.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
    )

    db_session.add(stats)
    db_session.commit()
    db_session.refresh(stats)

    assert stats.id is not None
    assert stats.assists == 0