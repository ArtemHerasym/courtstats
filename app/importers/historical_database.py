from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.player import Player
from app.models.season import Season
from app.models.team import Team
from app.schemas.player import PlayerCreate
from app.services.player import create_player
from app.importers.historical_workbook import (
    HistoricalWorkbookData,
    validate_historical_workbook,
)
from app.models.game import GameStatus
from app.models.player_game_stats import ParticipationStatus
from app.models.season import Season, SeasonStatus
from app.models.season_roster import RosterStatus

from app.schemas.game import GameCreate, GameUpdate
from app.schemas.player_game_stats import PlayerGameStatsCreate
from app.schemas.season import SeasonCreate, SeasonUpdate
from app.schemas.season_roster import SeasonRosterCreate

from app.services.game import create_game, update_game
from app.services.player_game_stats import create_player_game_stats
from app.services.season import create_season, update_season
from app.services.season_roster import create_season_roster


HISTORICAL_TEAM_NAME = "Jordan Christian Preparatory"
HISTORICAL_TEAM_ABBREVIATION = "JCP"
HISTORICAL_SEASON_NAME = "2025-26"


class HistoricalImportAlreadyExistsError(Exception):
    pass


def get_or_create_team(
    db: Session,
    name: str,
    abbreviation: str | None = None,
) -> Team:
    normalized_name = name.strip()

    existing_team = db.scalar(
        select(Team).where(
            func.lower(Team.name)
            == normalized_name.lower()
        )
    )

    if existing_team is not None:
        return existing_team

    team = Team(
        name=normalized_name,
        abbreviation=abbreviation,
    )

    db.add(team)
    db.commit()
    db.refresh(team)

    return team


def get_or_create_player(
    db: Session,
    full_name: str,
) -> Player:
    normalized_name = full_name.strip()

    matches = list(
        db.scalars(
            select(Player).where(
                func.lower(Player.full_name)
                == normalized_name.lower()
            )
        ).all()
    )

    if len(matches) > 1:
        raise ValueError(
            "Multiple existing players match historical player "
            f"name: {normalized_name}"
        )

    if matches:
        return matches[0]

    return create_player(
        db,
        PlayerCreate(
            full_name=normalized_name,
            display_name=None,
        ),
    )


def ensure_historical_season_not_imported(
    db: Session,
    team_id: int,
) -> None:
    existing_season = db.scalar(
        select(Season).where(
            Season.team_id == team_id,
            Season.name == HISTORICAL_SEASON_NAME,
        )
    )

    if existing_season is not None:
        raise HistoricalImportAlreadyExistsError(
            f"Historical season {HISTORICAL_SEASON_NAME} "
            f"already exists for {HISTORICAL_TEAM_NAME}. "
            "Import aborted."
        )

def import_historical_data(
    db: Session,
    data: HistoricalWorkbookData,
) -> Season:
    # Never write anything before the complete workbook
    # has passed preflight validation.
    validate_historical_workbook(data)

    team = get_or_create_team(
        db,
        HISTORICAL_TEAM_NAME,
        HISTORICAL_TEAM_ABBREVIATION,
    )

    ensure_historical_season_not_imported(
        db,
        team.id,
    )

    season = create_season(
        db,
        SeasonCreate(
            team_id=team.id,
            name=HISTORICAL_SEASON_NAME,
            start_date=min(
                game.game_date
                for game in data.games
            ),
            end_date=max(
                game.game_date
                for game in data.games
            ),
        ),
    )

    roster_by_player_name = {}

    for roster_row in data.roster:
        player = get_or_create_player(
            db,
            roster_row.full_name,
        )

        roster_entry = create_season_roster(
            db,
            SeasonRosterCreate(
                season_id=season.id,
                player_id=player.id,
                jersey_number=roster_row.jersey_number,
                position=roster_row.position,
                grade_level=roster_row.grade_level,
                status=RosterStatus.ACTIVE,
            ),
        )

        roster_by_player_name[
            roster_row.full_name.casefold()
        ] = roster_entry

    games_by_workbook_id = {}

    for game_row in data.games:
        opponent = get_or_create_team(
            db,
            game_row.opponent_name,
        )

        game = create_game(
            db,
            GameCreate(
                season_id=season.id,
                opponent_team_id=opponent.id,
                game_date=game_row.game_date,
                venue_type=game_row.venue_type,
                status=GameStatus.DRAFT,
                opponent_score=game_row.opponent_score,
                notes=None,
            ),
        )

        games_by_workbook_id[
            game_row.workbook_game_id
        ] = game

    for stats_row in data.player_stats:
        game = games_by_workbook_id[
            stats_row.workbook_game_id
        ]

        roster_entry = roster_by_player_name[
            stats_row.player_name.casefold()
        ]

        create_player_game_stats(
            db,
            PlayerGameStatsCreate(
                game_id=game.id,
                season_roster_id=roster_entry.id,
                participation_status=ParticipationStatus.PLAYED,
                three_point_attempts=stats_row.three_point_attempts,
                three_point_makes=stats_row.three_point_makes,
                two_point_attempts=stats_row.two_point_attempts,
                two_point_makes=stats_row.two_point_makes,
                free_throw_attempts=stats_row.free_throw_attempts,
                free_throw_makes=stats_row.free_throw_makes,
                turnovers=stats_row.turnovers,
                assists=stats_row.assists,
                offensive_rebounds=stats_row.offensive_rebounds,
                defensive_rebounds=stats_row.defensive_rebounds,
                steals=stats_row.steals,
                deflections=stats_row.deflections,
                personal_fouls=stats_row.personal_fouls,
            ),
        )

    # Only after the raw stats exist do we complete the games.
    for game in games_by_workbook_id.values():
        update_game(
            db,
            game.id,
            GameUpdate(
                status=GameStatus.COMPLETED,
            ),
        )

    season = update_season(
        db,
        season.id,
        SeasonUpdate(
            status=SeasonStatus.COMPLETED,
        ),
    )

    return season