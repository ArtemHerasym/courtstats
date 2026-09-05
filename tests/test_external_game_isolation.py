from datetime import date

from sqlalchemy import func, select

from app.models.game import (
    Game,
    GameStatus,
    VenueType,
)
from app.models.player_game_stats import (
    ParticipationStatus,
    PlayerGameStats,
)
from app.schemas.external_game import (
    ExternalGameCreate,
)
from app.schemas.external_game_player_stats import (
    ExternalGamePlayerStatsCreate,
)
from app.schemas.game import GameCreate
from app.schemas.player import PlayerCreate
from app.schemas.player_game_stats import (
    PlayerGameStatsCreate,
)
from app.schemas.season import SeasonCreate
from app.schemas.season_roster import (
    SeasonRosterCreate,
)
from app.schemas.team import TeamCreate
from app.services.csv_exports import (
    build_player_season_csv,
    build_season_csv,
)
from app.services.external_game import (
    create_external_game,
)
from app.services.external_game_workflow import (
    finalize_external_game_with_stats,
    sync_external_game_players,
)
from app.services.game import create_game
from app.services.player import create_player
from app.services.player_game_stats import (
    finalize_game_with_stats,
)
from app.services.season import create_season
from app.services.season_roster import (
    create_season_roster,
)
from app.services.statistics import (
    calculate_player_season_summary,
    calculate_team_season_summary,
    get_player_completed_game_log,
    get_season_game_series,
    get_season_player_leaderboards,
)
from app.services.team import create_team


def create_regular_season_data(
    db_session,
):
    school_team = create_team(
        db_session,
        TeamCreate(
            name="Isolation School",
            abbreviation="ISO",
        ),
    )

    regular_opponent = create_team(
        db_session,
        TeamCreate(
            name="Regular Opponent",
            abbreviation="REG",
        ),
    )

    season = create_season(
        db_session,
        SeasonCreate(
            team_id=school_team.id,
            name="Isolation Season",
            start_date=date(2026, 8, 1),
            end_date=date(2027, 5, 31),
        ),
    )

    player = create_player(
        db_session,
        PlayerCreate(
            full_name="Isolation Player",
        ),
    )

    roster = create_season_roster(
        db_session,
        SeasonRosterCreate(
            season_id=season.id,
            player_id=player.id,
            jersey_number=7,
            position="G",
            grade_level="12",
        ),
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=(
                regular_opponent.id
            ),
            game_date=date(2026, 9, 1),
            venue_type=VenueType.HOME,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=None,
        ),
    )

    regular_stats = PlayerGameStatsCreate(
        game_id=game.id,
        season_roster_id=roster.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        three_point_attempts=4,
        three_point_makes=2,
        two_point_attempts=6,
        two_point_makes=3,
        free_throw_attempts=2,
        free_throw_makes=2,
        turnovers=2,
        assists=5,
        offensive_rebounds=1,
        defensive_rebounds=4,
        steals=2,
        deflections=3,
        personal_fouls=2,
    )

    finalize_game_with_stats(
        db_session,
        game.id,
        [regular_stats],
        opponent_score=50,
    )

    return season, roster, player


def add_large_external_game(
    db_session,
    player,
):
    opponent = create_team(
        db_session,
        TeamCreate(
            name="External Isolation Opponent",
            abbreviation="EXT",
        ),
    )

    external_game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Huge External Game",
            opponent_team_id=opponent.id,
            game_date=date(2026, 9, 2),
            venue_type=VenueType.AWAY,
            status=GameStatus.DRAFT,
            opponent_score=None,
            notes=(
                "Must never affect season data."
            ),
        ),
    )

    sync_external_game_players(
        db_session,
        external_game.id,
        [player.id],
    )

    external_stats = (
        ExternalGamePlayerStatsCreate(
            external_game_id=(
                external_game.id
            ),
            player_id=player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),
            three_point_attempts=10,
            three_point_makes=10,
            two_point_attempts=10,
            two_point_makes=10,
            free_throw_attempts=10,
            free_throw_makes=10,
            turnovers=20,
            assists=99,
            offensive_rebounds=30,
            defensive_rebounds=40,
            steals=25,
            deflections=50,
            personal_fouls=5,
        )
    )

    finalize_external_game_with_stats(
        db_session,
        external_game.id,
        [external_stats],
        opponent_score=1,
    )

    return external_game


def test_external_game_does_not_change_player_season_analytics(
    db_session,
):
    season, roster, player = (
        create_regular_season_data(
            db_session
        )
    )

    before_summary = (
        calculate_player_season_summary(
            db_session,
            roster.id,
        )
    )

    before_game_log = (
        get_player_completed_game_log(
            db_session,
            roster.id,
        )
    )

    add_large_external_game(
        db_session,
        player,
    )

    after_summary = (
        calculate_player_season_summary(
            db_session,
            roster.id,
        )
    )

    after_game_log = (
        get_player_completed_game_log(
            db_session,
            roster.id,
        )
    )

    assert after_summary == before_summary
    assert after_game_log == before_game_log

    assert after_summary["games_played"] == 1
    assert after_summary["assists"] == 5


def test_external_game_does_not_change_team_or_dashboard_data(
    db_session,
):
    season, roster, player = (
        create_regular_season_data(
            db_session
        )
    )

    before_team_summary = (
        calculate_team_season_summary(
            db_session,
            season.id,
        )
    )

    before_leaderboards = (
        get_season_player_leaderboards(
            db_session,
            season.id,
        )
    )

    before_game_series = (
        get_season_game_series(
            db_session,
            season.id,
        )
    )

    add_large_external_game(
        db_session,
        player,
    )

    after_team_summary = (
        calculate_team_season_summary(
            db_session,
            season.id,
        )
    )

    after_leaderboards = (
        get_season_player_leaderboards(
            db_session,
            season.id,
        )
    )

    after_game_series = (
        get_season_game_series(
            db_session,
            season.id,
        )
    )

    assert (
        after_team_summary
        == before_team_summary
    )

    assert (
        after_leaderboards
        == before_leaderboards
    )

    assert (
        after_game_series
        == before_game_series
    )


def test_external_game_does_not_change_season_exports(
    db_session,
):
    season, roster, player = (
        create_regular_season_data(
            db_session
        )
    )

    before_season_csv = build_season_csv(
        db_session,
        season.id,
    )

    before_player_csv = (
        build_player_season_csv(
            db_session,
            roster.id,
        )
    )

    add_large_external_game(
        db_session,
        player,
    )

    after_season_csv = build_season_csv(
        db_session,
        season.id,
    )

    after_player_csv = (
        build_player_season_csv(
            db_session,
            roster.id,
        )
    )

    assert (
        after_season_csv
        == before_season_csv
    )

    assert (
        after_player_csv
        == before_player_csv
    )

    assert "Huge External Game" not in (
        after_season_csv
    )

    assert "Huge External Game" not in (
        after_player_csv
    )


def test_external_game_does_not_create_regular_game_or_stats_rows(
    db_session,
):
    season, roster, player = (
        create_regular_season_data(
            db_session
        )
    )

    regular_game_count_before = (
        db_session.scalar(
            select(
                func.count(Game.id)
            ).where(
                Game.season_id
                == season.id
            )
        )
    )

    regular_stats_count_before = (
        db_session.scalar(
            select(
                func.count(
                    PlayerGameStats.id
                )
            )
            .join(
                Game,
                PlayerGameStats.game_id
                == Game.id,
            )
            .where(
                Game.season_id
                == season.id
            )
        )
    )

    add_large_external_game(
        db_session,
        player,
    )

    regular_game_count_after = (
        db_session.scalar(
            select(
                func.count(Game.id)
            ).where(
                Game.season_id
                == season.id
            )
        )
    )

    regular_stats_count_after = (
        db_session.scalar(
            select(
                func.count(
                    PlayerGameStats.id
                )
            )
            .join(
                Game,
                PlayerGameStats.game_id
                == Game.id,
            )
            .where(
                Game.season_id
                == season.id
            )
        )
    )

    assert (
        regular_game_count_after
        == regular_game_count_before
        == 1
    )

    assert (
        regular_stats_count_after
        == regular_stats_count_before
        == 1
    )