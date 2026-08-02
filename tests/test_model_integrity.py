import pytest
from datetime import date
from sqlalchemy.exc import DataError, IntegrityError

from app.models.game import Game, GameStatus, VenueType
from app.models.player import Player
from app.models.player_game_stats import PlayerGameStats, ParticipationStatus
from app.models.season import Season
from app.models.season_roster import SeasonRoster
from app.models.team import Team
from app.models.season import Season, SeasonStatus
from app.models.season_roster import SeasonRoster, RosterStatus


def test_all_six_models_can_be_persisted(db_session):
    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    player = Player(
        full_name="Test Player",
        display_name="T. Player",
    )

    db_session.add_all([team, player])
    db_session.flush()

    assert team.id is not None
    assert player.id is not None

    season = Season(
        team=team,
        name="2026-27",
        start_date=date(2026, 10, 1),
        end_date=date(2027, 3, 31),
    )

    season_roster = SeasonRoster(
        season=season,
        player=player,
        jersey_number=10,
        position="G",
        grade_level="12",
    )

    db_session.add_all([season, season_roster])
    db_session.flush()

    assert season.id is not None
    assert season_roster.id is not None

    opponent = Team(
        name="Test Opponent",
        abbreviation="OPP",
    )

    db_session.add(opponent)
    db_session.flush()

    game = Game(
        season=season,
        opponent_team=opponent,
        game_date=date(2026, 11, 15),
        venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED,
        opponent_score=70,
    )

    db_session.add(game)
    db_session.flush()

    assert game.id is not None

    stats = PlayerGameStats(
        game=game,
        season_roster=season_roster,
        participation_status=ParticipationStatus.PLAYED,
        three_point_attempts=5,
        three_point_makes=2,
        two_point_attempts=8,
        two_point_makes=4,
        free_throw_attempts=3,
        free_throw_makes=2,
        turnovers=2,
        assists=5,
        offensive_rebounds=1,
        defensive_rebounds=4,
        steals=2,
        deflections=3,
        personal_fouls=2,
    )

    db_session.add(stats)
    db_session.flush()

    assert stats.id is not None
    assert season.team is team
    assert season_roster.season is season
    assert season_roster.player is player
    assert game.season is season
    assert game.opponent_team is opponent
    assert stats.game is game
    assert stats.season_roster is season_roster
    assert season in team.seasons
    assert season_roster in season.season_rosters
    assert season_roster in player.season_rosters
    assert game in season.games
    assert game in opponent.opponent_games
    assert stats in game.player_game_stats
    assert stats in season_roster.game_stats


def test_player_cannot_be_added_twice_to_same_season(db_session):
    team = Team(name="JCP")
    player = Player(full_name="Test Player")

    season = Season(
        team=team,
        name="2026-27",
    )

    db_session.add_all([team, player, season])
    db_session.flush()

    first_roster_entry = SeasonRoster(
        season=season,
        player=player,
    )

    db_session.add(first_roster_entry)
    db_session.flush()

    with pytest.raises(IntegrityError):
        duplicate_roster_entry = SeasonRoster(
            season=season,
            player=player,
        )

        db_session.add(duplicate_roster_entry)
        db_session.flush()

def test_player_cannot_have_two_stat_rows_in_same_game(db_session):
    team = Team(name="JCP")
    opponent = Team(name="Opponent")
    player = Player(full_name="Test Player")

    season = Season(
        team=team,
        name="2026-27",
    )

    roster = SeasonRoster(
        season=season,
        player=player,
    )

    game = Game(
        season=season,
        opponent_team=opponent,
        game_date=date(2026, 11, 15),
        venue_type=VenueType.HOME,
    )

    db_session.add_all([team, opponent, player, season, roster, game])
    db_session.flush()

    first_stats = PlayerGameStats(
        game=game,
        season_roster=roster,
        participation_status=ParticipationStatus.PLAYED,
    )

    db_session.add(first_stats)
    db_session.flush()

    with pytest.raises(IntegrityError):
        duplicate_stats = PlayerGameStats(
            game=game,
            season_roster=roster,
            participation_status=ParticipationStatus.PLAYED,
        )

        db_session.add(duplicate_stats)
        db_session.flush()

@pytest.mark.parametrize(
    "field_name",
    [
        "three_point_attempts",
        "three_point_makes",
        "two_point_attempts",
        "two_point_makes",
        "free_throw_attempts",
        "free_throw_makes",
        "turnovers",
        "assists",
        "offensive_rebounds",
        "defensive_rebounds",
        "steals",
        "deflections",
        "personal_fouls",
    ],
)
def test_raw_stats_cannot_be_negative(db_session, field_name):
    team = Team(name="JCP")
    opponent = Team(name="Opponent")
    player = Player(full_name="Test Player")

    season = Season(
        team=team,
        name="2026-27",
    )

    roster = SeasonRoster(
        season=season,
        player=player,
    )

    game = Game(
        season=season,
        opponent_team=opponent,
        game_date=date(2026, 11, 15),
        venue_type=VenueType.HOME,
    )

    db_session.add_all([
        team,
        opponent,
        player,
        season,
        roster,
        game,
    ])
    db_session.flush()

    stats = PlayerGameStats(
        game=game,
        season_roster=roster,
        participation_status=ParticipationStatus.PLAYED,
    )

    setattr(stats, field_name, -1)

    db_session.add(stats)

    with pytest.raises(IntegrityError):
        db_session.flush()

@pytest.mark.parametrize(
    "makes_field, attempts_field",
    [
        ("three_point_makes", "three_point_attempts"),
        ("two_point_makes", "two_point_attempts"),
        ("free_throw_makes", "free_throw_attempts"),
    ],
)
def test_makes_cannot_exceed_attempts(
    db_session,
    makes_field,
    attempts_field,
):
    team = Team(name="JCP")
    opponent = Team(name="Opponent")
    player = Player(full_name="Test Player")

    season = Season(
        team=team,
        name="2026-27",
    )

    roster = SeasonRoster(
        season=season,
        player=player,
    )

    game = Game(
        season=season,
        opponent_team=opponent,
        game_date=date(2026, 11, 15),
        venue_type=VenueType.HOME,
    )

    db_session.add_all([
        team,
        opponent,
        player,
        season,
        roster,
        game,
    ])
    db_session.flush()

    stats = PlayerGameStats(
        game=game,
        season_roster=roster,
        participation_status=ParticipationStatus.PLAYED,
    )

    setattr(stats, attempts_field, 2)
    setattr(stats, makes_field, 3)

    db_session.add(stats)

    with pytest.raises(IntegrityError):
        db_session.flush()

def test_model_defaults_are_applied(db_session):
    team = Team(name="JCP")
    opponent = Team(name="Opponent")
    player = Player(full_name="Test Player")

    season = Season(
        team=team,
        name="2026-27",
    )

    roster = SeasonRoster(
        season=season,
        player=player,
    )

    game = Game(
        season=season,
        opponent_team=opponent,
        game_date=date(2026, 11, 15),
        venue_type=VenueType.HOME,
    )

    stats = PlayerGameStats(
        game=game,
        season_roster=roster,
        participation_status=ParticipationStatus.PLAYED,
    )

    db_session.add_all([
        team,
        opponent,
        player,
        season,
        roster,
        game,
        stats,
    ])

    db_session.flush()

    assert season.status == SeasonStatus.SETUP
    assert roster.status == RosterStatus.ACTIVE
    assert game.status == GameStatus.DRAFT

    assert stats.three_point_attempts == 0
    assert stats.three_point_makes == 0
    assert stats.two_point_attempts == 0
    assert stats.two_point_makes == 0
    assert stats.free_throw_attempts == 0
    assert stats.free_throw_makes == 0
    assert stats.turnovers == 0
    assert stats.assists == 0
    assert stats.offensive_rebounds == 0
    assert stats.defensive_rebounds == 0
    assert stats.steals == 0
    assert stats.deflections == 0
    assert stats.personal_fouls == 0

@pytest.mark.parametrize(
    "model_factory",
    [
        lambda: SeasonRoster(
            season_id=999999,
            player_id=999998,
        ),
        lambda: Game(
            season_id=999999,
            opponent_team_id=999998,
            game_date=date(2026, 11, 15),
            venue_type=VenueType.HOME,
        ),
        lambda: PlayerGameStats(
            game_id=999999,
            season_roster_id=999998,
            participation_status=ParticipationStatus.PLAYED,
        ),
    ],
)
def test_foreign_keys_require_existing_records(db_session, model_factory):
    record = model_factory()

    db_session.add(record)

    with pytest.raises(IntegrityError):
        db_session.flush()

def test_invalid_venue_type_is_rejected(db_session):
    team = Team(name="JCP")
    opponent = Team(name="Opponent")

    season = Season(
        team=team,
        name="2026-27",
    )

    game = Game(
        season=season,
        opponent_team=opponent,
        game_date=date(2026, 11, 15),
        venue_type="SOMEWHERE",
    )

    db_session.add_all([team, opponent, season, game])

    with pytest.raises(DataError):
        db_session.flush()

def test_did_not_play_cannot_have_nonzero_stats(db_session):
    team = Team(name="JCP")
    opponent = Team(name="Opponent")
    player = Player(full_name="Test Player")

    season = Season(
        team=team,
        name="2026-27",
    )

    roster = SeasonRoster(
        season=season,
        player=player,
    )

    game = Game(
        season=season,
        opponent_team=opponent,
        game_date=date(2026, 11, 15),
        venue_type=VenueType.HOME,
    )

    stats = PlayerGameStats(
        game=game,
        season_roster=roster,
        participation_status=ParticipationStatus.DID_NOT_PLAY,
        assists=1,
    )

    db_session.add_all([
        team,
        opponent,
        player,
        season,
        roster,
        game,
        stats,
    ])

    with pytest.raises(IntegrityError):
        db_session.flush()

def test_did_not_play_cannot_have_nonzero_stats(db_session):
    team = Team(name="JCP")
    opponent = Team(name="Opponent")
    player = Player(full_name="Test Player")

    season = Season(
        team=team,
        name="2026-27",
    )

    roster = SeasonRoster(
        season=season,
        player=player,
    )

    game = Game(
        season=season,
        opponent_team=opponent,
        game_date=date(2026, 11, 15),
        venue_type=VenueType.HOME,
    )

    stats = PlayerGameStats(
        game=game,
        season_roster=roster,
        participation_status=ParticipationStatus.DID_NOT_PLAY,
        assists=1,
    )

    db_session.add_all([
        team,
        opponent,
        player,
        season,
        roster,
        game,
        stats,
    ])

    with pytest.raises(IntegrityError):
        db_session.flush()

def test_team_cannot_have_duplicate_season_names(db_session):
    team = Team(name="JCP")

    first_season = Season(
        team=team,
        name="2026-27",
    )

    duplicate_season = Season(
        team=team,
        name="2026-27",
    )

    db_session.add_all([
        team,
        first_season,
        duplicate_season,
    ])

    with pytest.raises(IntegrityError):
        db_session.flush()

def test_team_names_are_unique_case_insensitively(db_session):
    first_team = Team(name="Jordan Christian Preparatory")
    duplicate_team = Team(name="jordan christian preparatory")

    db_session.add(first_team)
    db_session.flush()

    db_session.add(duplicate_team)

    with pytest.raises(IntegrityError):
        db_session.flush()