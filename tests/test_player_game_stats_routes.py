from datetime import date

from app.models.game import Game, GameStatus, VenueType
from app.models.player import Player
from app.models.season import Season
from app.models.season_roster import RosterStatus, SeasonRoster
from app.models.team import Team


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


def test_create_player_game_stats_route_returns_201_for_played(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    response = client.post(
        "/player-game-stats",
        json={
            "game_id": game.id,
            "season_roster_id": roster.id,
            "participation_status": "PLAYED",
            "three_point_attempts": 5,
            "three_point_makes": 2,
            "assists": 6,
            "steals": 2,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["game_id"] == game.id
    assert data["season_roster_id"] == roster.id
    assert data["participation_status"] == "PLAYED"
    assert data["three_point_attempts"] == 5
    assert data["three_point_makes"] == 2
    assert data["assists"] == 6
    assert data["steals"] == 2
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


def test_create_player_game_stats_route_returns_201_for_dnp(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    response = client.post(
        "/player-game-stats",
        json={
            "game_id": game.id,
            "season_roster_id": roster.id,
            "participation_status": "DID_NOT_PLAY",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["participation_status"] == "DID_NOT_PLAY"
    assert data["assists"] == 0
    assert data["three_point_attempts"] == 0
    assert data["personal_fouls"] == 0


def test_create_player_game_stats_route_returns_404_for_missing_game(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    response = client.post(
        "/player-game-stats",
        json={
            "game_id": 999999,
            "season_roster_id": roster.id,
            "participation_status": "PLAYED",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Game with ID 999999 was not found."
    )


def test_create_player_game_stats_route_returns_404_for_missing_roster(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    response = client.post(
        "/player-game-stats",
        json={
            "game_id": game.id,
            "season_roster_id": 999999,
            "participation_status": "PLAYED",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season roster entry with ID 999999 was not found."
    )


def test_create_player_game_stats_route_returns_409_for_wrong_season(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    other_player = Player(
        full_name="Other Season Player",
    )

    other_season = Season(
        team_id=season_team.id,
        name="2025-26",
    )

    db_session.add_all([
        other_player,
        other_season,
    ])
    db_session.commit()

    db_session.refresh(other_player)
    db_session.refresh(other_season)

    other_roster = SeasonRoster(
        season_id=other_season.id,
        player_id=other_player.id,
        status=RosterStatus.ACTIVE,
    )

    db_session.add(other_roster)
    db_session.commit()
    db_session.refresh(other_roster)

    response = client.post(
        "/player-game-stats",
        json={
            "game_id": game.id,
            "season_roster_id": other_roster.id,
            "participation_status": "PLAYED",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Game and season roster must belong to the same season."
    )


def test_create_player_game_stats_route_returns_409_for_duplicate(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    payload = {
        "game_id": game.id,
        "season_roster_id": roster.id,
        "participation_status": "PLAYED",
    }

    first_response = client.post(
        "/player-game-stats",
        json=payload,
    )

    assert first_response.status_code == 201

    second_response = client.post(
        "/player-game-stats",
        json=payload,
    )

    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Player game stats already exist for this game and roster entry."
    )


def test_create_player_game_stats_route_returns_422_for_invalid_shooting(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    response = client.post(
        "/player-game-stats",
        json={
            "game_id": game.id,
            "season_roster_id": roster.id,
            "participation_status": "PLAYED",
            "three_point_attempts": 3,
            "three_point_makes": 4,
        },
    )

    assert response.status_code == 422


def test_create_player_game_stats_route_returns_422_for_invalid_dnp(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    response = client.post(
        "/player-game-stats",
        json={
            "game_id": game.id,
            "season_roster_id": roster.id,
            "participation_status": "DID_NOT_PLAY",
            "assists": 1,
        },
    )

    assert response.status_code == 422


def test_list_player_game_stats_route_returns_entries(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    create_response = client.post(
        "/player-game-stats",
        json={
            "game_id": game.id,
            "season_roster_id": roster.id,
            "participation_status": "PLAYED",
            "assists": 3,
        },
    )

    assert create_response.status_code == 201

    response = client.get(
        "/player-game-stats"
    )

    assert response.status_code == 200

    data = response.json()

    assert len(data) == 1
    assert data[0]["game_id"] == game.id
    assert data[0]["season_roster_id"] == roster.id
    assert data[0]["assists"] == 3


def test_get_player_game_stats_route_returns_existing(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    create_response = client.post(
        "/player-game-stats",
        json={
            "game_id": game.id,
            "season_roster_id": roster.id,
            "participation_status": "PLAYED",
            "steals": 2,
        },
    )

    assert create_response.status_code == 201

    stats_id = create_response.json()["id"]

    response = client.get(
        f"/player-game-stats/{stats_id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == stats_id
    assert response.json()["steals"] == 2


def test_get_player_game_stats_route_returns_404_for_missing(
    client,
):
    response = client.get(
        "/player-game-stats/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Player game stats with ID 999999 were not found."
    )


def test_update_player_game_stats_route_partial_update(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    create_response = client.post(
        "/player-game-stats",
        json={
            "game_id": game.id,
            "season_roster_id": roster.id,
            "participation_status": "PLAYED",
            "three_point_attempts": 5,
            "three_point_makes": 2,
            "assists": 3,
        },
    )

    assert create_response.status_code == 201

    stats_id = create_response.json()["id"]

    response = client.patch(
        f"/player-game-stats/{stats_id}",
        json={
            "assists": 7,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == stats_id
    assert data["assists"] == 7
    assert data["three_point_attempts"] == 5
    assert data["three_point_makes"] == 2
    assert data["participation_status"] == "PLAYED"


def test_update_player_game_stats_route_returns_422_for_invalid_final_state(
    client,
    db_session,
):
    season_team, season, game, roster = _create_dependencies(
        db_session
    )

    create_response = client.post(
        "/player-game-stats",
        json={
            "game_id": game.id,
            "season_roster_id": roster.id,
            "participation_status": "PLAYED",
            "three_point_attempts": 5,
            "three_point_makes": 2,
        },
    )

    assert create_response.status_code == 201

    stats_id = create_response.json()["id"]

    response = client.patch(
        f"/player-game-stats/{stats_id}",
        json={
            "three_point_makes": 6,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Three-point makes cannot exceed three-point attempts"
    )