from datetime import date

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
from app.models.season import (
    Season,
    SeasonStatus,
)
from app.models.season_roster import (
    RosterStatus,
    SeasonRoster,
)
from app.models.team import Team
from app.schemas.external_game import (
    ExternalGameCreate,
    ExternalGameUpdate,
)
from app.schemas.external_game_player_stats import (
    ExternalGamePlayerStatsCreate,
)
from app.services.csv_exports import (
    build_season_csv,
)
from app.services.external_game import (
    create_external_game,
    update_external_game,
)
from app.services.external_game_player_stats import (
    create_external_game_player_stats,
)
from app.services.statistics import (
    calculate_player_season_summary,
    calculate_team_season_summary,
    get_player_completed_game_log,
    get_season_chart_data,
    get_season_comparison_data,
    get_season_game_series,
    get_season_player_leaderboards,
)


def _create_regular_completed_season(
    db_session,
):
    team = Team(
        name="Isolation JCP",
        abbreviation="JCP-I",
    )

    opponent = Team(
        name="Isolation Regular Opponent",
        abbreviation="REG-I",
    )

    player = Player(
        full_name="Isolation Player",
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
        name="Isolation Season",
        start_date=date(2026, 8, 1),
        end_date=date(2027, 3, 1),
        status=SeasonStatus.ACTIVE,
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    roster = SeasonRoster(
        season_id=season.id,
        player_id=player.id,
        jersey_number=12,
        position="G",
        grade_level="12",
        status=RosterStatus.ACTIVE,
    )

    db_session.add(roster)
    db_session.commit()
    db_session.refresh(roster)

    game = Game(
        season_id=season.id,
        opponent_team_id=opponent.id,
        game_date=date(2026, 8, 28),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=12,
        notes="Regular season isolation game",
    )

    db_session.add(game)
    db_session.commit()
    db_session.refresh(game)

    stats = PlayerGameStats(
        game_id=game.id,
        season_roster_id=roster.id,
        participation_status=(
            ParticipationStatus.PLAYED
        ),
        three_point_attempts=4,
        three_point_makes=2,
        two_point_attempts=6,
        two_point_makes=3,
        free_throw_attempts=4,
        free_throw_makes=3,
        turnovers=2,
        assists=4,
        offensive_rebounds=2,
        defensive_rebounds=3,
        steals=1,
        deflections=2,
        personal_fouls=2,
    )

    db_session.add(stats)
    db_session.commit()
    db_session.refresh(stats)

    return season, roster, player


def _regular_row_counts(
    db_session,
) -> tuple[int, int]:
    game_count = db_session.scalar(
        select(
            func.count(Game.id)
        )
    )

    stats_count = db_session.scalar(
        select(
            func.count(PlayerGameStats.id)
        )
    )

    assert game_count is not None
    assert stats_count is not None

    return game_count, stats_count


def _capture_season_outputs(
    db_session,
    season_id: int,
    season_roster_id: int,
):
    return {
        "player_summary": (
            calculate_player_season_summary(
                db_session,
                season_roster_id,
            )
        ),
        "player_game_log": (
            get_player_completed_game_log(
                db_session,
                season_roster_id,
            )
        ),
        "team_summary": (
            calculate_team_season_summary(
                db_session,
                season_id,
            )
        ),
        "leaderboards": (
            get_season_player_leaderboards(
                db_session,
                season_id,
            )
        ),
        "game_series": (
            get_season_game_series(
                db_session,
                season_id,
            )
        ),
        "chart_data": (
            get_season_chart_data(
                db_session,
                season_id,
            )
        ),
        "comparisons": (
            get_season_comparison_data(
                db_session,
                season_id,
            )
        ),
        "season_csv": (
            build_season_csv(
                db_session,
                season_id,
            )
        ),
    }


def test_external_game_is_completely_isolated_from_season(
    authenticated_client,
    db_session,
):
    (
        season,
        roster,
        player,
    ) = _create_regular_completed_season(
        db_session
    )

    before_outputs = _capture_season_outputs(
        db_session,
        season.id,
        roster.id,
    )

    before_regular_counts = (
        _regular_row_counts(
            db_session
        )
    )

    before_dashboard = (
        authenticated_client.get(
            (
                f"/app/seasons/"
                f"{season.id}/dashboard"
            )
        )
    )

    assert before_dashboard.status_code == 200

    before_profile = (
        authenticated_client.get(
            (
                f"/app/season-rosters/"
                f"{roster.id}/profile"
            )
        )
    )

    assert before_profile.status_code == 200

    external_opponent = Team(
        name="Isolation External Opponent",
        abbreviation="EXT-I",
    )

    db_session.add(external_opponent)
    db_session.commit()
    db_session.refresh(external_opponent)

    external_game = create_external_game(
        db_session,
        ExternalGameCreate(
            name="Extreme External Showcase",
            opponent_team_id=(
                external_opponent.id
            ),
            game_date=date(2026, 8, 30),
            venue_type=VenueType.NEUTRAL,
        ),
    )

    create_external_game_player_stats(
        db_session,
        ExternalGamePlayerStatsCreate(
            external_game_id=(
                external_game.id
            ),
            player_id=player.id,
            participation_status=(
                ParticipationStatus.PLAYED
            ),

            # Deliberately extreme statistics.
            three_point_attempts=100,
            three_point_makes=100,
            two_point_attempts=100,
            two_point_makes=100,
            free_throw_attempts=100,
            free_throw_makes=100,
            turnovers=99,
            assists=100,
            offensive_rebounds=100,
            defensive_rebounds=100,
            steals=100,
            deflections=100,
            personal_fouls=100,
        ),
    )

    completed_external_game = (
        update_external_game(
            db_session,
            external_game.id,
            ExternalGameUpdate(
                opponent_score=500,
                status=GameStatus.COMPLETED,
            ),
        )
    )

    assert (
        completed_external_game.status
        == GameStatus.COMPLETED
    )

    after_outputs = _capture_season_outputs(
        db_session,
        season.id,
        roster.id,
    )

    after_regular_counts = (
        _regular_row_counts(
            db_session
        )
    )

    after_dashboard = (
        authenticated_client.get(
            (
                f"/app/seasons/"
                f"{season.id}/dashboard"
            )
        )
    )

    assert after_dashboard.status_code == 200

    after_profile = (
        authenticated_client.get(
            (
                f"/app/season-rosters/"
                f"{roster.id}/profile"
            )
        )
    )

    assert after_profile.status_code == 200

    # Player season statistics must not change.
    assert (
        after_outputs["player_summary"]
        == before_outputs["player_summary"]
    )

    assert (
        after_outputs["player_game_log"]
        == before_outputs["player_game_log"]
    )

    # Team season statistics and record
    # must not change.
    assert (
        after_outputs["team_summary"]
        == before_outputs["team_summary"]
    )

    # Dashboard leaderboards must not change.
    assert (
        after_outputs["leaderboards"]
        == before_outputs["leaderboards"]
    )

    # Completed regular-game series must
    # not contain the External Game.
    assert (
        after_outputs["game_series"]
        == before_outputs["game_series"]
    )

    # Dashboard charts must remain unchanged.
    assert (
        after_outputs["chart_data"]
        == before_outputs["chart_data"]
    )

    # Win/loss and venue comparisons must
    # remain unchanged.
    assert (
        after_outputs["comparisons"]
        == before_outputs["comparisons"]
    )

    # Season CSV must be byte-for-byte unchanged.
    assert (
        after_outputs["season_csv"]
        == before_outputs["season_csv"]
    )

    # Existing rendered Season Dashboard and
    # Player Season Profile must remain unchanged.
    assert (
        after_dashboard.text
        == before_dashboard.text
    )

    assert (
        after_profile.text
        == before_profile.text
    )

    # Creating External Games must never create
    # regular Game or PlayerGameStats rows.
    assert (
        after_regular_counts
        == before_regular_counts
    )

    # Explicit baseline assertions make accidental
    # contamination easy to detect.
    player_summary = (
        after_outputs["player_summary"]
    )

    team_summary = (
        after_outputs["team_summary"]
    )

    assert player_summary["games_played"] == 1
    assert player_summary["points"] == 15
    assert player_summary["assists"] == 4

    assert team_summary["games_played"] == 1
    assert team_summary["wins"] == 1
    assert team_summary["losses"] == 0
    assert team_summary["points"] == 15
    assert team_summary["opponent_points"] == 12

    # External identifiers must never leak
    # into regular-season outputs.
    assert (
        "Extreme External Showcase"
        not in after_outputs["season_csv"]
    )

    assert (
        "Isolation External Opponent"
        not in after_outputs["season_csv"]
    )

    assert (
        "Isolation External Opponent"
        not in after_dashboard.text
    )

    assert (
        "Isolation External Opponent"
        not in after_profile.text
    )