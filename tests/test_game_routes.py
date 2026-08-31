from datetime import date, timedelta

from app.models.player import Player
from app.models.season_roster import RosterStatus, SeasonRoster
from app.models.team import Team


def _create_game_dependencies(client, db_session):
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

    season_response = client.post(
        "/seasons",
        json={
            "team_id": season_team.id,
            "name": "2026-27",
        },
    )

    assert season_response.status_code == 201

    return (
        season_team,
        opponent_team,
        season_response.json(),
    )


def _create_game(
    client,
    season_id,
    opponent_team_id,
    game_date=None,
    venue_type="HOME",
    opponent_score=None,
    notes=None,
):
    if game_date is None:
        game_date = date.today()

    response = client.post(
        "/games",
        json={
            "season_id": season_id,
            "opponent_team_id": opponent_team_id,
            "game_date": game_date.isoformat(),
            "venue_type": venue_type,
            "status": "DRAFT",
            "opponent_score": opponent_score,
            "notes": notes,
        },
    )

    assert response.status_code == 201
    return response.json()


def _add_player_game_stats(
    client,
    db_session,
    season_id,
    game_id,
    participation_status="PLAYED",
):
    player = Player(
        full_name="Stats Player",
    )

    db_session.add(player)
    db_session.commit()
    db_session.refresh(player)

    roster = SeasonRoster(
        season_id=season_id,
        player_id=player.id,
        status=RosterStatus.ACTIVE,
    )

    db_session.add(roster)
    db_session.commit()
    db_session.refresh(roster)

    response = client.post(
        "/player-game-stats",
        json={
            "game_id": game_id,
            "season_roster_id": roster.id,
            "participation_status": participation_status,
        },
    )

    assert response.status_code == 201

    return response.json()


def test_create_game_route_returns_201_and_expected_values(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game_date = date.today()

    response = client.post(
        "/games",
        json={
            "season_id": season["id"],
            "opponent_team_id": opponent_team.id,
            "game_date": game_date.isoformat(),
            "venue_type": "HOME",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["season_id"] == season["id"]
    assert data["opponent_team_id"] == opponent_team.id
    assert data["game_date"] == game_date.isoformat()
    assert data["venue_type"] == "HOME"
    assert data["status"] == "DRAFT"
    assert data["opponent_score"] is None
    assert data["notes"] is None
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None


def test_create_game_route_returns_422_for_direct_completed_creation(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    response = client.post(
        "/games",
        json={
            "season_id": season["id"],
            "opponent_team_id": opponent_team.id,
            "game_date": date.today().isoformat(),
            "venue_type": "HOME",
            "status": "COMPLETED",
            "opponent_score": 65,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "New games must start as DRAFT"
    )


def test_create_game_route_returns_404_for_missing_season(
    client,
    db_session,
):
    opponent_team = Team(
        name="Opponent Academy",
        abbreviation="OA",
    )

    db_session.add(opponent_team)
    db_session.commit()
    db_session.refresh(opponent_team)

    response = client.post(
        "/games",
        json={
            "season_id": 999999,
            "opponent_team_id": opponent_team.id,
            "game_date": date.today().isoformat(),
            "venue_type": "HOME",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season with ID 999999 was not found."
    )


def test_create_game_route_returns_404_for_missing_opponent(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    response = client.post(
        "/games",
        json={
            "season_id": season["id"],
            "opponent_team_id": 999999,
            "game_date": date.today().isoformat(),
            "venue_type": "HOME",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Opponent team with ID 999999 was not found."
    )


def test_create_game_route_returns_409_for_season_team_as_opponent(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    response = client.post(
        "/games",
        json={
            "season_id": season["id"],
            "opponent_team_id": season_team.id,
            "game_date": date.today().isoformat(),
            "venue_type": "HOME",
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Opponent team cannot be the same team as the seasons team."
    )


def test_create_game_route_returns_422_for_invalid_pydantic_data(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    response = client.post(
        "/games",
        json={
            "season_id": season["id"],
            "opponent_team_id": opponent_team.id,
            "game_date": date.today().isoformat(),
            "venue_type": "INVALID_VENUE",
        },
    )

    assert response.status_code == 422


def test_create_game_route_returns_422_for_negative_opponent_score(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    response = client.post(
        "/games",
        json={
            "season_id": season["id"],
            "opponent_team_id": opponent_team.id,
            "game_date": date.today().isoformat(),
            "venue_type": "HOME",
            "opponent_score": -1,
        },
    )

    assert response.status_code == 422


def test_list_games_route_returns_games_in_id_order(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    first_game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        game_date=date.today(),
        venue_type="HOME",
    )

    second_game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        game_date=date.today() + timedelta(days=1),
        venue_type="AWAY",
    )

    response = client.get("/games")

    assert response.status_code == 200

    data = response.json()

    assert [game["id"] for game in data] == [
        first_game["id"],
        second_game["id"],
    ]


def test_get_game_route_returns_existing_game(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
    )

    response = client.get(
        f"/games/{game['id']}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == game["id"]
    assert response.json()["season_id"] == season["id"]
    assert response.json()["opponent_team_id"] == opponent_team.id


def test_get_game_route_returns_404_for_missing_game(client):
    response = client.get(
        "/games/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Game with ID 999999 was not found."
    )


def test_update_game_route_partial_update(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        venue_type="HOME",
        notes="Original note",
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "venue_type": "NEUTRAL",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == game["id"]
    assert data["season_id"] == season["id"]
    assert data["opponent_team_id"] == opponent_team.id
    assert data["venue_type"] == "NEUTRAL"
    assert data["status"] == "DRAFT"
    assert data["notes"] == "Original note"


def test_update_game_route_can_clear_optional_fields(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        opponent_score=65,
        notes="Tournament game",
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "opponent_score": None,
            "notes": None,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["opponent_score"] is None
    assert data["notes"] is None


def test_update_game_route_returns_404_for_missing_game(client):
    response = client.patch(
        "/games/999999",
        json={
            "venue_type": "AWAY",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Game with ID 999999 was not found."
    )


def test_update_game_route_returns_404_for_missing_season(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "season_id": 999999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season with ID 999999 was not found."
    )


def test_update_game_route_returns_404_for_missing_opponent(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "opponent_team_id": 999999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Opponent team with ID 999999 was not found."
    )


def test_update_game_route_returns_409_for_season_team_as_opponent(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "opponent_team_id": season_team.id,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Opponent team cannot be the same team as the seasons team."
    )


def test_update_draft_game_without_stats_cannot_complete(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        opponent_score=65,
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "status": "COMPLETED",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Completed game requires at least one player game stats row"
    )


def test_update_draft_game_with_only_dnp_cannot_complete(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        opponent_score=65,
    )

    _add_player_game_stats(
        client,
        db_session,
        season["id"],
        game["id"],
        participation_status="DID_NOT_PLAY",
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "status": "COMPLETED",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Completed game requires at least one PLAYED "
        "player game stats row"
    )


def test_update_draft_game_with_played_stats_can_complete(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        game_date=date.today() - timedelta(days=1),
        opponent_score=65,
    )

    _add_player_game_stats(
        client,
        db_session,
        season["id"],
        game["id"],
        participation_status="PLAYED",
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "status": "COMPLETED",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "COMPLETED"
    assert data["opponent_score"] == 65


def test_update_draft_game_without_opponent_score_cannot_complete(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
    )

    _add_player_game_stats(
        client,
        db_session,
        season["id"],
        game["id"],
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "status": "COMPLETED",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Completed game requires an opponent score"
    )


def test_update_future_draft_game_cannot_complete(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        game_date=date.today() + timedelta(days=1),
        opponent_score=70,
    )

    _add_player_game_stats(
        client,
        db_session,
        season["id"],
        game["id"],
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "status": "COMPLETED",
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Future-dated game cannot be completed"
    )


def test_update_completed_game_cannot_clear_opponent_score(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        game_date=date.today() - timedelta(days=1),
        opponent_score=65,
    )

    _add_player_game_stats(
        client,
        db_session,
        season["id"],
        game["id"],
    )

    complete_response = client.patch(
        f"/games/{game['id']}",
        json={
            "status": "COMPLETED",
        },
    )

    assert complete_response.status_code == 200

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "opponent_score": None,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Completed game requires an opponent score"
    )


def test_update_completed_game_cannot_move_to_future_date(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        game_date=date.today() - timedelta(days=1),
        opponent_score=65,
    )

    _add_player_game_stats(
        client,
        db_session,
        season["id"],
        game["id"],
    )

    complete_response = client.patch(
        f"/games/{game['id']}",
        json={
            "status": "COMPLETED",
        },
    )

    assert complete_response.status_code == 200

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "game_date": (
                date.today() + timedelta(days=1)
            ).isoformat(),
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Future-dated game cannot be completed"
    )


def test_completed_game_remains_editable_when_final_state_valid(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
        opponent_score=65,
    )

    _add_player_game_stats(
        client,
        db_session,
        season["id"],
        game["id"],
    )

    complete_response = client.patch(
        f"/games/{game['id']}",
        json={
            "status": "COMPLETED",
        },
    )

    assert complete_response.status_code == 200

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "notes": "Reviewed after completion",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["status"] == "COMPLETED"
    assert data["opponent_score"] == 65
    assert data["notes"] == "Reviewed after completion"


def test_update_game_route_returns_422_for_required_field_null(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "status": None,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Game status cannot be None"
    )

    def test_update_game_route_returns_409_when_changing_season_with_stats(
            client,
            db_session,
    ):
        season_team, opponent_team, season = _create_game_dependencies(
            client,
            db_session,
        )

        second_season_response = client.post(
            "/seasons",
            json={
                "team_id": season_team.id,
                "name": "2027-28",
            },
        )

        assert second_season_response.status_code == 201
        second_season = second_season_response.json()

        game = _create_game(
            client,
            season["id"],
            opponent_team.id,
        )

        _add_player_game_stats(
            client,
            db_session,
            season["id"],
            game["id"],
        )

        response = client.patch(
            f"/games/{game['id']}",
            json={
                "season_id": second_season["id"],
            },
        )

        assert response.status_code == 409
        assert response.json()["detail"] == (
            "Game seasons cannot be changed after player game stats exist."
        )

def test_update_game_route_returns_409_when_changing_season_with_stats(
    client,
    db_session,
):
    season_team, opponent_team, season = _create_game_dependencies(
        client,
        db_session,
    )

    second_season_response = client.post(
        "/seasons",
        json={
            "team_id": season_team.id,
            "name": "2027-28",
        },
    )

    assert second_season_response.status_code == 201
    second_season = second_season_response.json()

    game = _create_game(
        client,
        season["id"],
        opponent_team.id,
    )

    _add_player_game_stats(
        client,
        db_session,
        season["id"],
        game["id"],
    )

    response = client.patch(
        f"/games/{game['id']}",
        json={
            "season_id": second_season["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Game seasons cannot be changed after player game stats exist."
    )