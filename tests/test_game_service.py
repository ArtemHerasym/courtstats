from datetime import date, timedelta

import pytest

from app.models.game import GameStatus, VenueType
from app.models.season import Season
from app.models.team import Team
from app.schemas.game import GameCreate, GameUpdate
from app.services.game import (
    GameNotFoundError,
    GameOpponentConflictError,
    OpponentTeamNotFoundError,
    create_game,
    get_game,
    list_games,
    update_game,
)
from app.services.season import SeasonNotFoundError


def _create_game_dependencies(db_session):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    db_session.add_all([
        season_team,
        opponent_team,
    ])
    db_session.commit()
    db_session.refresh(season_team)
    db_session.refresh(opponent_team)

    season = Season(
        team_id=season_team.id,
        name="2026-27",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    return season_team, opponent_team, season


def test_create_valid_draft_game(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game_date = date.today()

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=game_date,
            venue_type=VenueType.HOME,
        ),
    )

    assert game.id is not None
    assert game.season_id == season.id
    assert game.opponent_team_id == opponent_team.id
    assert game.game_date == game_date
    assert game.venue_type == VenueType.HOME
    assert game.status == GameStatus.DRAFT
    assert game.opponent_score is None
    assert game.notes is None
    assert game.created_at is not None
    assert game.updated_at is not None


def test_create_valid_completed_game(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today() - timedelta(days=1),
            venue_type=VenueType.AWAY,
            status=GameStatus.COMPLETED,
            opponent_score=68,
        ),
    )

    assert game.status == GameStatus.COMPLETED
    assert game.opponent_score == 68


def test_create_game_rejects_missing_season(db_session):
    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    db_session.add(opponent_team)
    db_session.commit()
    db_session.refresh(opponent_team)

    with pytest.raises(SeasonNotFoundError):
        create_game(
            db_session,
            GameCreate(
                season_id=999999,
                opponent_team_id=opponent_team.id,
                game_date=date.today(),
                venue_type=VenueType.HOME,
            ),
        )


def test_create_game_rejects_missing_opponent_team(db_session):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    db_session.add(season_team)
    db_session.commit()
    db_session.refresh(season_team)

    season = Season(
        team_id=season_team.id,
        name="2026-27",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    with pytest.raises(OpponentTeamNotFoundError):
        create_game(
            db_session,
            GameCreate(
                season_id=season.id,
                opponent_team_id=999999,
                game_date=date.today(),
                venue_type=VenueType.HOME,
            ),
        )


def test_create_game_rejects_season_team_as_opponent(db_session):
    season_team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )

    db_session.add(season_team)
    db_session.commit()
    db_session.refresh(season_team)

    season = Season(
        team_id=season_team.id,
        name="2026-27",
    )

    db_session.add(season)
    db_session.commit()
    db_session.refresh(season)

    with pytest.raises(GameOpponentConflictError):
        create_game(
            db_session,
            GameCreate(
                season_id=season.id,
                opponent_team_id=season_team.id,
                game_date=date.today(),
                venue_type=VenueType.HOME,
            ),
        )


def test_create_future_draft_game_is_allowed(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    future_date = date.today() + timedelta(days=30)

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=future_date,
            venue_type=VenueType.AWAY,
        ),
    )

    assert game.game_date == future_date
    assert game.status == GameStatus.DRAFT


def test_create_future_completed_game_is_rejected(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    with pytest.raises(
        ValueError,
        match="Future-dated game cannot be completed",
    ):
        create_game(
            db_session,
            GameCreate(
                season_id=season.id,
                opponent_team_id=opponent_team.id,
                game_date=date.today() + timedelta(days=1),
                venue_type=VenueType.AWAY,
                status=GameStatus.COMPLETED,
                opponent_score=70,
            ),
        )


def test_create_completed_game_without_opponent_score_is_rejected(
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    with pytest.raises(
        ValueError,
        match="Completed game requires an opponent score",
    ):
        create_game(
            db_session,
            GameCreate(
                season_id=season.id,
                opponent_team_id=opponent_team.id,
                game_date=date.today(),
                venue_type=VenueType.HOME,
                status=GameStatus.COMPLETED,
            ),
        )


def test_get_game_returns_existing_game(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    created_game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today(),
            venue_type=VenueType.HOME,
        ),
    )

    game = get_game(
        db_session,
        created_game.id,
    )

    assert game.id == created_game.id
    assert game.season_id == season.id
    assert game.opponent_team_id == opponent_team.id


def test_get_game_raises_not_found(db_session):
    with pytest.raises(
        GameNotFoundError,
        match="Game with ID 999999 was not found.",
    ):
        get_game(db_session, 999999)


def test_list_games_returns_games_in_id_order(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    first_game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today(),
            venue_type=VenueType.HOME,
        ),
    )

    second_game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today() + timedelta(days=1),
            venue_type=VenueType.AWAY,
        ),
    )

    games = list_games(db_session)

    assert [game.id for game in games] == [
        first_game.id,
        second_game.id,
    ]


def test_update_game_partial_update_preserves_omitted_fields(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today(),
            venue_type=VenueType.HOME,
            notes="Original note",
        ),
    )

    updated_game = update_game(
        db_session,
        game.id,
        GameUpdate(
            venue_type=VenueType.NEUTRAL,
        ),
    )

    assert updated_game.id == game.id
    assert updated_game.season_id == season.id
    assert updated_game.opponent_team_id == opponent_team.id
    assert updated_game.game_date == date.today()
    assert updated_game.venue_type == VenueType.NEUTRAL
    assert updated_game.status == GameStatus.DRAFT
    assert updated_game.opponent_score is None
    assert updated_game.notes == "Original note"


def test_update_game_can_clear_optional_notes(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today(),
            venue_type=VenueType.HOME,
            notes="Tournament game",
        ),
    )

    updated_game = update_game(
        db_session,
        game.id,
        GameUpdate(
            notes=None,
        ),
    )

    assert updated_game.notes is None


def test_update_draft_game_to_completed_is_allowed(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today() - timedelta(days=1),
            venue_type=VenueType.HOME,
            opponent_score=65,
        ),
    )

    updated_game = update_game(
        db_session,
        game.id,
        GameUpdate(
            status=GameStatus.COMPLETED,
        ),
    )

    assert updated_game.status == GameStatus.COMPLETED
    assert updated_game.opponent_score == 65


def test_update_completed_game_cannot_clear_opponent_score(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today() - timedelta(days=1),
            venue_type=VenueType.HOME,
            status=GameStatus.COMPLETED,
            opponent_score=65,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Completed game requires an opponent score",
    ):
        update_game(
            db_session,
            game.id,
            GameUpdate(
                opponent_score=None,
            ),
        )


def test_update_completed_game_cannot_move_to_future_date(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today() - timedelta(days=1),
            venue_type=VenueType.HOME,
            status=GameStatus.COMPLETED,
            opponent_score=65,
        ),
    )

    with pytest.raises(
        ValueError,
        match="Future-dated game cannot be completed",
    ):
        update_game(
            db_session,
            game.id,
            GameUpdate(
                game_date=date.today() + timedelta(days=1),
            ),
        )


def test_update_game_rejects_missing_final_season(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today(),
            venue_type=VenueType.HOME,
        ),
    )

    with pytest.raises(SeasonNotFoundError):
        update_game(
            db_session,
            game.id,
            GameUpdate(
                season_id=999999,
            ),
        )


def test_update_game_rejects_missing_final_opponent_team(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today(),
            venue_type=VenueType.HOME,
        ),
    )

    with pytest.raises(OpponentTeamNotFoundError):
        update_game(
            db_session,
            game.id,
            GameUpdate(
                opponent_team_id=999999,
            ),
        )


def test_update_game_rejects_season_team_as_opponent(db_session):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today(),
            venue_type=VenueType.HOME,
        ),
    )

    with pytest.raises(GameOpponentConflictError):
        update_game(
            db_session,
            game.id,
            GameUpdate(
                opponent_team_id=season_team.id,
            ),
        )


@pytest.mark.parametrize(
    ("field_name", "expected_message"),
    [
        ("season_id", "Game season_id cannot be None"),
        (
            "opponent_team_id",
            "Game opponent_team_id cannot be None",
        ),
        ("game_date", "Game game_date cannot be None"),
        ("venue_type", "Game venue_type cannot be None"),
        ("status", "Game status cannot be None"),
    ],
)
def test_update_game_rejects_none_for_required_fields(
    db_session,
    field_name,
    expected_message,
):
    season_team, opponent_team, season = _create_game_dependencies(
        db_session
    )

    game = create_game(
        db_session,
        GameCreate(
            season_id=season.id,
            opponent_team_id=opponent_team.id,
            game_date=date.today(),
            venue_type=VenueType.HOME,
        ),
    )

    update = GameUpdate(**{field_name: None})

    with pytest.raises(
        ValueError,
        match=expected_message,
    ):
        update_game(
            db_session,
            game.id,
            update,
        )