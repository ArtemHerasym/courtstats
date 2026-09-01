from app.models.team import Team

def _create_season(authenticated_client, db_session, name="2026-27"):
    team = Team(
        name="Jordan Christian Preparatory",
        abbreviation="JCP",
    )
    db_session.add(team)
    db_session.commit()
    db_session.refresh(team)

    response = authenticated_client.post(
        "/seasons",
        json={
            "team_id": team.id,
            "name": name,
        },
    )

    assert response.status_code == 201
    return response.json()


def _create_player(authenticated_client, full_name="John Smith"):
    response = authenticated_client.post(
        "/players",
        json={
            "full_name": full_name,
        },
    )

    assert response.status_code == 201
    return response.json()

def test_create_season_roster_route_returns_201(authenticated_client, db_session):
    season = _create_season(authenticated_client, db_session)
    player = _create_player(authenticated_client)

    response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": player["id"],
            "jersey_number": 12,
            "position": "Guard",
            "grade_level": "Senior",
        },
    )

    assert response.status_code == 201


def test_create_season_roster_route_returns_expected_values(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    player = _create_player(authenticated_client)

    response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": player["id"],
            "jersey_number": 12,
            "position": "Guard",
            "grade_level": "Senior",
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["season_id"] == season["id"]
    assert data["player_id"] == player["id"]
    assert data["jersey_number"] == 12
    assert data["position"] == "Guard"
    assert data["grade_level"] == "Senior"
    assert data["status"] == "ACTIVE"
    assert data["id"] is not None
    assert data["created_at"] is not None
    assert data["updated_at"] is not None

def test_list_season_rosters_route_returns_entries_in_id_order(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    first_player = _create_player(authenticated_client, "First Player")
    second_player = _create_player(authenticated_client, "Second Player")

    first_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": first_player["id"],
        },
    )

    second_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": second_player["id"],
        },
    )

    response = authenticated_client.get("/seasons-rosters")

    assert response.status_code == 200

    data = response.json()

    assert [roster["id"] for roster in data] == [
        first_response.json()["id"],
        second_response.json()["id"],
    ]


def test_get_season_roster_route_returns_existing_entry(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    player = _create_player(authenticated_client)

    create_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": player["id"],
            "jersey_number": 12,
        },
    )

    roster_id = create_response.json()["id"]

    response = authenticated_client.get(
        f"/seasons-rosters/{roster_id}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == roster_id
    assert response.json()["season_id"] == season["id"]
    assert response.json()["player_id"] == player["id"]
    assert response.json()["jersey_number"] == 12


def test_get_season_roster_route_returns_404_for_missing_id(authenticated_client):
    response = authenticated_client.get(
        "/seasons-rosters/999999"
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season roster entry with ID 999999 was not found."
    )

def test_update_season_roster_route_partial_update(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    player = _create_player(authenticated_client)

    create_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": player["id"],
            "jersey_number": 12,
            "position": "Guard",
            "grade_level": "Junior",
        },
    )

    roster_id = create_response.json()["id"]

    response = authenticated_client.patch(
        f"/seasons-rosters/{roster_id}",
        json={
            "grade_level": "Senior",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == roster_id
    assert data["season_id"] == season["id"]
    assert data["player_id"] == player["id"]
    assert data["jersey_number"] == 12
    assert data["position"] == "Guard"
    assert data["grade_level"] == "Senior"
    assert data["status"] == "ACTIVE"

def test_update_season_roster_route_can_clear_optional_field(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    player = _create_player(authenticated_client)

    create_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": player["id"],
            "position": "Guard",
        },
    )

    roster_id = create_response.json()["id"]

    response = authenticated_client.patch(
        f"/seasons-rosters/{roster_id}",
        json={
            "position": None,
        },
    )

    assert response.status_code == 200
    assert response.json()["position"] is None

def test_create_season_roster_route_returns_404_for_missing_season(
    authenticated_client,
):
    player = _create_player(authenticated_client)

    response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": 999999,
            "player_id": player["id"],
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season with ID 999999 was not found."
    )


def test_create_season_roster_route_returns_404_for_missing_player(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)

    response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": 999999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Player with ID 999999 was not found."
    )


def test_create_season_roster_route_returns_409_for_duplicate_membership(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    player = _create_player(authenticated_client)

    roster_data = {
        "season_id": season["id"],
        "player_id": player["id"],
    }

    first_response = authenticated_client.post(
        "/seasons-rosters",
        json=roster_data,
    )

    second_response = authenticated_client.post(
        "/seasons-rosters",
        json=roster_data,
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Player is already on this seasons roster."
    )


def test_create_season_roster_route_returns_409_for_active_jersey_conflict(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    first_player = _create_player(authenticated_client, "First Player")
    second_player = _create_player(authenticated_client, "Second Player")

    first_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": first_player["id"],
            "jersey_number": 12,
        },
    )

    second_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": second_player["id"],
            "jersey_number": 12,
        },
    )

    assert first_response.status_code == 201
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == (
        "Jersey number 12 is already assigned "
        "to an active player in this seasons."
    )

def test_create_season_roster_route_returns_422_for_invalid_input(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    player = _create_player(authenticated_client)

    response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": player["id"],
            "status": "INVALID_STATUS",
        },
    )

    assert response.status_code == 422


def test_update_season_roster_route_returns_404_for_missing_roster(authenticated_client):
    response = authenticated_client.patch(
        "/seasons-rosters/999999",
        json={
            "position": "Guard",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season roster entry with ID 999999 was not found."
    )


def test_update_season_roster_route_returns_404_for_missing_season(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    player = _create_player(authenticated_client)

    create_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": player["id"],
        },
    )

    roster_id = create_response.json()["id"]

    response = authenticated_client.patch(
        f"/seasons-rosters/{roster_id}",
        json={
            "season_id": 999999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Season with ID 999999 was not found."
    )


def test_update_season_roster_route_returns_404_for_missing_player(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    player = _create_player(authenticated_client)

    create_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": player["id"],
        },
    )

    roster_id = create_response.json()["id"]

    response = authenticated_client.patch(
        f"/seasons-rosters/{roster_id}",
        json={
            "player_id": 999999,
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == (
        "Player with ID 999999 was not found."
    )


def test_update_season_roster_route_returns_409_for_membership_conflict(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    first_player = _create_player(authenticated_client, "First Player")
    second_player = _create_player(authenticated_client, "Second Player")

    authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": first_player["id"],
        },
    )

    second_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": second_player["id"],
        },
    )

    second_roster_id = second_response.json()["id"]

    response = authenticated_client.patch(
        f"/seasons-rosters/{second_roster_id}",
        json={
            "player_id": first_player["id"],
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Player is already on this seasons roster."
    )


def test_update_season_roster_route_returns_409_for_active_jersey_conflict(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    first_player = _create_player(authenticated_client, "First Player")
    second_player = _create_player(authenticated_client, "Second Player")

    authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": first_player["id"],
            "jersey_number": 12,
        },
    )

    second_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": second_player["id"],
            "jersey_number": 7,
        },
    )

    second_roster_id = second_response.json()["id"]

    response = authenticated_client.patch(
        f"/seasons-rosters/{second_roster_id}",
        json={
            "jersey_number": 12,
        },
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Jersey number 12 is already assigned "
        "to an active player in this seasons."
    )


def test_update_season_roster_route_returns_422_for_none_status(
    authenticated_client,
    db_session,
):
    season = _create_season(authenticated_client, db_session)
    player = _create_player(authenticated_client)

    create_response = authenticated_client.post(
        "/seasons-rosters",
        json={
            "season_id": season["id"],
            "player_id": player["id"],
        },
    )

    roster_id = create_response.json()["id"]

    response = authenticated_client.patch(
        f"/seasons-rosters/{roster_id}",
        json={
            "status": None,
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"] == (
        "Season roster status cannot be None"
    )