from datetime import date

import pytest

import app.services.player_game_stats as player_game_stats_service
from app.models.game import Game, GameStatus, VenueType
from app.models.player import Player
from app.models.player_game_stats import (
    ParticipationStatus,
    PlayerGameStats,
)
from app.models.season import Season
from app.models.season_roster import RosterStatus, SeasonRoster
from app.models.team import Team
from app.schemas.player_game_stats import (
    PlayerGameStatsCreate,
    PlayerGameStatsUpdate,
)
from app.services.game import GameNotFoundError
from app.services.player_game_stats import (
    PlayerGameStatsConflictError,
    PlayerGameStatsNotFoundError,
    PlayerGameStatsSeasonMismatchError,
    create_player_game_stats,
    get_player_game_stats,
    list_player_game_stats,
    update_player_game_stats,
)
from app.services.season_roster import SeasonRosterNotFoundError


def _create_dependencies(db_session):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    player = Player(
        full_name="John Smith",
    )

    db_session.add_all([
        season_team,
        opponent_team,
        player,
    ])
    db_session.commit()

    db_session.refresh(season_team)
    db_session.refresh(opponent_team)
    db_session.refresh(player)

    season = Season(
        team_id=season_team.id,
        name="2026-27",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    game = Game(
        season_id=season.id,
        opponent_team_id=opponent_team.id,
        game_date=date.today(),
        venue_type=VenueType.HOME,
        status=GameStatus.DRAFT,
    )

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        status=RosterStatus.ACTIVE,
    )

    db_session.add_all([
        game,
        roster,
    ])
    db_session.commit()

    db_session.refresh(game)
    db_session.refresh(roster)

    return season_team, season, game, roster


def _create_second_roster(
    db_session,
    season,
):
    player = Player(
        full_name="Second Player",
    )

    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        status=RosterStatus.ACTIVE,
    )

    db_session.add(roster)
    db_session.commit()
    db_session.refresh(roster)

    return roster


def _create_other_season_roster(
    db_session,
    season_team,
):
    player = Player(
        full_name="Other Season Player",
    )

    season = Season(
        team_id=season_team.id,
        name="2025-26",
    )

    db_session.add_all([
        player,
        season,
    ])
    db_session.commit()

    db_session.refresh(player)
    db_session.refresh(season)

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        status=RosterStatus.ACTIVE,
    )

    db_session.add(roster)
    db_session.commit()
    db_session.refresh(roster)

    return roster


def test_create_player_game_stats(db_session):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
            three_point_attempts=5,
            three_point_makes=2,
            assists=6,
            steals=2,
        ),
    )

    assert stats.id is not None
    assert stats.game_id == game.id
    assert stats.season_roster_id == roster.id
    assert stats.participation_status == ParticipationStatus.PLAYED
    assert stats.three_point_attempts == 5
    assert stats.three_point_makes == 2
    assert stats.assists == 6
    assert stats.steals == 2
    assert stats.created_at is not None
    assert stats.updated_at is not None


def test_create_player_game_stats_persists_all_raw_values(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    created = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
            three_point_attempts=6,
            three_point_makes=3,
            two_point_attempts=10,
            two_point_makes=5,
            free_throw_attempts=4,
            free_throw_makes=3,
            turnovers=2,
            assists=7,
            offensive_rebounds=2,
            defensive_rebounds=6,
            steals=3,
            deflections=4,
            personal_fouls=2,
        ),
    )

    stats_id = created.id

    db_session.expire_all()

    persisted = db_session.get(
        PlayerGameStats,
        stats_id,
    )

    assert persisted is not None
    assert persisted.three_point_attempts == 6
    assert persisted.three_point_makes == 3
    assert persisted.two_point_attempts == 10
    assert persisted.two_point_makes == 5
    assert persisted.free_throw_attempts == 4
    assert persisted.free_throw_makes == 3
    assert persisted.turnovers == 2
    assert persisted.assists == 7
    assert persisted.offensive_rebounds == 2
    assert persisted.defensive_rebounds == 6
    assert persisted.steals == 3
    assert persisted.deflections == 4
    assert persisted.personal_fouls == 2


def test_create_valid_dnp_player_game_stats(db_session):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.DID_NOT_PLAY,
        ),
    )

    assert stats.participation_status == ParticipationStatus.DID_NOT_PLAY
    assert stats.three_point_attempts == 0
    assert stats.three_point_makes == 0
    assert stats.assists == 0
    assert stats.steals == 0
    assert stats.personal_fouls == 0


def test_create_rejects_missing_game(db_session):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    with pytest.raises(GameNotFoundError):
        create_player_game_stats(
            db_session,
            PlayerGameStatsCreate(
                game_id=999999,
                season_roster_id=roster.id,
                participation_status=ParticipationStatus.PLAYED,
            ),
        )


def test_create_rejects_missing_season_roster(db_session):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    with pytest.raises(SeasonRosterNotFoundError):
        create_player_game_stats(
            db_session,
            PlayerGameStatsCreate(
                game_id=game.id,
                season_roster_id=999999,
                participation_status=ParticipationStatus.PLAYED,
            ),
        )


def test_create_rejects_roster_from_wrong_season(db_session):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    other_roster = _create_other_season_roster(
        db_session,
        season_team,
    )

    with pytest.raises(
        PlayerGameStatsSeasonMismatchError,
        match="Game and season roster must belong to the same season.",
    ):
        create_player_game_stats(
            db_session,
            PlayerGameStatsCreate(
                game_id=game.id,
                season_roster_id=other_roster.id,
                participation_status=ParticipationStatus.PLAYED,
            ),
        )


def test_create_rejects_duplicate_game_roster_pair(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
        ),
    )

    with pytest.raises(
        PlayerGameStatsConflictError,
        match=(
            "Player game stats already exist for this game "
            "and roster entry."
        ),
    ):
        create_player_game_stats(
            db_session,
            PlayerGameStatsCreate(
                game_id=game.id,
                season_roster_id=roster.id,
                participation_status=ParticipationStatus.PLAYED,
            ),
        )


def test_get_player_game_stats_returns_existing_record(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    created = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
            assists=4,
        ),
    )

    stats = get_player_game_stats(
        db_session,
        created.id,
    )

    assert stats.id == created.id
    assert stats.game_id == game.id
    assert stats.season_roster_id == roster.id
    assert stats.assists == 4


def test_get_player_game_stats_raises_not_found(
    db_session,
):
    with pytest.raises(
        PlayerGameStatsNotFoundError,
        match="Player game stats with ID 999999 were not found.",
    ):
        get_player_game_stats(
            db_session,
            999999,
        )


def test_list_player_game_stats_returns_entries_in_id_order(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    second_roster = _create_second_roster(
        db_session,
        season,
    )

    first_stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
        ),
    )

    second_stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=second_roster.id,
            participation_status=ParticipationStatus.PLAYED,
        ),
    )

    stats_entries = list_player_game_stats(
        db_session
    )

    assert [stats.id for stats in stats_entries] == [
        first_stats.id,
        second_stats.id,
    ]


def test_update_player_game_stats_partial_update_preserves_omitted_fields(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
            three_point_attempts=5,
            three_point_makes=2,
            assists=3,
            steals=1,
        ),
    )

    updated = update_player_game_stats(
        db_session,
        stats.id,
        PlayerGameStatsUpdate(
            assists=7,
        ),
    )

    assert updated.id == stats.id
    assert updated.game_id == game.id
    assert updated.season_roster_id == roster.id
    assert updated.participation_status == ParticipationStatus.PLAYED
    assert updated.three_point_attempts == 5
    assert updated.three_point_makes == 2
    assert updated.assists == 7
    assert updated.steals == 1


def test_update_player_game_stats_persists_changes(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
            assists=2,
            steals=1,
        ),
    )

    stats_id = stats.id

    update_player_game_stats(
        db_session,
        stats_id,
        PlayerGameStatsUpdate(
            assists=8,
            steals=4,
        ),
    )

    db_session.expire_all()

    persisted = db_session.get(
        PlayerGameStats,
        stats_id,
    )

    assert persisted is not None
    assert persisted.assists == 8
    assert persisted.steals == 4


def test_update_rejects_final_makes_above_attempts(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
            three_point_attempts=5,
            three_point_makes=2,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Three-point makes cannot exceed three-point attempts",
    ):
        update_player_game_stats(
            db_session,
            stats.id,
            PlayerGameStatsUpdate(
                three_point_makes=6,
            ),
        )


def test_update_rejects_nonzero_played_row_changed_directly_to_dnp(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
            assists=5,
        ),
    )

    with pytest.raises(
        ValueError,
        match="DID_NOT_PLAY requires all statistics to be zero",
    ):
        update_player_game_stats(
            db_session,
            stats.id,
            PlayerGameStatsUpdate(
                participation_status=ParticipationStatus.DID_NOT_PLAY,
            ),
        )


def test_update_allows_change_to_dnp_when_final_stats_are_zero(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
        ),
    )

    updated = update_player_game_stats(
        db_session,
        stats.id,
        PlayerGameStatsUpdate(
            participation_status=ParticipationStatus.DID_NOT_PLAY,
        ),
    )

    assert updated.participation_status == ParticipationStatus.DID_NOT_PLAY
    assert updated.assists == 0
    assert updated.three_point_attempts == 0
    assert updated.personal_fouls == 0


def test_update_rejects_duplicate_game_roster_pair(
    db_session,
):
    season_team, season, game, first_roster = _create_dependencies(
        db_session
    )

    second_roster = _create_second_roster(
        db_session,
        season,
    )

    create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=first_roster.id,
            participation_status=ParticipationStatus.PLAYED,
        ),
    )

    second_stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=second_roster.id,
            participation_status=ParticipationStatus.PLAYED,
        ),
    )

    with pytest.raises(PlayerGameStatsConflictError):
        update_player_game_stats(
            db_session,
            second_stats.id,
            PlayerGameStatsUpdate(
                season_roster_id=first_roster.id,
            ),
        )


def test_update_rejects_none_for_required_reference(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Player game stats game_id cannot be None",
    ):
        update_player_game_stats(
            db_session,
            stats.id,
            PlayerGameStatsUpdate(
                game_id=None,
            ),
        )


def test_update_rejects_none_for_raw_stat(
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Player game stats assists cannot be None",
    ):
        update_player_game_stats(
            db_session,
            stats.id,
            PlayerGameStatsUpdate(
                assists=None,
            ),
        )


def test_database_failure_rolls_back_and_session_remains_usable(
    db_session,
    monkeypatch,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    first_stats = create_player_game_stats(
        db_session,
        PlayerGameStatsCreate(
            game_id=game.id,
            season_roster_id=roster.id,
            participation_status=ParticipationStatus.PLAYED,
        ),
    )

    first_stats_id = first_stats.id

    monkeypatch.setattr(
        player_game_stats_service,
        "_ensure_stats_entry_available",
        lambda *args, **kwargs: None,
    )

    with pytest.raises(PlayerGameStatsConflictError):
        create_player_game_stats(
            db_session,
            PlayerGameStatsCreate(
                game_id=game.id,
                season_roster_id=roster.id,
                participation_status=ParticipationStatus.PLAYED,
            ),
        )

    existing = get_player_game_stats(
        db_session,
        first_stats_id,
    )

    assert existing.id == first_stats_id