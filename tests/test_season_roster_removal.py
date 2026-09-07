from datetime import date

import pytest
from sqlalchemy import func, select

from app.models.game import (
    Game,
    GameStatus,
    VenueType,
)
from app.models.player import Player
from app.models.player_game_stats import (
    ParticipationStatus,
    PlayerGameStats,
)
from app.models.season import Season
from app.models.season_roster import (
    SeasonRoster,
)
from app.models.team import Team
from app.services.season_roster import (
    SeasonRosterRemovalBlockedError,
    remove_season_roster,
)


def _create_context(
    db_session,
):
    team = Team(
        name="Roster Removal Team",
    )

    opponent = Team(
        name="Roster Removal Opponent",
    )

    player = Player(
        full_name="Roster Removal Player",
    )

    db_session.add_all(
        [
            team,
            opponent,
            player,
        ]
    )
    db_session.commit()

    db_session.refresh(team)
    db_session.refresh(opponent)
    db_session.refresh(player)

    season = Season(
        team_id=team.id,
        name="2027-2028",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
    )

    db_session.add(roster)
    db_session.commit()
    db_session.refresh(roster)

    return (
        season,
        roster,
        player,
        opponent,
    )


def _create_game(
    db_session,
    season: Season,
    opponent: Team,
    *,
    status: GameStatus,
) -> Game:
    game = Game(
        season_id=season.id,
        opponent_team_id=opponent.id,
        game_date=date(
            2026,
            9,
            1,
        ),
        venue_type=VenueType.HOME,
        status=status,
        opponent_score=(
            0
            if status
            == GameStatus.COMPLETED
            else None
        ),
    )

    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)

    return game


def _create_stats(
    db_session,
    game: Game,
    roster: SeasonRoster,
    *,
    participation_status: ParticipationStatus,
    assists: int = 0,
) -> PlayerGameStats:
    stats = PlayerGameStats(
        game_id=game.id,
        season_roster_id=roster.id,
        participation_status=(
            participation_status
        ),
        assists=assists,
    )

    db_session.add(stats)
    db_session.commit()
    db_session.refresh(stats)

    return stats


def test_remove_roster_with_no_stats_succeeds(
    db_session,
):
    (
        _,
        roster,
        player,
        _,
    ) = _create_context(
        db_session
    )

    roster_id = roster.id
    player_id = player.id

    remove_season_roster(
        db_session,
        roster_id,
    )

    assert (
        db_session.get(
            SeasonRoster,
            roster_id,
        )
        is None
    )

    assert (
        db_session.get(
            Player,
            player_id,
        )
        is not None
    )


def test_remove_roster_with_zero_stat_draft_played_cleans_stats(
    db_session,
):
    (
        season,
        roster,
        player,
        opponent,
    ) = _create_context(
        db_session
    )

    game = _create_game(
        db_session,
        season,
        opponent,
        status=GameStatus.DRAFT,
    )

    stats = _create_stats(
        db_session,
        game,
        roster,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
    )

    roster_id = roster.id
    stats_id = stats.id
    player_id = player.id

    remove_season_roster(
        db_session,
        roster_id,
    )

    assert (
        db_session.get(
            PlayerGameStats,
            stats_id,
        )
        is None
    )

    assert (
        db_session.get(
            SeasonRoster,
            roster_id,
        )
        is None
    )

    assert (
        db_session.get(
            Player,
            player_id,
        )
        is not None
    )


def test_remove_roster_with_draft_dnp_succeeds(
    db_session,
):
    (
        season,
        roster,
        _,
        opponent,
    ) = _create_context(
        db_session
    )

    game = _create_game(
        db_session,
        season,
        opponent,
        status=GameStatus.DRAFT,
    )

    stats = _create_stats(
        db_session,
        game,
        roster,
        participation_status=(
            ParticipationStatus.DID_NOT_PLAY
        ),
    )

    roster_id = roster.id
    stats_id = stats.id

    remove_season_roster(
        db_session,
        roster_id,
    )

    assert (
        db_session.get(
            PlayerGameStats,
            stats_id,
        )
        is None
    )

    assert (
        db_session.get(
            SeasonRoster,
            roster_id,
        )
        is None
    )


def test_remove_roster_with_meaningful_draft_stats_is_blocked(
    db_session,
):
    (
        season,
        roster,
        _,
        opponent,
    ) = _create_context(
        db_session
    )

    game = _create_game(
        db_session,
        season,
        opponent,
        status=GameStatus.DRAFT,
    )

    stats = _create_stats(
        db_session,
        game,
        roster,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        assists=1,
    )

    with pytest.raises(
        SeasonRosterRemovalBlockedError,
        match="statistical history",
    ):
        remove_season_roster(
            db_session,
            roster.id,
        )

    assert (
        db_session.get(
            SeasonRoster,
            roster.id,
        )
        is not None
    )

    assert (
        db_session.get(
            PlayerGameStats,
            stats.id,
        )
        is not None
    )


def test_remove_roster_with_completed_played_history_is_blocked(
    db_session,
):
    (
        season,
        roster,
        _,
        opponent,
    ) = _create_context(
        db_session
    )

    game = _create_game(
        db_session,
        season,
        opponent,
        status=GameStatus.COMPLETED,
    )

    stats = _create_stats(
        db_session,
        game,
        roster,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        assists=4,
    )

    with pytest.raises(
        SeasonRosterRemovalBlockedError,
        match="completed-game history",
    ):
        remove_season_roster(
            db_session,
            roster.id,
        )

    assert (
        db_session.get(
            SeasonRoster,
            roster.id,
        )
        is not None
    )

    assert (
        db_session.get(
            PlayerGameStats,
            stats.id,
        )
        is not None
    )


def test_remove_roster_with_completed_dnp_history_is_blocked(
    db_session,
):
    (
        season,
        roster,
        _,
        opponent,
    ) = _create_context(
        db_session
    )

    game = _create_game(
        db_session,
        season,
        opponent,
        status=GameStatus.COMPLETED,
    )

    stats = _create_stats(
        db_session,
        game,
        roster,
        participation_status=(
            ParticipationStatus.DID_NOT_PLAY
        ),
    )

    with pytest.raises(
        SeasonRosterRemovalBlockedError,
        match="completed-game history",
    ):
        remove_season_roster(
            db_session,
            roster.id,
        )

    assert (
        db_session.get(
            SeasonRoster,
            roster.id,
        )
        is not None
    )

    assert (
        db_session.get(
            PlayerGameStats,
            stats.id,
        )
        is not None
    )


def test_successful_roster_removal_never_deletes_global_player(
    db_session,
):
    (
        _,
        roster,
        player,
        _,
    ) = _create_context(
        db_session
    )

    player_id = player.id

    remove_season_roster(
        db_session,
        roster.id,
    )

    remaining_player = db_session.get(
        Player,
        player_id,
    )

    assert remaining_player is not None

    player_count = db_session.scalar(
        select(
            func.count(Player.id)
        )
    )

    assert player_count == 1


def test_blocked_removal_leaves_all_data_unchanged(
    db_session,
):
    (
        season,
        roster,
        player,
        opponent,
    ) = _create_context(
        db_session
    )

    game = _create_game(
        db_session,
        season,
        opponent,
        status=GameStatus.DRAFT,
    )

    stats = _create_stats(
        db_session,
        game,
        roster,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        assists=8,
    )

    with pytest.raises(
        SeasonRosterRemovalBlockedError
    ):
        remove_season_roster(
            db_session,
            roster.id,
        )

    remaining_roster = db_session.get(
        SeasonRoster,
        roster.id,
    )

    remaining_stats = db_session.get(
        PlayerGameStats,
        stats.id,
    )

    remaining_player = db_session.get(
        Player,
        player.id,
    )

    assert remaining_roster is not None
    assert remaining_stats is not None
    assert remaining_stats.assists == 8
    assert remaining_player is not None


def test_remove_roster_rolls_back_if_commit_fails(
    db_session,
    monkeypatch,
):
    (
        season,
        roster,
        player,
        opponent,
    ) = _create_context(
        db_session
    )

    game = _create_game(
        db_session,
        season,
        opponent,
        status=GameStatus.DRAFT,
    )

    stats = _create_stats(
        db_session,
        game,
        roster,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
    )

    roster_id = roster.id
    stats_id = stats.id
    player_id = player.id

    original_commit = db_session.commit

    def failing_commit():
        raise RuntimeError(
            "Simulated removal failure"
        )

    monkeypatch.setattr(
        db_session,
        "commit",
        failing_commit,
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated removal failure",
    ):
        remove_season_roster(
            db_session,
            roster_id,
        )

    monkeypatch.setattr(
        db_session,
        "commit",
        original_commit,
    )

    db_session.expire_all()

    assert (
        db_session.get(
            SeasonRoster,
            roster_id,
        )
        is not None
    )

    assert (
        db_session.get(
            PlayerGameStats,
            stats_id,
        )
        is not None
    )

    assert (
        db_session.get(
            Player,
            player_id,
        )
        is not None
    )