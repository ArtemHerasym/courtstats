from datetime import date
import re
from unittest.mock import patch

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.models.game import Game, GameStatus, VenueType
from app.models.player import Player
from app.models.player_game_stats import ParticipationStatus, PlayerGameStats
from app.models.season import Season
from app.models.season_roster import SeasonRoster
from app.models.team import Team
from app.services.game import GameNotFoundError, delete_game
from app.services.statistics import calculate_team_season_summary


@pytest.fixture
def deletion_data(db_session):
    team = Team(name="Home")
    opponent = Team(name="Opponent")
    player = Player(full_name="Deletion Player")
    db_session.add_all([team, opponent, player])
    db_session.flush()
    season = Season(team_id=team.id, name="Deletion season")
    db_session.add(season)
    db_session.flush()
    roster = SeasonRoster(season_id=season.id, player_id=player.id)
    db_session.add(roster)
    db_session.flush()
    games = [Game(
        season_id=season.id, opponent_team_id=opponent.id,
        game_date=date.today(), venue_type=VenueType.HOME,
        status=GameStatus.COMPLETED, opponent_score=3,
    ) for _ in range(2)]
    db_session.add_all(games)
    db_session.flush()
    stats = [PlayerGameStats(
        game_id=game.id, season_roster_id=roster.id,
        participation_status=ParticipationStatus.PLAYED,
        two_point_makes=makes, two_point_attempts=4,
    ) for game, makes in zip(games, [3, 1])]
    db_session.add_all(stats)
    db_session.commit()
    return season, roster, player, team, opponent, games, stats


@pytest.mark.parametrize("status,with_stats", [
    (GameStatus.DRAFT, False), (GameStatus.DRAFT, True),
    (GameStatus.COMPLETED, True),
])
def test_delete_game_preserves_unrelated_data(db_session, deletion_data, status, with_stats):
    season, roster, player, team, opponent, games, stats = deletion_data
    game_id = games[0].id
    games[0].status = status
    if not with_stats:
        db_session.delete(stats[0])
    else:
        other_player = Player(full_name="Second player")
        db_session.add(other_player)
        db_session.flush()
        other_roster = SeasonRoster(season_id=season.id, player_id=other_player.id)
        db_session.add(other_roster)
        db_session.flush()
        db_session.add(PlayerGameStats(
            game_id=game_id, season_roster_id=other_roster.id,
            participation_status=ParticipationStatus.DID_NOT_PLAY,
        ))
    db_session.commit()
    # Exercise deletion with the ORM collection already loaded.
    assert len(games[0].player_game_stats) == (2 if with_stats else 0)
    with patch.object(db_session, "commit", wraps=db_session.commit) as commit:
        delete_game(db_session, game_id)
    commit.assert_called_once_with()
    assert db_session.get(Game, game_id) is None
    assert not db_session.scalars(select(PlayerGameStats).where(
        PlayerGameStats.game_id == game_id,
    )).all()
    for obj in [season, roster, player, team, opponent, games[1], stats[1]]:
        assert db_session.get(type(obj), obj.id) is not None


def test_delete_missing_game(db_session):
    with pytest.raises(GameNotFoundError, match="999999"):
        delete_game(db_session, 999999)


@pytest.mark.parametrize("failure_point", ["execute", "delete", "commit"])
def test_delete_database_failure_rolls_back(db_session, deletion_data, failure_point):
    game = deletion_data[5][0]
    game_id, stats_id = game.id, deletion_data[6][0].id
    with patch.object(db_session, failure_point, side_effect=SQLAlchemyError("failure")):
        with patch.object(db_session, "rollback", wraps=db_session.rollback) as rollback:
            with pytest.raises(SQLAlchemyError, match="failure"):
                delete_game(db_session, game_id)
            rollback.assert_called_once_with()
    assert db_session.get(Game, game_id) is not None
    assert db_session.get(PlayerGameStats, stats_id) is not None


def test_deleted_completed_game_no_longer_contributes_to_analytics(db_session, deletion_data):
    season = deletion_data[0]
    before = calculate_team_season_summary(db_session, season.id)
    assert (before["games_played"], before["points"], before["wins"]) == (2, 8, 1)
    delete_game(db_session, deletion_data[5][0].id)
    after = calculate_team_season_summary(db_session, season.id)
    assert (after["games_played"], after["points"], after["wins"], after["losses"]) == (1, 2, 0, 1)
    assert after["points_per_game"] == 2
    assert after["field_goal_percentage"] == 0.25


@pytest.mark.parametrize("status", [GameStatus.DRAFT, GameStatus.COMPLETED])
def test_delete_form_and_success(logged_in_client, db_session, deletion_data, status):
    game = deletion_data[5][0]
    game.status = status
    db_session.commit()
    game_id, season_id = game.id, game.season_id
    page = logged_in_client.get(f"/app/games?season_id={season_id}")
    form = re.search(r'<form\s+method="post"\s+action="[^"]*/app/games/'
                     + str(game_id) + r'/delete"[\s\S]*?</form>', page.text)
    assert form is not None
    assert 'type="submit"' in form.group()
    assert 'button-destructive' in form.group()
    message = (
        "Delete this draft game? This cannot be undone."
        if status == GameStatus.DRAFT else
        "Delete this completed game and all of its player statistics? This will change season analytics and cannot be undone."
    )
    assert f"return confirm('{message}');" in form.group()
    token = re.search(r'name="csrf_token"\s+value="([^"]+)"', form.group()).group(1)
    response = logged_in_client.post(f"/app/games/{game_id}/delete",
                                    data={"csrf_token": token}, follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == f"/app/games?season_id={season_id}&deleted=1"
    assert db_session.get(Game, game_id) is None
    assert not db_session.scalars(select(PlayerGameStats).where(PlayerGameStats.game_id == game_id)).all()
    redirected = logged_in_client.get(response.headers["location"])
    assert redirected.status_code == 200
    assert "Game deleted." in redirected.text
    assert f"/app/games/{game_id}/delete" not in redirected.text
    assert "Game deleted." not in logged_in_client.get(f"/app/games?season_id={season_id}").text


@pytest.mark.parametrize("data", [{}, {"csrf_token": "invalid"}])
def test_delete_rejects_csrf(logged_in_client, db_session, deletion_data, data):
    game_id = deletion_data[5][0].id
    response = logged_in_client.post(f"/app/games/{game_id}/delete", data=data)
    assert response.status_code == 403
    assert response.json() == {"detail": "Invalid CSRF token."}
    assert db_session.get(Game, game_id) is not None


def test_delete_missing_game_page(authenticated_client):
    response = authenticated_client.post("/app/games/999999/delete")
    assert response.status_code == 404
    assert response.text == "Game not found."


def test_delete_requires_authentication(client, db_session, deletion_data):
    game_id = deletion_data[5][0].id
    response = client.post(f"/app/games/{game_id}/delete", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    assert db_session.get(Game, game_id) is not None


def test_get_cannot_delete(authenticated_client, db_session, deletion_data):
    game_id = deletion_data[5][0].id
    response = authenticated_client.get(f"/app/games/{game_id}/delete")
    assert response.status_code == 405
    assert db_session.get(Game, game_id) is not None
